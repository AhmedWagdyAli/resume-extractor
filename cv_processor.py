import os
from docx import Document
from app import app
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)


class CVProcessor:
    def __init__(self):
        self.doc = Document()

    def add_section(self, doc, title, items, bullet_points=False):
        doc.add_heading(title, level=1)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    # Add each key-value pair from the dictionary as a paragraph
                    for key, value in item.items():
                        doc.add_paragraph(f"{key}: {value}")
                    doc.add_paragraph()  # Add a blank line between items for clarity
                else:
                    doc.add_paragraph(
                        item, style="List Bullet" if bullet_points else None
                    )
        elif isinstance(items, dict):
            for key, value in items.items():
                doc.add_paragraph(f"{key}: {value}")
        else:
            doc.add_paragraph(items)

    def add_personal_info(self, doc, data, coded):
        if coded == "code":
            personal_info = [
                f"Name: {'**'}",
                f"Email: {'**@gmail.com'}",
                f"Phone 1: {'****'}",
                f"Phone 2: {'Not provided'}",
                f"Address: {data['address'] or 'Not provided'}",
                f"City: {data['city'] or 'Not provided'}",
                f"LinkedIn: {'**@linkedin.com' or 'Not provided'}",
                f"Professional Experience in Years: {data['professional_experience_in_years']}",
                f"Highest Education: {data['highest_education']}",
            ]
        elif coded == "name":
            personal_info = [
                f"Name: {data['name']}",
                f"Email: {'**@gmail.com'}",
                f"Phone 1: {'****'}",
                f"Phone 2: {'Not provided'}",
                f"Address: {data['address'] or 'Not provided'}",
                f"City: {data['city'] or 'Not provided'}",
                f"LinkedIn: {'**@linkedin.com' or 'Not provided'}",
                f"Professional Experience in Years: {data['professional_experience_in_years']}",
                f"Highest Education: {data['highest_education']}",
            ]
        else:
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
            ]
        for info in personal_info:
            doc.add_paragraph(info)

    def format_experience(self, experience_list):
        if not isinstance(experience_list, list) or not experience_list:
            return "Not provided"

        formatted_experience = []
        for item in experience_list:
            details = []
            for key, value in item.items():
                if value:  # Include only non-empty values
                    # Format the key-value pair in key: value format
                    details.append(f"{key}: {value}")
            # Join details with a newline and ensure proper indentation for each item
            formatted_experience.append("\n".join(details))
        # Separate each experience entry with an additional newline for clarity
        return "\n\n".join(formatted_experience)

    def format_skills(self, skills_text):
        if not skills_text or not isinstance(skills_text, list):
            return "N/A"
        skills_list = [skill.strip() for skill in skills_text]
        # TODO: insert into database here
        return "\n".join(f"• {skill}" for skill in skills_list if skill)

    def format_education(self, education_list):
        if not isinstance(education_list, list):
            return "N/A"

        formatted_education = []
        for item in education_list:
            details = []
            for key, value in item.items():
                if value:  # Include only non-empty values
                    # Format the key-value pair in key: value format
                    details.append(f"{key}: {value}")
            # Join details with a newline and ensure proper indentation for each item
            formatted_education.append("\n".join(details))
        # Separate each experience entry with an additional newline for clarity
        return "\n\n".join(formatted_education)

    def replace_placeholders(self, doc, data, template_type):
        """Replace placeholders in a Word document."""

        def add_personal_info(data, template_type):
            """Generate personal info string dynamically based on template type."""
            if template_type == "code":
                return "\n".join(
                    [
                        f"Name: {'**'}",
                        f"Email: {'**@gmail.com'}",
                        f"Phone 1: {'****'}",
                        f"Phone 2: {'Not provided'}",
                        f"Address: {data.get('address', 'Not provided')}",
                        f"City: {data.get('city', 'Not provided')}",
                        f"LinkedIn: {'**@linkedin.com'}",
                        f"Professional Experience in Years: {data.get('professional_experience_in_years', 'Not provided')}",
                        f"Highest Education: {data.get('highest_education', 'Not provided')}",
                    ]
                )
            elif template_type == "name":
                return "\n".join(
                    [
                        f"Name: {data.get('name', 'Not provided')}",
                        f"Email: {'**@gmail.com'}",
                        f"Phone 1: {'****'}",
                        f"Phone 2: {'Not provided'}",
                        f"Address: {data.get('address', 'Not provided')}",
                        f"City: {data.get('city', 'Not provided')}",
                        f"LinkedIn: {'**@linkedin.com'}",
                        f"Professional Experience in Years: {data.get('professional_experience_in_years', 'Not provided')}",
                        f"Highest Education: {data.get('highest_education', 'Not provided')}",
                    ]
                )
            else:  # Normal template
                return "\n".join(
                    [
                        f"Name: {data.get('name', 'Not provided')}",
                        f"Email: {data.get('email', 'Not provided')}",
                        f"Phone 1: {data.get('phone_1', 'Not provided')}",
                        f"Phone 2: {data.get('phone_2', 'Not provided')}",
                        f"Address: {data.get('address', 'Not provided')}",
                        f"City: {data.get('city', 'Not provided')}",
                        f"LinkedIn: {data.get('linkedin', 'Not provided')}",
                        f"Professional Experience in Years: {data.get('professional_experience_in_years', 'Not provided')}",
                        f"Highest Education: {data.get('highest_education', 'Not provided')}",
                    ]
                )

        def convert_value(key, value):
            """Convert individual key-value pairs based on template type."""
            if (
                key == "professional_experience"
                or key == "projects"
                and isinstance(value, list)
            ):
                return self.format_experience(
                    value
                )  # Already formatted by format_experience
            elif key == "skills" or key == "Skills":
                return self.format_skills(value)  # Already formatted by format_skills
            elif key == "education" and isinstance(value, list):
                return self.format_education(
                    value
                )  # Already formatted by format_education
            elif key == "certifications" and isinstance(value, list):
                return "\n".join(cert["name"] for cert in value)
            # Handle name, email, phone_1, and phone_2 with `template_type` logic
            if key in ["name", "email", "phone_1", "phone_2"]:
                if template_type == "code":
                    if key == "name":
                        return "*****"
                    elif key == "email":
                        return "****@gmail.com"
                    elif key in ["phone_1", "phone_2"]:
                        return "****" if key == "phone_1" else "Not provided"
                elif template_type == "name":
                    if key == "name":
                        return data.get("name", "Not provided")
                    elif key == "email":
                        return "**@gmail.com"
                    elif key in ["phone_1", "phone_2"]:
                        return "****" if key == "phone_1" else "Not provided"
            # Fallback for other keys
            return str(value) if value is not None else "Not provided"

        # Replace placeholders in paragraphs
        for paragraph in doc.paragraphs:
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"  # Dynamic placeholder
                if placeholder in paragraph.text:
                    # Replace individual placeholders
                    paragraph.text = paragraph.text.replace(
                        placeholder, convert_value(key, value)
                    )

        # Replace placeholders in tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for key, value in data.items():
                        placeholder = f"{{{{{key}}}}}"  # Dynamic placeholder
                        if placeholder in cell.text:
                            cell.text = cell.text.replace(
                                placeholder, convert_value(key, value)
                            )

        # Add combined `personal_info` to the document
        combined_personal_info = add_personal_info(data, template_type)
        for paragraph in doc.paragraphs:
            if "{{personal_info}}" in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    "{{personal_info}}", combined_personal_info
                )

    def fill_cv_template(self, data, output_path, template_type):
        try:
            # Load the template document
            template_path = os.path.join(app.root_path, "template.docx")
            doc = Document(template_path)

            # Replace placeholders with actual data
            self.replace_placeholders(doc, data, template_type)

            # Create the output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            os.makedirs(output_dir, exist_ok=True)

            # Save the document
            doc.save(output_path)
            logging.debug(f"Document created: {output_path}")
        except Exception as e:
            logging.error(f"Error filling the template: {e}")

    # Update the individual functions to use the refactored function
    def fill_template(self, data, output_path):
        self.fill_cv_template(data, output_path, template_type="normal")

    def fill_coded_template(self, data, output_path):
        self.fill_cv_template(data, output_path, template_type="code")

    def fill_name_template(self, data, output_path):
        self.fill_cv_template(data, output_path, template_type="name")
