#!/usr/bin/env python

import os, re, yaml, json
from jsonschema import validate, ValidationError

schemas = {
    "course": json.load(open("./schemas/course_schema.json")),
    "module": json.load(open("./schemas/module_schema.json"))
}

expected_order = [
    "title", "code", "scientific_sector", "degree", "semester", "year", "credits", "modular",
    "total_lecturing_hours", "total_lab_hours", "attendance", "prerequisites", "course_page",
    "specific_educational_objectives", "lecturer", "language", "teaching_assistant", "topics",
    "teaching_format", "assessment", "assessment_language", "assessment_typology", "evaluation_criteria",
    "required_readings", "supplementary_readings", "software"
]

def get_positions(data):
    return [expected_order.index(k) for k in data.get("course", {}) if k in expected_order]

def check_order(positions):
    if any(positions[i] <= positions[i - 1] for i in range(1, len(positions))):
        raise ValidationError("Fields not in expected order.")

folder = "./syllabi/standard"
pattern = re.compile(r"^[\w\s]+ \(\d+\)\.yml$", re.IGNORECASE)

for filename in os.listdir(folder):
    if pattern.match(filename):
        path = os.path.abspath(os.path.join(folder, filename))
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
                top_key = next(iter(data), None)
                if top_key not in schemas:
                    raise ValidationError(f"Unsupported top-level key: '{top_key}'")
                validate(instance=data, schema=schemas[top_key])
                if top_key == "course":
                    check_order(get_positions(data))
        except ValidationError as ve:
            field = ".".join([str(p) for p in ve.path]) or "(root)"
            print(f"❌ {filename} is INVALID:\n   {path}:1\n   Field: {field}\n   Error: {ve.message}")
        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")
