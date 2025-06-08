from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import yaml
import networkx as nx
from ruamel.yaml import YAML

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"
socketio = SocketIO(app)

# Use ruamel.yaml for writing to preserve YAML formatting
yaml_rt = YAML()
yaml_rt.preserve_quotes = True
yaml_rt.width = float("inf")

# File storing ignored warnings
IGNORED_FILE = os.path.join(os.path.dirname(__file__), "warnings.yml")

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
    """Return the course dictionary from a YAML structure."""
    return "course", data.get("course", {})


def load_ignored_warnings():
    data = load_yaml(IGNORED_FILE)
    warns = data.get("ignore", [])
    if not isinstance(warns, list):
        return []
    return warns


def load_ignored_errors():
    data = load_yaml(IGNORED_FILE)
    errs = data.get("ignore_errors", [])
    if not isinstance(errs, list):
        return []
    return errs


def update_ignored_warning(text, ignore=True):
    data = load_yaml(IGNORED_FILE)
    warns = data.get("ignore", [])
    if not isinstance(warns, list):
        warns = []
    if ignore:
        if text not in warns:
            warns.append(text)
    else:
        warns = [w for w in warns if w != text]
    data["ignore"] = warns
    save_yaml(IGNORED_FILE, data)


def update_ignored_error(text, ignore=True):
    data = load_yaml(IGNORED_FILE)
    errs = data.get("ignore_errors", [])
    if not isinstance(errs, list):
        errs = []
    if ignore:
        if text not in errs:
            errs.append(text)
    else:
        errs = [e for e in errs if e != text]
    data["ignore_errors"] = errs
    save_yaml(IGNORED_FILE, data)


def modify_dependency(path, course_name, base_topic, subtopic="", note=""):
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
    try:
        base_idx = int(base_topic)
    except (TypeError, ValueError):
        return

    item = next((t for t in topics if int(t.get("topic", -1)) == base_idx), None)
    if item:
        if subtopic:
            item["subtopic"] = subtopic
        else:
            item.pop("subtopic", None)
        if note:
            item["note"] = note
        else:
            item.pop("note", None)
    else:
        new_topic = {"topic": base_idx}
        if subtopic:
            new_topic["subtopic"] = subtopic
        if note:
            new_topic["note"] = note
        topics.append(new_topic)
    entry["topics"] = topics

    root["depends-on"] = deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def update_comment(path, course_name, comment=""):
    yaml_data = load_yaml(path)
    key, root = get_root(yaml_data)
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []

    entry = next((d for d in deps if d.get("course") == course_name), None)
    if entry is None:
        entry = {"course": course_name, "topics": []}
        deps.append(entry)

    if comment:
        entry["comment"] = comment
    else:
        entry.pop("comment", None)

    root["depends-on"] = deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def remove_dependency(path, course_name, base_topic):
    yaml_data = load_yaml(path)
    key, root = get_root(yaml_data)
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []

    try:
        base_idx = int(base_topic)
    except (TypeError, ValueError):
        return

    for dep in deps:
        if dep.get("course") == course_name:
            topics = dep.get("topics", [])
            new_topics = [t for t in topics if int(t.get("topic", -1)) != base_idx]
            if new_topics:
                dep["topics"] = new_topics
            else:
                dep.pop("topics", None)
                if not dep.get("comment"):
                    deps.remove(dep)
            break
    root["depends-on"] = deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def remove_course_dependency(source_name, target_name):
    """Remove all dependencies on target_name from source_name course."""
    source_id = next((cid for cid, n in COURSE_NAMES.items() if n == source_name), None)
    if not source_id:
        return
    path = COURSE_PATHS.get(source_id)
    if not path:
        return
    yaml_data = load_yaml(path)
    key, root = get_root(yaml_data)
    deps = root.get("depends-on", [])
    if not isinstance(deps, list):
        deps = []
    new_deps = [d for d in deps if d.get("course") != target_name]
    root["depends-on"] = new_deps
    yaml_data[key] = root
    save_yaml(path, yaml_data)


def load_courses():
    """Load all courses and modules into memory."""
    global COURSES, COURSE_TOPICS, COURSE_PATHS, COURSE_NAMES, YEARS
    base_dir = os.path.dirname(__file__)
    entries = []
    years = set()


    course_dir = os.path.join(base_dir, "syllabi")
    for filename in os.listdir(course_dir):
        filepath = os.path.join(course_dir, filename)
        if not filename.endswith(".yml") or not os.path.isfile(filepath):
            continue
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


def dependency_info():
    """Return list of courses sorted by number of dependent courses."""

    # Map course name to id for quick lookup
    name_to_id = {v: k for k, v in COURSE_NAMES.items()}

    # Track dependents for each course and for each topic
    dependents = {
        cid: {"total": set(), "topics": {}} for cid in COURSE_PATHS.keys()
    }

    # Scan all courses to populate dependents structure
    for src_id, path in COURSE_PATHS.items():
        data = load_yaml(path)
        _, root = get_root(data)
        deps = root.get("depends-on", [])
        if not isinstance(deps, list):
            deps = []
        for entry in deps:
            target_name = entry.get("course")
            target_id = name_to_id.get(target_name)
            if not target_id:
                continue
            dependents[target_id]["total"].add(COURSE_NAMES.get(src_id, ""))
            topics = entry.get("topics", []) or []
            for t in topics:
                try:
                    idx = int(t.get("topic"))
                except (TypeError, ValueError):
                    continue
                dependents[target_id]["topics"].setdefault(idx, []).append(
                    {
                        "course": COURSE_NAMES.get(src_id, ""),
                        "subtopic": t.get("subtopic", ""),
                        "note": t.get("note", ""),
                    }
                )

    # Build final list
    result = []
    for cid in COURSE_PATHS.keys():
        topics_data = []
        for idx, topic_name in enumerate(COURSE_TOPICS.get(cid, []), 1):
            dep_entries = dependents[cid]["topics"].get(idx, [])
            topics_data.append(
                {
                    "name": topic_name,
                    "courses": [
                        {
                            "id": name_to_id.get(entry.get("course", ""), ""),
                            "name": entry.get("course", ""),
                            "course": entry.get("course", ""),
                            "subtopic": entry.get("subtopic", ""),
                            "note": entry.get("note", ""),
                        }
                        for entry in dep_entries
                    ],
                }
            )

        count = len(dependents[cid]["total"])
        result.append(
            {
                "id": cid,
                "name": COURSE_NAMES.get(cid, ""),
                "topics": topics_data,
                "count": count,
            }
        )

    result.sort(key=lambda d: d["count"], reverse=True)
    return result


def build_course_graph():
    """Return a directed graph of course dependencies."""
    g = nx.DiGraph()
    for name in COURSE_NAMES.values():
        g.add_node(name)
    for cid, path in COURSE_PATHS.items():
        course_name = COURSE_NAMES.get(cid, "")
        data = load_yaml(path)
        _, root = get_root(data)
        deps = root.get("depends-on", [])
        if not isinstance(deps, list):
            continue
        for d in deps:
            dep_name = d.get("course")
            if dep_name:
                g.add_edge(course_name, dep_name)
    return g


def find_circular_dependencies():
    """Return a list of course cycles."""
    graph = build_course_graph()
    return list(nx.simple_cycles(graph))


def _parse_order(value):
    """Return numeric order from strings like '1st', '2nd'."""
    try:
        return int("".join(ch for ch in str(value) if ch.isdigit()))
    except Exception:
        return 0


def dependency_issues():
    """Return lists of warning and error messages for course dependencies."""
    name_info = {
        c["name"]: {
            "year": _parse_order(c["year"]),
            "semester": _parse_order(c["semester"]),
        }
        for c in COURSES
    }

    warnings = []
    errors = []

    for cid, path in COURSE_PATHS.items():
        src_name = COURSE_NAMES.get(cid, "")
        src = name_info.get(src_name, {})
        src_year = src.get("year", 0)
        src_sem = src.get("semester", 0)

        data = load_yaml(path)
        _, root = get_root(data)
        deps = root.get("depends-on", [])
        if not isinstance(deps, list):
            deps = []

        for d in deps:
            dep_name = d.get("course")
            info = name_info.get(dep_name)
            if not info:
                continue
            dep_year = info.get("year", 0)
            dep_sem = info.get("semester", 0)

            if dep_year == src_year and dep_sem == src_sem:
                warnings.append(
                    f"{src_name} depends on {dep_name} in the same year and semester"
                )
            elif dep_year > src_year or (
                dep_year == src_year and dep_sem > src_sem
            ):
                errors.append(
                    f"{src_name} depends on {dep_name} in a future semester or year"
                )

    return warnings, errors


@app.route("/")
def home():
    return render_template("index.html", message="Welcome to Flask!")


@app.route("/visualize")
def visualize():
    info = dependency_info()
    return render_template("visualize.html", courses=info)


@app.route("/dependencies")
def dependencies():
    """Display course dependencies page."""
    return render_template(
        "dependencies.html",
        courses=COURSES,
        all_courses=COURSES,
        years=YEARS,
    )
@app.route("/warnings")
def warnings():
    cycles = find_circular_dependencies()
    warns, errs = dependency_issues()
    ignored_warn = set(load_ignored_warnings())
    ignored_err = set(load_ignored_errors())
    warn_objs = [{"text": w, "ignored": w in ignored_warn} for w in warns]
    err_objs = [{"text": e, "ignored": e in ignored_err} for e in errs]
    return render_template(
        "warnings.html",
        cycles=cycles,
        warnings=warn_objs,
        errors=err_objs,
    )

@app.route("/toggle_warning", methods=["POST"])
def toggle_warning():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    ignore = bool(data.get("ignore"))
    if not text:
        return jsonify({"ok": False}), 400
    update_ignored_warning(text, ignore)
    return jsonify({"ok": True})


@app.route("/toggle_error", methods=["POST"])
def toggle_error():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "")
    ignore = bool(data.get("ignore"))
    if not text:
        return jsonify({"ok": False}), 400
    update_ignored_error(text, ignore)
    return jsonify({"ok": True})

@app.route("/remove_course_dependency", methods=["POST"])
def remove_course_dependency_route():
    data = request.get_json(force=True)
    remove_course_dependency(data.get("source"), data.get("target"))
    return {"ok": True}

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
    try:
        base_topic = int(base_topic)
    except (TypeError, ValueError):
        return
    course_name = COURSE_NAMES.get(source_id, "")
    modify_dependency(
        path,
        course_name,
        base_topic,
        data.get("subtopic", ""),
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
    try:
        base_topic = int(base_topic)
    except (TypeError, ValueError):
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
    try:
        base_topic = int(base_topic)
    except (TypeError, ValueError):
        return
    course_name = COURSE_NAMES.get(source_id, "")
    modify_dependency(
        path,
        course_name,
        base_topic,
        data.get("subtopic", ""),
        data.get("note", ""),
    )
    emit("saved", {"ok": True})


@socketio.on("update_comment")
def handle_update_comment(data):
    target_id = data.get("target_id")
    source_id = data.get("source_id")
    path = COURSE_PATHS.get(target_id)
    if not path or not source_id:
        return
    course_name = COURSE_NAMES.get(source_id, "")
    update_comment(path, course_name, data.get("comment", ""))
    emit("saved", {"ok": True})


if __name__ == "__main__":
    socketio.run(app, debug=True)
