from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os
import yaml
from ruamel.yaml import YAML

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"
socketio = SocketIO(app)

# Use ruamel.yaml for writing to preserve YAML formatting
yaml_rt = YAML()
yaml_rt.preserve_quotes = True
yaml_rt.width = float("inf")

# Course data loaded at startup
COURSES = []
COURSE_TOPICS = {}
COURSE_PATHS = {}
COURSE_NAMES = {}
YEARS = []


def load_yaml(path):
    try:
        with open(path, "r") as f:
            return yaml_rt.load(f) or {}
    except Exception:
        return {}


def save_yaml(path, data):
    with open(path, "w") as f:
        yaml_rt.dump(data, f)


def get_root(data):
    key = next(
        (k for k in ("course", "module1", "module2") if k in data), "course"
    )
    return key, data.get(key, {})


def modify_dependency(path, course_name, base_topic, sub_topic="", note=""):
    yaml_data = load_yaml(path)
    key, root = get_root(yaml_data)
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []

    entry = next((d for d in deps if d.get("course") == course_name), None)
    if entry is None:
        entry = {"course": course_name, "topics": []}
        deps.append(entry)

    topics = entry.get("topics", [])
    item = next((t for t in topics if t.get("topic") == base_topic), None)
    if item:
        if sub_topic:
            item["sub-topic"] = sub_topic
        else:
            item.pop("sub-topic", None)
        if note:
            item["note"] = note
        else:
            item.pop("note", None)
    else:
        new_topic = {"topic": base_topic}
        if sub_topic:
            new_topic["sub-topic"] = sub_topic
        if note:
            new_topic["note"] = note
        topics.append(new_topic)
    entry["topics"] = topics

    root["depends-on"] = deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def remove_dependency(path, course_name, base_topic):
    yaml_data = load_yaml(path)
    key, root = get_root(yaml_data)
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []
    for dep in deps:
        if dep.get("course") == course_name:
            topics = dep.get("topics", [])
            new_topics = [t for t in topics if t.get("topic") != base_topic]
            if new_topics:
                dep["topics"] = new_topics
            else:
                deps.remove(dep)
            break
    root["depends-on"] = deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def load_courses():
    """Load all courses and modules into memory."""
    global COURSES, COURSE_TOPICS, COURSE_PATHS, COURSE_NAMES, YEARS
    base_dir = os.path.dirname(__file__)
    entries = []
    years = set()

    std_dir = os.path.join(base_dir, "syllabi", "standard")
    for filename in os.listdir(std_dir):
        if not filename.endswith(".yml"):
            continue
        filepath = os.path.join(std_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f) or {}
            course = data.get("course", {})
            title = course.get("title")
            semester = course.get("semester")
            year = course.get("year")
            topics = course.get("topics", [])
            if title and semester and year:
                entries.append(
                    {
                        "name": f"{title}",
                        "topics": topics,
                        "year": year,
                        "semester": semester,
                        "path": filepath,
                    }
                )
                years.add(year)
        except Exception:
            continue

    modular_dir = os.path.join(base_dir, "syllabi", "modular")
    for filename in os.listdir(modular_dir):
        if not filename.endswith(".yml"):
            continue
        filepath = os.path.join(modular_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f) or {}
            course = data.get("course", {})
            semester = course.get("semester")
            year = course.get("year")
            includes = course.get("include", [])
            for mod_path in includes or []:
                mod_file = os.path.join(base_dir, mod_path)
                if not os.path.isfile(mod_file):
                    continue
                with open(mod_file, "r") as mf:
                    mod_data = yaml.safe_load(mf) or {}
                module_info = next(iter(mod_data.values()))
                if not isinstance(module_info, dict):
                    continue
                title = module_info.get("title")
                topics = module_info.get("topics", [])
                if title and semester and year:
                    entries.append(
                        {
                            "name": f"{title}",
                            "topics": topics,
                            "year": year,
                            "semester": semester,
                            "path": mod_file,
                        }
                    )
                    years.add(year)
        except Exception:
            continue

    entries.sort(key=lambda e: e["name"])

    courses = []
    course_topics = {}
    course_paths = {}
    course_names = {}
    for idx, entry in enumerate(entries, 1):
        cid = str(idx)
        courses.append(
            {
                "id": cid,
                "name": entry["name"],
                "year": entry["year"],
                "semester": entry["semester"],
            }
        )
        course_topics[cid] = entry["topics"]
        course_paths[cid] = entry["path"]
        course_names[cid] = entry["name"]

    COURSES = courses
    COURSE_TOPICS = course_topics
    COURSE_PATHS = course_paths
    COURSE_NAMES = course_names
    YEARS = sorted(years)


load_courses()


@app.route("/")
def home():
    return render_template("index.html", message="Welcome to Flask!")


@app.route("/dependencies")
def dependencies():
    """Display course dependencies page."""
    return render_template(
        "dependencies.html",
        courses=COURSES,
        all_courses=COURSES,
        years=YEARS,
    )


@socketio.on("filter")
def handle_filter(data):
    year = data.get("year", "")
    semester = data.get("semester", "")
    course_id = data.get("course", "")
    filtered = [
        c
        for c in COURSES
        if (not year or c["year"] == year)
        and (not semester or c["semester"] == semester)
    ]
    if course_id not in [c["id"] for c in filtered]:
        selected_course = ""
        topics = []
    else:
        selected_course = course_id
        topics = COURSE_TOPICS.get(course_id, [])
    emit(
        "filtered",
        {
            "courses": filtered,
            "topics": topics,
            "selected_course": selected_course,
        },
    )


@socketio.on("add_dependency")
def handle_add_dependency(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    base_topic = data.get("base_topic")
    path = COURSE_PATHS.get(target_id)
    if not path or not base_topic or not source_id:
        return
    course_name = COURSE_NAMES.get(source_id, "")
    modify_dependency(
        path,
        course_name,
        base_topic,
        data.get("sub_topic", ""),
        data.get("note", ""),
    )
    emit("saved", {"ok": True})


@socketio.on("get_dependencies")
def handle_get_dependencies(data):
    target_id = data.get("target_id")
    path = COURSE_PATHS.get(target_id)
    deps = []
    if path:
        key, root = get_root(load_yaml(path))
        deps = root.get("depends-on", [])
        if not isinstance(deps, list):
            deps = []
    emit("dependencies", {"target_id": target_id, "dependencies": deps})


@socketio.on("remove_dependency")
def handle_remove_dependency(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    base_topic = data.get("base_topic")
    path = COURSE_PATHS.get(target_id)
    if not path or not base_topic or not source_id:
        return
    course_name = COURSE_NAMES.get(source_id, "")
    remove_dependency(path, course_name, base_topic)
    emit("saved", {"ok": True})


@socketio.on("update_dependency")
def handle_update_dependency(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    base_topic = data.get("base_topic")
    path = COURSE_PATHS.get(target_id)
    if not path or not base_topic or not source_id:
        return
    course_name = COURSE_NAMES.get(source_id, "")
    modify_dependency(
        path,
        course_name,
        base_topic,
        data.get("sub_topic", ""),
        data.get("note", ""),
    )
    emit("saved", {"ok": True})


if __name__ == "__main__":
    socketio.run(app, debug=True)
