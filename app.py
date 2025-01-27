from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    send_file,
    flash,
    jsonify,
)
import json
from werkzeug.utils import secure_filename
import os
from cv_service import CVService
import random
from models import (
    db,
    CV,
    Certificates,
    Skills,
    Experiences,
)  # Import models from models.py
from flask_migrate import Migrate
from sqlalchemy import or_
import zipfile
from io import BytesIO
from redis import Redis
from rq import Queue
from pdfminer.high_level import extract_text
from json_helper import InputData as input
from docx import Document
import re
from extract_text import ExtractText

app = Flask(__name__)

redis_conn = Redis(host="localhost", port=6379)  # Connect to Redis
queue = Queue(connection=redis_conn)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config["TEMPLATE_FOLDER"] = "./templates"  # For Word templates
app.config["OUTPUT_FOLDER"] = "./output"  # For filled CVs
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)
migrate = Migrate(app, db)
# Ensure directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)


@app.route("/", methods=["get"])
def get_cv_form():
    return render_template("/upload.html")


def extract_text_from_pdf(pdf_path):
    return extract_text(pdf_path)


def extract_certificates(text):
    # Define a broader regex pattern to capture certificate-like phrases
    pattern = r"(?i)\b(certification|certificate|certified|certifications|certificates|cert)\b.*?([A-Za-z0-9\(\)&,\s]+)"
    matches = re.findall(pattern, text, re.IGNORECASE)

    # Parse and clean up the matches
    results = []
    for _, match in matches:
        # Split by commas or 'and' and clean each certificate
        sub_matches = re.split(r",| and ", match)
        results.extend([{"name": sub.strip()} for sub in sub_matches if sub.strip()])

    return results


def extract_projects(text):
    """
    Extract project information from the given CV text.
    """
    # Define keywords related to projects
    keywords = ["project", "projects", "assignment", "assignments"]

    # Split the text into lines for easier processing
    lines = text.splitlines()
    results = []

    for i, line in enumerate(lines):
        # Check if the line contains any project-related keyword
        if any(keyword.lower() in line.lower() for keyword in keywords):
            # Attempt to extract projects in the current line
            projects = extract_project_names(line)
            results.extend(projects)

            # Check the following lines for related information
            for j in range(1, 3):  # Search up to 2 subsequent lines
                if i + j < len(lines) and lines[i + j].strip():
                    projects = extract_project_names(lines[i + j])
                    results.extend(projects)

    # Remove duplicates and clean up results
    unique_results = {proj["name"]: proj for proj in results}.values()
    return list(unique_results)


def extract_project_names(line):
    """
    Extract project names from a given line of text using regex and cleanup.
    """
    pattern = r"(?i)([A-Za-z0-9\(\)&,\s]+(?:Proj|Proj\.)?[A-Za-z0-9\(\)&,\s]*)"
    matches = re.findall(pattern, line)

    # Clean up and return matched projects
    return [{"name": match.strip()} for match in matches if match.strip()]


@app.route("/upload", methods=["POST"])
def upload_cv():
    # Save the uploaded file
    file = request.files["file"]
    filename = secure_filename(file.filename)

    # Define the upload path (keep the original filename with its extension)
    upload_path = os.path.join(app.root_path, "uploads", filename)

    # Save the uploaded file to the target path
    file.save(upload_path)

    # Process the CV
    text = ExtractText.extract_based_on_extension(upload_path)
    # text =extract_text_from_pdf(upload_path)

    llm = input.llm()

    data = llm.invoke(input.input_data(text))
    # return data
    certificates = search_certificates(text)
    # projects = extract_projects(text)
    unique_filename = f"document_{random.randint(1000, 9999)}.docx"
    path = os.path.join(app.root_path, "output", unique_filename)
    path_of_coded_cv = os.path.join(app.root_path, "output", f"coded_{unique_filename}")
    path_of_named_cv = os.path.join(app.root_path, "output", f"name_{unique_filename}")

    try:
        data = json.loads(data)
        data["certificates"] = certificates
        # data["projects"] = projects
        data["path_of_cv"] = path
        data["path_of_coded_cv"] = path_of_coded_cv
        data["path_of_named_cv"] = path_of_named_cv

    except json.JSONDecodeError:
        print("Error: Data is not valid JSON.")
    service = CVService(db)
    id = service.save_cv(data)
    # Generate a unique filename for the document
    fill_template(data, os.path.join(app.config["OUTPUT_FOLDER"], unique_filename))
    fill_coded_template(
        data, os.path.join(app.config["OUTPUT_FOLDER"], f"coded_{unique_filename}")
    )
    fill_name_template(
        data, os.path.join(app.config["OUTPUT_FOLDER"], f"name_{unique_filename}")
    )
    return render_template("generate.html")

    # return data
    """  Send the file
    # return send_file(output_path, as_attachment=True)
    cv_data = service.get_cv(id)
    cv, skills, experiences = cv_data
    return render_template("result.html", cv=cv, skills=skills, experiences=experiences)
    """


@app.route("/generate", methods=["GET"])
def generate_cv_form():
    return render_template("/generate.html")


@app.route("/generate_cv", methods=["POST"])
def get_cv_data():
    try:
        job_title = request.form.get("job_title")
        company = request.form.get("company")
        min_experience = request.form.get("years_of_experience")
        skill = request.form.get("skill")
        format = request.form.get("format")

        # Validate format
        valid_formats = ["normal", "code", "name"]
        if format not in valid_formats:
            return jsonify({"error": "Invalid format specified"}), 400

        # Ensure at least one filter is provided
        if not job_title and not company and not min_experience and not skill:
            return jsonify({"error": "At least one filter is required"}), 400

        # Build query
        query = (
            CV.query.join(Experiences).join(Skills).filter(CV.path_of_cv.isnot(None))
        )

        if job_title:
            query = query.filter(CV.job_title.ilike(f"%{job_title}%"))

        if company:
            query = query.filter(Experiences.organisation_name.ilike(f"%{company}%"))

        if min_experience:
            try:
                min_experience = int(min_experience)
                query = query.filter(CV.years_of_experience >= min_experience)
            except ValueError:
                return jsonify({"error": "Invalid value for years_of_experience"}), 400

        if skill:
            skill_list = [s.strip() for s in skill.split(",")]
            skill_filters = [Skills.name.ilike(f"%{s}%") for s in skill_list]
            query = query.filter(or_(*skill_filters))

        # Fetch results
        cvs = query.all()

        if not cvs:
            return jsonify({"error": "No CVs found with the given criteria"}), 404

        # Select files based on format
        if format == "normal":
            valid_files = [
                cv.path_of_cv
                for cv in cvs
                if cv.path_of_cv and os.path.isfile(cv.path_of_cv)
            ]
        elif format == "code":
            valid_files = [
                cv.path_of_coded_cv
                for cv in cvs
                if cv.path_of_coded_cv and os.path.isfile(cv.path_of_coded_cv)
            ]
        else:  # format == "named"
            valid_files = [
                cv.path_of_named_cv
                for cv in cvs
                if cv.path_of_named_cv and os.path.isfile(cv.path_of_named_cv)
            ]

        if not valid_files:
            return jsonify({"error": "No valid CV files found on the server"}), 404

        # Create ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in valid_files:
                zip_file.write(file_path, os.path.basename(file_path))

        # Send ZIP file for download
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="matching_cvs.zip",
        )

    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/upload_cvs", methods=["POST"])
def upload_cvs():
    if "files[]" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    files = request.files.getlist("files[]")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    jobs = []
    for file in files:
        file_content = file.read()  # Get the binary content
        file_name = file.filename
        # Enqueue the parsing task
        job = queue.enqueue(parse_cv, file_name, file_content)
        jobs.append({"job_id": job.id, "filename": file_name})

    return jsonify({"message": "Files uploaded successfully.", "jobs": jobs}), 200


@app.route("/job_status/<job_id>", methods=["GET"])
def job_status(job_id):
    """
    Check the status of a specific job.
    """
    from rq.job import Job

    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            return jsonify({"status": "completed", "result": job.result}), 200
        elif job.is_failed:
            return jsonify({"status": "failed"}), 500
        else:
            return jsonify({"status": "in progress"}), 202
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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


def add_personal_info(doc, data, coded):

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


def format_experience(experience_list):
    if not isinstance(experience_list, list):
        return "N/A"

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


def format_skills(skills_text):
    if not skills_text or not isinstance(skills_text, str):
        return "N/A"
    skills_list = [skill.strip() for skill in skills_text.split(",")]
    # TODO: insert into database here
    return "\n".join(f"• {skill}" for skill in skills_list if skill)


def format_education(education_list):
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


def replace_placeholders(doc, data, template_type):
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
        if key == "professional_experience" and isinstance(value, list):
            return format_experience(value)  # Already formatted by format_experience
        elif key == "Skills" and isinstance(value, str):
            return format_skills(value)  # Already formatted by format_skills
        elif key == "education" and isinstance(value, list):
            return format_education(value)  # Already formatted by format_education
        elif key == "certificates" and isinstance(value, list):
            return "\n".join(cert["name"] for cert in value)
        # Handle name, email, phone_1, and phone_2 with `template_type` logic
        if key in ["name", "email", "phone_1", "phone_2"]:
            if template_type == "code":
                if key == "name":
                    return "**"
                elif key == "email":
                    return "**@gmail.com"
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


""" def replace_placeholders(doc, data):
    def convert_value(key, value):
        # Skip reprocessing for specific keys
        if key == "professional_experience" and isinstance(value, list):
            return format_experience(value)  # Already formatted by format_experience
        elif key == "skills" and isinstance(value, str):
            return format_skills(value)  # Already formatted by format_skills
        elif key == "education" and isinstance(value, list):
            return format_education(value)  # Already formatted by format_education
        elif key == "certificates" and isinstance(value, list):
            return "\n".join(cert["name"] for cert in value)
        elif isinstance(value, dict):
            # For other dictionaries, convert to key: value format
            return "\n".join(f"{k}: {v}" for k, v in value.items())
        elif isinstance(value, list):
            # For generic lists, join each item as a string
            return "\n".join(str(item) for item in value)
        return str(value)  # For other data types, convert to string

    for paragraph in doc.paragraphs:
        for key, value in data.items():
            placeholder = f"{{{{{key}}}}}"
            # Check for placeholders and process accordingly
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(
                    placeholder, convert_value(key, value)
                )

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, value in data.items():
                    placeholder = f"{{{{{key}}}}}"
                    if placeholder in cell.text:
                        cell.text = cell.text.replace(
                            placeholder, convert_value(key, value)
                        )


try:
    # Load the template document
    template_path = os.path.join(app.root_path, "template.docx")
    doc = Document(template_path)

    # Replace placeholders with actual data
    replace_placeholders(doc, data)

    # Create the output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)

    # Save the document
    doc.save(output_path)
    print(f"Document created: {output_path}")
except Exception as e:
    print(f"Error filling the template: {e}")
"""


def fill_cv_template(data, output_path, template_type):
    try:
        # Load the template document
        template_path = os.path.join(app.root_path, "template.docx")
        doc = Document(template_path)

        # Replace placeholders with actual data
        replace_placeholders(doc, data, template_type)

        # Create the output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)

        # Save the document
        doc.save(output_path)
        print(f"Document created: {output_path}")
    except Exception as e:
        print(f"Error filling the template: {e}")


# Update the individual functions to use the refactored function
def fill_template(data, output_path):
    fill_cv_template(data, output_path, template_type="normal")


def fill_coded_template(data, output_path):
    fill_cv_template(data, output_path, template_type="code")


def fill_name_template(data, output_path):
    fill_cv_template(data, output_path, template_type="name")


def search_certificates(text):
    """
    Search for certificate information in the given CV text.
    """
    # Define keywords related to certifications
    keywords = ["certificate", "certification", "certified", "certifications"]

    # Split the text into lines for easier processing
    lines = text.splitlines()
    results = []

    for i, line in enumerate(lines):
        # Check if the line contains any certification-related keyword
        if any(keyword.lower() in line.lower() for keyword in keywords):
            # Attempt to extract certificates in the current line
            certificates = extract_certificate_names(line)
            results.extend(certificates)

            # Check the following lines for related information
            for j in range(1, 3):  # Search up to 2 subsequent lines
                if i + j < len(lines) and lines[i + j].strip():
                    certificates = extract_certificate_names(lines[i + j])
                    results.extend(certificates)

    # Remove duplicates and clean up results
    unique_results = {cert["name"]: cert for cert in results}.values()
    return list(unique_results)


def extract_certificate_names(line):
    """
    Extract certificate names from a given line of text using regex and cleanup.
    """
    pattern = r"(?i)([A-Za-z0-9\(\)&,\s]+(?:Cert|Cert\.)?[A-Za-z0-9\(\)&,\s]*)"
    matches = re.findall(pattern, line)

    # Clean up and return matched certificates
    return [{"name": match.strip()} for match in matches if match.strip()]


if __name__ == "__main__":

    app.secret_key = "supersecretkey"  # Needed for flash messages
    app.run(debug=True)
