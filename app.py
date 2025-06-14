from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import os
import threading
import yaml
import networkx as nx
from ruamel.yaml import YAML
from sentence_transformers import SentenceTransformer, models
from pathlib import Path

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
SIMILARITY_TASKS = {}


def load_yaml(path):
    try:
        with open(path, "r") as f:
            return yaml_rt.load(f) or {}
    except Exception:
        return {}


def save_yaml(path, data):
    with open(path, "w") as f:
        yaml_rt.dump(data, f)


def load_similarity():
    data = load_yaml("./similarity.yml")
    names = data.get("courses", [])
    matrix = data.get("matrix", [])
    return names, matrix


def save_similarity(names, matrix):
    save_yaml("./similarity.yml", {"courses": names, "matrix": matrix})


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


def compute_similarity(cancel_event=None, progress_cb=None, force=False):
    """Compute cosine similarity matrix for all courses.

    Parameters
    ----------
    cancel_event: threading.Event | None
        If provided, computation aborts when this event is set.
    progress_cb: callable(int) | None
        Called periodically with an integer percentage from 0 to 100.
    """

    if not force:
        names, matrix = load_similarity()
        if names and matrix:
            if progress_cb:
                progress_cb(100)
            return names, matrix

    if progress_cb:
        progress_cb(0)

    texts = []
    names = []
    for c in COURSES:
        names.append(c["name"])
        topics = COURSE_TOPICS.get(c["id"], [])
        texts.append(" ".join(topics))

    if progress_cb:
        progress_cb(10)

    if not texts or (cancel_event and cancel_event.is_set()):
        return names, []

    model_path = str(Path("all-MiniLM-L6-v2").resolve())

    word_embedding_model = models.Transformer(model_path)
    pooling_model = models.Pooling(word_embedding_model.get_word_embedding_dimension())
    model = SentenceTransformer(modules=[word_embedding_model, pooling_model])

    if progress_cb:
        progress_cb(20)

    if cancel_event and cancel_event.is_set():
        return names, []

    embeddings = model.encode(texts, normalize_embeddings=True)

    if progress_cb:
        progress_cb(70)

    if cancel_event and cancel_event.is_set():
        return names, []

    matrix = (embeddings @ embeddings.T).tolist()

    if progress_cb:
        progress_cb(100)
    save_similarity(names, matrix)
    return names, matrix

# > 0.8: very likely overlapping
# 0.6 – 0.8: some overlap
# < 0.6: weak or no meaningful overlap

def similarity_colors(matrix):
    white = "#FFFFFF"
    orange = "#FFA500"
    red = "#FF0000"

    def get_color(val):
        if val < 0.6:
            return white
        elif val > 0.8:
            return red
        else:
            return orange

    return [[get_color(val) for val in row] for row in matrix]



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
    dependent_counts = {name: 0 for name in COURSE_NAMES.values()}

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
            if dep_name in dependent_counts:
                dependent_counts[dep_name] += 1
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

    for name, count in dependent_counts.items():
        if count == 0:
            warnings.append(f"No course depends on {name}")

    return warnings, errors


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/dependency_list")
def dependency_list():
    info = dependency_info()
    return render_template("dependency_list.html", courses=info)


@app.route("/dependency_graph")
def dependency_graph():
    """Display a force-directed graph of course dependencies."""
    graph = build_course_graph()
    links = [{"source": u, "target": v} for u, v in graph.edges]
    nodes = [{"id": n} for n in graph.nodes]
    # names, matrix = load_similarity()

    linked_ids = {link["source"] for link in links} | {link["target"] for link in links}
    nodes = [node for node in nodes if node["id"] in linked_ids]

    sim_links = []
    # for i, src in enumerate(names):
    #     for j in range(i + 1, len(names)):
    #         try:
    #             val = matrix[i][j]
    #         except Exception:
    #             continue
    #         if val >= 0.6:
    #             sim_links.append(
    #                 {
    #                     "source": src,
    #                     "target": names[j],
    #                     "distance": 150 * (1 - val),
    #                 }
    #             )
    return render_template(
        "dependency_graph.html", nodes=nodes, links=links, sim_links=sim_links
    )




@app.route("/similarity")
def similarity():
    """Display similarity matrix."""
    names, matrix = load_similarity()
    colors = similarity_colors(matrix) if matrix else []
    data = {"courses": names, "matrix": matrix, "colors": colors}
    return render_template("similarity.html", data=data)


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


@app.route("/warning_stats")
def warning_stats():
    warns, errs = dependency_issues()
    ignored_warn = set(load_ignored_warnings())
    ignored_err = set(load_ignored_errors())
    active_warns = [w for w in warns if w not in ignored_warn]
    active_errs = [e for e in errs if e not in ignored_err]
    return jsonify({"warnings": len(active_warns), "errors": len(active_errs)})

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


@socketio.on("start_similarity")
def handle_start_similarity(data=None):
    """Compute similarity matrix in the background."""
    sid = request.sid

    stop_event = threading.Event()

    force = False
    if isinstance(data, dict):
        force = bool(data.get("force"))

    def worker():
        def update(pct):
            socketio.emit("similarity_progress", {"progress": pct}, to=sid)

        names, matrix = compute_similarity(
            cancel_event=stop_event, progress_cb=update, force=force
        )
        if stop_event.is_set():
            return
        socketio.emit(
            "similarity_result",
            {"courses": names, "matrix": matrix, "colors": similarity_colors(matrix)},
            to=sid,
        )

    thread = threading.Thread(target=worker, daemon=True)
    SIMILARITY_TASKS[sid] = (thread, stop_event)
    thread.start()


@socketio.on("disconnect")
def handle_disconnect():
    task = SIMILARITY_TASKS.pop(request.sid, None)
    if task:
        _, event = task
        event.set()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, debug=False, host="0.0.0.0", port=port)
