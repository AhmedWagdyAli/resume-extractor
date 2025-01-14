from docx import Document


class CVProcessor:
    def __init__(self):
        self.doc = Document()

    def add_section(self, title, items, bullet_points=False):
        self.doc.add_heading(title, level=1)
        if isinstance(items, list):
            for item in items:
                self.doc.add_paragraph(
                    item, style="List Bullet" if bullet_points else None
                )
        elif isinstance(items, dict):
            for key, value in items.items():
                self.doc.add_paragraph(f"{key}: {value}")
        else:
            self.doc.add_paragraph(items)

    def fill_template(self, data, output_path):
        try:
            # Adding sections to the document
            # 1. Personal Information
            self.doc.add_heading("Personal Information", level=1)
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
                self.doc.add_paragraph(info)

            # 2. Skills (added as bullet points)
            self.add_section("Skills", data["skills"], bullet_points=True)

            # 3. Education
            self.add_section("Education", data["education"])

            # 4. Professional Experience
            self.add_section("Professional Experience", data["professional_experience"])

            # Save the document
            self.doc.save(output_path)
            print(f"Document created: {output_path}")
        except Exception as e:
            print(f"Error filling the template: {e}")


if __name__ == "__main__":
    data = {
        "name": "Student Name",
        "email": "",
        "phone_1": "1234567890",
        "phone_2": "",
        "address": "",
        "city": "",
        "linkedin": "",
        "professional_experience_in_years": "0",
        "highest_education": "B.Tech",
        "is_fresher": "yes",
        "is_student": "yes",
        "applied_for_profile": "",
        "skills": ["Python", "Java", "C++"],
        "education": {
            "Degree": "B.Tech",
            "Branch": "Computer Science",
            "College": "ABC College",
            "University": "XYZ University",
            "Year of Graduation": "2022",
        },
        "professional_experience": {
            "Company": "ABC Company",
            "Role": "Software Developer",
            "Duration": "6 months",
            "Location": "City",
            "Description": "Worked on Python projects",
        },
    }
    template_helper = CVProcessor()
    template_helper.fill_template(data=data, output_path="candidate_profile.docx")
