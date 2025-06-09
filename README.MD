# syllabus

A toolset for managing, validating, comparing, and visualizing university course syllabi described in structured YAML format.

## Features

* YAML-based syllabus definition
* Schema validation using JSON Schema
* Course similarity analysis based on content overlap
* Course dependency and hierarchy visualization
* Interactive web-based UI
* Similarity computation using embeddings
* Python backend with Flask

## Structure

```
syllabus/
├── app.py                 # Main Flask application
├── static/                # Static assets (JS/CSS/images)
├── templates/             # Jinja2 templates
├── schema/                # JSON Schema for validation
├── syllabi/               # Collection of YAML course descriptions
├── utils/                 # Similarity, parsing, and helper functions
├── scripts/               # CLI tools (e.g., for validation, analysis)
└── requirements.txt       # Python dependencies
```

## Installation

```bash
git clone https://github.com/ajanes/syllabus.git
cd syllabus
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Launch the Web Application

```bash
python app.py
```

Then open your browser at [http://localhost:5000](http://localhost:5000).

## Example YAML Syllabus

```yaml
course:
  title: Operating Systems
  code: 12345
  scientific_sector: INF/01
  degree: MSc Computer Science
  semester: 1st
  year: 2nd
  credits: 6
  modular: false
  total_lecturing_hours: 40
  total_lab_hours: 20
  prerequisites: Introduction to Computer Science
  learning_outcomes:
    - Understand process scheduling and memory management
    - Apply synchronization primitives
```

## Development

Ensure you have a recent Python 3.10+ version. This project uses Jinja2, PyYAML, Flask, and scikit-learn for similarity computation.

## License

MIT License.