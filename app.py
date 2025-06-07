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
    syllabi_dir = os.path.join(os.path.dirname(__file__), "syllabi", "standard")
    courses = []
    for filename in os.listdir(syllabi_dir):
        if filename.endswith(".yml"):
            filepath = os.path.join(syllabi_dir, filename)
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
    courses.sort()
    return render_template("dependencies.html", courses=courses)

if __name__ == "__main__":
    app.run(debug=True)
