#!/bin/bash

# Standard courses 
GLOBAL="./global.yml"
OUTPUT_DIR="./output"
INPUT_DIR_STANDARD="./syllabi"
INPUT_DIR_MODULAR="./syllabi/modular"
OVERWRITE=false

print_usage() {
    echo "Usage: $0 [-o]"
    echo "  -o    Overwrite existing .docx files"
}

while getopts ":oh" opt; do
    case ${opt} in
        o )
            OVERWRITE=true
            ;;
        h )
            print_usage
            exit 0
            ;;
        \? )
            echo "Invalid option: -$OPTARG" >&2
            print_usage
            exit 1
            ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

for yaml_file in "$INPUT_DIR_STANDARD"/*.yml; do
    filename=$(basename "$yaml_file" .yml)
    output_docx="$OUTPUT_DIR/${filename}.docx"
    output_pdf="$OUTPUT_DIR/${filename}.pdf"

    if [ -f "$output_pdf" ] && [ "$OVERWRITE" = false ]; then
        echo "Skipping existing file: $output_docx"
        continue
    fi

    ./create_syllabus.py "./templates/template_standard.docx" "$output_docx" "$yaml_file" "$GLOBAL"

    # rm "$output_docx"
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "Error (code 1) generating syllabus for $yaml_file" >&2
        exit 1
    elif [ $exit_code -ne 0 ]; then
        echo "Error (code $exit_code) generating syllabus for $yaml_file" >&2
    fi
done

for yaml_file in "$INPUT_DIR_MODULAR"/*.yml; do
    filename=$(basename "$yaml_file" .yml)
    output_docx="$OUTPUT_DIR/${filename}.docx"
    output_pdf="$OUTPUT_DIR/${filename}.pdf"

    if [ -f "$output_pdf" ] && [ "$OVERWRITE" = false ]; then
        echo "Skipping existing file: $output_docx"
        continue
    fi

    ./create_syllabus.py "./templates/template_modules.docx" "$output_docx" "$yaml_file" "$GLOBAL"
    # rm "$output_docx"
    exit_code=$?
    if [ $exit_code -eq 1 ]; then
        echo "Error (code 1) generating syllabus for $yaml_file" >&2
        exit 1
    elif [ $exit_code -ne 0 ]; then
        echo "Error (code $exit_code) generating syllabus for $yaml_file" >&2
    fi
done