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

    try:
        data = json.loads(data)
        data["certificates"] = certificates
        # data["projects"] = projects
        data["path_of_cv"] = path

    except json.JSONDecodeError:
        print("Error: Data is not valid JSON.")
    service = CVService(db)
    id = service.save_cv(data)
    # Generate a unique filename for the document
    fill_template(data, unique_filename)
    # fill_template(data, os.path.join("document.docx"))
    return data
    """  # Send the file
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
    # Query the CV table by job_title
    try:
        # Extract job title from the form data
        job_title = request.form.get("job_title")
        company = request.form.get("company")
        min_experience = request.form.get("years_of_experience")
        skill = request.form.get("skill")

        # Check if all inputs are empty
        if not job_title and not company and not min_experience and not skill:
            return jsonify({"error": "At least one filter is required"}), 400

        # Query CV data
        query = (
            CV.query.join(Experiences).join(Skills).filter(CV.path_of_cv.isnot(None))
        )

        if job_title:
            query = query.filter(CV.job_title.ilike(f"%{job_title}%"))

        if company:
            query = query.filter(Experiences.organisation_name.ilike(f"%{company}%"))

        if min_experience is not None:
            query = query.filter(CV.years_of_experience >= min_experience)

        if skill:
            query = query.filter(Skills.name.ilike(f"%{skill}%"))

        cvs = query.all()

        if not cvs:
            return jsonify({"error": "No CVs found with the given criteria"}), 404

        # Filter valid file paths
        valid_files = [cv.path_of_cv for cv in cvs if os.path.isfile(cv.path_of_cv)]

        if not valid_files:
            return jsonify({"error": "No valid CV files found on the server"}), 404

        # Create an in-memory ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in valid_files:
                # Add files to the ZIP archive
                zip_file.write(file_path, os.path.basename(file_path))

        # Prepare the ZIP file for download
        zip_buffer.seek(0)  # Move the cursor to the beginning of the buffer
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="matching_cvs.zip",
        )

    except Exception as e:
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
        upload_path = os.path.join(app.root_path, "output", output_path)

        doc.save(upload_path)
        print(f"Document created: {output_path}")
    except Exception as e:
        print(f"Error filling the template: {e}")


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
