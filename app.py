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

    COURSES = courses
    COURSE_TOPICS = course_topics
    COURSE_PATHS = course_paths
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
    topic = data.get("topic")
    path = COURSE_PATHS.get(target_id)
    if not path or not topic:
        return
    try:
        with open(path, "r") as f:
            yaml_data = yaml.safe_load(f) or {}
    except Exception:
        yaml_data = {}
    course = yaml_data.get("course", {})
    deps = course.get("depends-on", [])
    if topic not in deps:
        deps.append(topic)
        course["depends-on"] = deps
        yaml_data["course"] = course
        with open(path, "w") as f:
            yaml.safe_dump(yaml_data, f, sort_keys=False)
    emit("saved", {"ok": True})

if __name__ == "__main__":
    socketio.run(app, debug=True)
