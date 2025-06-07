from flask import Flask, render_template
import os
import yaml

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", message="Welcome to Flask!")


@app.route("/dependencies")
def dependencies():
    """Display course dependencies page with topics."""
    base_dir = os.path.dirname(__file__)

    entries = []

    # Collect standard courses and their topics
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
                    "name": f"{title} ({year} year, {semester} semester)",
                    "topics": topics,
                })
        except Exception:
            continue

    # Collect modules referenced by modular course files
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
            includes = data.get("include", [])
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
                        "name": f"{title} ({year} year, {semester} semester)",
                        "topics": topics,
                    })
        except Exception:
            continue

    # Sort courses by name
    entries.sort(key=lambda e: e["name"])

    courses = []
    course_topics = {}
    for idx, entry in enumerate(entries, 1):
        courses.append({"id": str(idx), "name": entry["name"]})
        course_topics[str(idx)] = entry["topics"]

    return render_template("dependencies.html", courses=courses, course_topics=course_topics)

if __name__ == "__main__":
    app.run(debug=True)
