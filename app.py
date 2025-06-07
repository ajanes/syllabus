from flask import Flask, render_template, request
import os
import yaml

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-me"

@app.route("/")
def home():
    return render_template("index.html", message="Welcome to Flask!")


@app.route("/dependencies")
def dependencies():
    """Display course dependencies page with topics."""
    base_dir = os.path.dirname(__file__)

    entries = []
    years = set()

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
                    "name": f"{title}",
                    "topics": topics,
                    "year": year,
                    "semester": semester,
                })
                years.add(year)
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
                    })
                    years.add(year)
        except Exception:
            continue

    # Sort courses by name
    entries.sort(key=lambda e: e["name"])

    courses = []
    course_topics = {}
    for idx, entry in enumerate(entries, 1):
        courses.append(
            {
                "id": str(idx),
                "name": entry["name"],
                "year": entry["year"],
                "semester": entry["semester"],
            }
        )
        course_topics[str(idx)] = entry["topics"]

    years = sorted(years)

    selected_year = request.args.get("year", "")
    selected_semester = request.args.get("semester", "")
    selected_course = request.args.get("course", "")

    filtered_courses = [
        c
        for c in courses
        if (not selected_year or c["year"] == selected_year)
        and (not selected_semester or c["semester"] == selected_semester)
    ]

    if not any(c["id"] == selected_course for c in filtered_courses):
        selected_course = ""
        topics = []
    else:
        topics = course_topics.get(selected_course, [])

    return render_template(
        "dependencies.html",
        courses=filtered_courses,
        all_courses=courses,
        years=years,
        selected_year=selected_year,
        selected_semester=selected_semester,
        selected_course=selected_course,
        topics=topics,
    )

if __name__ == "__main__":
    app.run(debug=True)
