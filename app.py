from flask import Flask, render_template
import os
import yaml

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html", message="Welcome to Flask!")


@app.route("/dependencies")
def dependencies():
    """Display course dependencies page."""
    base_dir = os.path.dirname(__file__)

    courses = []

    # Collect standard courses
    std_dir = os.path.join(base_dir, "syllabi", "standard")
    for filename in os.listdir(std_dir):
        if not filename.endswith(".yml"):
            continue
        filepath = os.path.join(std_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            course = data.get("course", {}) if data else {}
            title = course.get("title")
            semester = course.get("semester")
            year = course.get("year")
            if title and semester and year:
                courses.append(f"{title} ({year} year, {semester} semester)")
        except Exception:
            continue

    # Collect modules referenced by modular course files
    modular_dir = os.path.join(base_dir, "syllabi", "modular")
    modules_dir = os.path.join(modular_dir, "modules")

    for filename in os.listdir(modular_dir):
        if not filename.endswith(".yml"):
            continue
        filepath = os.path.join(modular_dir, filename)
        try:
            with open(filepath, "r") as f:
                data = yaml.safe_load(f)
            if not data:
                continue
            course = data.get("course", {})
            semester = course.get("semester")
            year = course.get("year")
            includes = data.get("include", [])
            for mod_path in includes or []:
                mod_file = os.path.join(base_dir, mod_path)
                if not os.path.isfile(mod_file):
                    continue
                with open(mod_file, "r") as mf:
                    mod_data = yaml.safe_load(mf)
                if not mod_data:
                    continue
                module_info = next(iter(mod_data.values()))
                title = module_info.get("title") if isinstance(module_info, dict) else None
                if title and semester and year:
                    courses.append(f"{title} ({year} year, {semester} semester)")
        except Exception:
            continue

    courses.sort()
    return render_template("dependencies.html", courses=courses)

if __name__ == "__main__":
    app.run(debug=True)
