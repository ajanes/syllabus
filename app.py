from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import os
import yaml

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"
socketio = SocketIO(app)

# Course data loaded at startup
COURSES = []
COURSE_TOPICS = {}
COURSE_PATHS = {}
COURSE_NAMES = {}
YEARS = []

def load_courses():
    """Load all courses and modules into memory."""
    global COURSES, COURSE_TOPICS, COURSE_PATHS, YEARS
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
                entries.append({
                    "name": f"{title}",
                    "topics": topics,
                    "year": year,
                    "semester": semester,
                    "path": filepath,
                })
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
                    entries.append({
                        "name": f"{title}",
                        "topics": topics,
                        "year": year,
                        "semester": semester,
                        "path": mod_file,
                    })
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
        courses.append({
            "id": cid,
            "name": entry["name"],
            "year": entry["year"],
            "semester": entry["semester"],
        })
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
    base_topic = data.get("topic")
    optional_topic = data.get("optional_topic", "")
    description = data.get("note", "")

    path = COURSE_PATHS.get(target_id)
    if not path or not base_topic or not source_id:
        return

    try:
        with open(path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception:
        yaml_data = {}

    root_key = next((k for k in ("course", "module1", "module2") if k in yaml_data), "course")
    root = yaml_data.get(root_key, {})

    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []

    entry = {
        "course": COURSE_NAMES.get(source_id, ""),
        "topic": base_topic,
    }
    if optional_topic:
        entry["optional_topic"] = optional_topic
    if description:
        entry["description"] = description

    updated = False
    for dep in deps:
        if dep.get("course") == entry["course"] and dep.get("topic") == base_topic:
            if optional_topic:
                dep["optional_topic"] = optional_topic
            else:
                dep.pop("optional_topic", None)
            if description:
                dep["description"] = description
            else:
                dep.pop("description", None)
            updated = True
            break

    if not updated:
        deps.append(entry)

    root["depends-on"] = deps
    yaml_data[root_key] = root
    with open(path, "w") as f:
        yaml.safe_dump(yaml_data, f, sort_keys=False)

    emit("saved", {"ok": True})


@socketio.on("get_dependencies")
def handle_get_dependencies(data):
    target_id = data.get("target_id")
    path = COURSE_PATHS.get(target_id)
    deps = []
    if path:
        try:
            with open(path, "r") as f:
                yaml_data = yaml.safe_load(f) or {}
            root_key = next((k for k in ("course", "module1", "module2") if k in yaml_data), "course")
            root = yaml_data.get(root_key, {})
            deps = root.get("depends-on", [])
            if not isinstance(deps, list):
                deps = []
        except Exception:
            deps = []
    emit("dependencies", {"target_id": target_id, "dependencies": deps})


@socketio.on("remove_dependency")
def handle_remove_dependency(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    topic = data.get("topic")
    if not target_id or not source_id or not topic:
        return
    path = COURSE_PATHS.get(target_id)
    if not path:
        return
    try:
        with open(path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception:
        return

    root_key = next((k for k in ("course", "module1", "module2") if k in yaml_data), "course")
    root = yaml_data.get(root_key, {})
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []
    course_name = COURSE_NAMES.get(source_id, "")
    new_deps = [d for d in deps if not (d.get("course") == course_name and d.get("topic") == topic)]
    if len(new_deps) != len(deps):
        root["depends-on"] = new_deps
        yaml_data[root_key] = root
        with open(path, "w") as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False)
    emit("saved", {"ok": True})


@socketio.on("update_dependency")
def handle_update_dependency(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    base_topic = data.get("topic")
    optional_topic = data.get("optional_topic", "")
    description = data.get("note", "")
    if not target_id or not source_id or not base_topic:
        return
    path = COURSE_PATHS.get(target_id)
    if not path:
        return
    try:
        with open(path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception:
        yaml_data = {}
    root_key = next((k for k in ("course", "module1", "module2") if k in yaml_data), "course")
    root = yaml_data.get(root_key, {})
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []
    course_name = COURSE_NAMES.get(source_id, "")
    updated = False
    for dep in deps:
        if dep.get("course") == course_name and dep.get("topic") == base_topic:
            if optional_topic:
                dep["optional_topic"] = optional_topic
            else:
                dep.pop("optional_topic", None)
            if description:
                dep["description"] = description
            else:
                dep.pop("description", None)
            updated = True
            break
    if not updated:
        new_entry = {"course": course_name, "topic": base_topic}
        if optional_topic:
            new_entry["optional_topic"] = optional_topic
        if description:
            new_entry["description"] = description
        deps.append(new_entry)
    root["depends-on"] = deps
    yaml_data[root_key] = root
    with open(path, "w") as f:
        yaml.safe_dump(yaml_data, f, sort_keys=False)
    emit("saved", {"ok": True})

if __name__ == "__main__":
    socketio.run(app, debug=True)
