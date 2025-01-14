from pdfminer.high_level import extract_text
from json_helper import InputData as input
from cv_processor import CVProcessor
from docx import Document
import json


def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)


text = extract_text_from_pdf(r"./cv.pdf")

llm = input.llm()

data = llm.invoke(input.input_data(text))
try:
    data = json.loads(data)
except json.JSONDecodeError:
    print("Error: Data is not valid JSON.")
    data = {}


def add_section(doc, title, items, bullet_points=False):
    doc.add_heading(title, level=1)
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                # Add each key-value pair from the dictionary as a paragraph
                for key, value in item.items():
                    doc.add_paragraph(f"{key}: {value}")
                doc.add_paragraph()  # Add a blank line between items for clarity
            else:
                doc.add_paragraph(item, style="List Bullet" if bullet_points else None)
    elif isinstance(items, dict):
        for key, value in items.items():
            print("here")
            doc.add_paragraph(f"{key}: {value}")
    else:
        print("there")
        doc.add_paragraph(items)


def fill_template(data, output_path):
    try:
        # Adding sections to the document
        # 1. Personal Information
        doc = Document()
        doc.add_heading("Personal Information", level=1)
        personal_info = [
            f"Name: {data['name']}",
            f"Email: {data['email']}",
            f"Phone 1: {data['phone_1']}",
            f"Phone 2: {data['phone_2'] or 'Not provided'}",
            f"Address: {data['address'] or 'Not provided'}",
            f"City: {data['city'] or 'Not provided'}",
            f"LinkedIn: {data['linkedin'] or 'Not provided'}",
            f"Professional Experience in Years: {data['professional_experience_in_years']}",
            f"Highest Education: {data['highest_education']}",
            f"Fresher: {'Yes' if data['is_fresher'] == 'yes' else 'No'}",
            f"Student: {'Yes' if data['is_student'] == 'yes' else 'No'}",
            f"Applied for Profile: {data['applied_for_profile'] or 'Not provided'}",
        ]
        for info in personal_info:
            doc.add_paragraph(info)

        # 2. Skills (added as bullet points)
        add_section(doc, "Skills", data["skills"], bullet_points=True)

        # 3. Education
        add_section(doc, "Education", data["education"])

        # 4. Professional Experience
        add_section(doc, "Professional Experience", data["professional_experience"])

        # Save the document
        doc.save(output_path)
        print(f"Document created: {output_path}")
    except Exception as e:
        print(f"Error filling the template: {e}")


# Call fill_template directly
fill_template(data, "output.docx")
