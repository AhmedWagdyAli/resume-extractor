import logging
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
    send_file,
    flash,
    jsonify,
    flash,
    session,
    send_from_directory,
)
import time
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
    JobTitle,
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
from prompt import DeepSeekPrompt
from deepseek_parse import DeepSeekInputData as DeepSeekInput
from chatgpt_service import ChatGPTInputData as ChatGPT
from dotenv import load_dotenv
from service_switcher import ServiceSwitcher

load_dotenv()
app = Flask(__name__)

redis_conn = Redis(host="localhost", port=6379)  # Connect to Redis--
queue = Queue(connection=redis_conn, default_timeout=600)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config["TEMPLATE_FOLDER"] = "./templates"  # For Word templates
app.config["OUTPUT_FOLDER"] = "./output"  # For filled CVs
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
)
""" app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://cvflask_user:yourpassword@localhost:3306/cvflask"
) """
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "supersecret"
db.init_app(app)
migrate = Migrate(app, db)

# Ensure directories exist
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["OUTPUT_FOLDER"], exist_ok=True)


def create_app():
    app = Flask(__name__)

    redis_conn = Redis(host="localhost", port=6379)  # Connect to Redis
    queue = Queue(connection=redis_conn, default_timeout=600)
    app.config["UPLOAD_FOLDER"] = "./uploads"
    app.config["TEMPLATE_FOLDER"] = "./templates"  # For Word templates
    app.config["OUTPUT_FOLDER"] = "./output"  # For filled CVs
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
    )

    """     app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+mysqlconnector://cvflask_user:yourpassword@localhost:3306/cvflask"
    ) """
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.secret_key = "supersecret"
    db.init_app(app)

    return app  # Return the Flask app instance


@app.route("/", methods=["get"])
def get_cv_form():
    return render_template("/upload.html")


@app.route("/upload_multiple", methods=["GET"])
def upload_multiple_form():
    return render_template("upload_multiple.html")


@app.route("/cvs")
def cv_list():
    cvs = CV.query.all()
    return render_template("cvs.html", cvs=cvs)


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

    parsed_data = ServiceSwitcher.parseService(text)

    """     chatgpt = ChatGPT()
    data = chatgpt.invoke(text)
    print(data) """
    """  try:
        parsed_data = json.loads(data)

    except json.JSONDecodeError:
        print("Error: Data is not valid JSON.") """

    job_title = parsed_data.get("job_title", "No job title")
    # initials = "".join([name[0] for name in parsed_data.get("name") if name])
    today_date = time.strftime("%Y%m%d")
    unique_filename = f"{today_date}_{job_title}.docx"
    path = os.path.join(app.root_path, "output", unique_filename)
    path_of_coded_cv = os.path.join(app.root_path, "output", f"coded_{unique_filename}")
    path_of_named_cv = os.path.join(app.root_path, "output", f"name_{unique_filename}")

    try:
        parsed_data["path_of_cv"] = path
        parsed_data["path_of_coded_cv"] = path_of_coded_cv
        parsed_data["path_of_named_cv"] = path_of_named_cv
        parsed_data["path_of_original_cv"] = upload_path
    except json.JSONDecodeError:
        print("Error: Data is not valid JSON.")
    service = CVService(db)
    service.save_cv(parsed_data)
    # Generate a unique filename for the document
    fill_template(
        parsed_data, os.path.join(app.config["OUTPUT_FOLDER"], unique_filename)
    )
    fill_coded_template(
        parsed_data,
        os.path.join(app.config["OUTPUT_FOLDER"], f"coded_{unique_filename}"),
    )
    fill_name_template(
        parsed_data,
        os.path.join(app.config["OUTPUT_FOLDER"], f"name_{unique_filename}"),
    )
    flash("Operation successful!", "success")  # "success" is the category

    return render_template("generate.html")


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
        valid_formats = ["code", "name"]
        if format not in valid_formats:
            flash("Invalid format specified", "danger")
            return render_template("generate.html")

        # Ensure at least one filter is provided
        if not job_title and not company and not min_experience and not skill:
            flash("At least one filter is required", "danger")
            return render_template("generate.html")

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
                flash("Invalid value for years_of_experience", "danger")
                return render_template("generate.html")

        if skill:
            skill_list = [s.strip() for s in skill.split(",")]
            if skill_list:
                skill_filters = [Skills.name.ilike(f"%{s}%") for s in skill_list]
                query = query.filter(or_(*skill_filters))

        # Fetch results
        cvs = query.all()

        if not cvs:
            flash("No CVs found with the given criteria", "danger")
            return render_template("generate.html")

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
            flash("No valid CV files found on the server", "danger")
            return render_template("generate.html")

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
        flash("An error occurred while generating CVs", "danger")
        return render_template("generate.html")


@app.route("/prompt", methods=["GET"])
def generate_prompt_form():
    return render_template("/prompt.html")


@app.route("/prompt_cv", methods=["POST"])
def get_prompt_data():
    try:
        # Process incoming prompt and ChatGPT response
        text = request.form.get("prompt")
        # Load settings from file
        settings = load_settings()
        search_by_generated_job_titles = settings["configurations"]["setting2"]
        search_by_generated_skills = settings["configurations"]["setting3"]
        exact_search = settings["configurations"]["setting4"]
        # this switches LLM model based on setting, parse the text and return the parsed data
        parsed_data = ServiceSwitcher.togglePromptService(text)
        print(parsed_data)
        """  try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError:
            flash("Error: Data is not valid JSON.", "danger")
            return render_template("cvs.html") """

        # Extract parameters from parsed_data
        job_title = parsed_data.get("job_title")
        company = parsed_data.get("company")
        min_experience_str = parsed_data.get("years_of_experience", "")
        skill = parsed_data.get("skills")
        fmt = (parsed_data.get("format") or "").lower()
        filter_by = parsed_data.get("not")
        min_experience = extract_experience(min_experience_str)

        # Normalize format
        valid_formats = ["blind", "blind with name", "blind_with_name"]
        fmt = fmt if fmt in valid_formats else "normal"

        # Build the initial query
        query = build_initial_query(
            job_title, company, min_experience, skill, filter_by, exact_search
        )
        cvs = query.all()

        # Fallback: Search by generated titles if no CVs found
        if not cvs:
            cvs = fallback_search_titles(
                parsed_data, job_title, search_by_generated_job_titles
            )
        # Fallback: Search by generated skills if still no CVs and setting enabled
        if not cvs and search_by_generated_skills.lower() == "true":
            cvs = fallback_search_skills(parsed_data)

        if not cvs:
            flash("No CVs found with the given criteria", "danger")
            return render_template("cvs.html")

        # Determine valid files based on desired format
        valid_files = get_valid_files(cvs, fmt)
        if not valid_files:
            flash("No valid CV files found on the server", "danger")
            return render_template("cvs.html")

        return render_template("cvs.html", cvs=cvs)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        flash("An error occurred while generating CVs", "danger")
        return render_template("cvs.html")


def load_settings():
    """Load settings from the settings.json file."""
    settings_path = os.path.join(app.root_path, "settings.json")
    with open(settings_path, "r") as file:
        return json.load(file)


def extract_experience(experience_str):
    """Extracts the first integer found in the experience string."""
    matches = re.findall(r"\d+", experience_str)
    return int(matches[0]) if matches else 0


def build_initial_query(
    job_title, company, min_experience, skill, filter_by, exact_search
):
    """Build the base query with filters for job title, company, experience, and skills."""
    query = CV.query.join(Experiences).join(Skills).filter(CV.path_of_cv.isnot(None))

    if job_title:
        if exact_search == "True":
            query = query.filter(CV.job_title == job_title)
        else:
            query = query.filter(CV.job_title.ilike(f"%{job_title}%"))

    if company:
        query = query.filter(Experiences.organisation_name.ilike(f"%{company}%"))

    if min_experience:
        try:
            query = query.filter(CV.years_of_experience >= int(min_experience))
        except ValueError:
            flash("Invalid value for years_of_experience", "danger")
            return render_template("cvs.html")

    if skill:
        skill_filters = [Skills.name.ilike(f"%{s}%") for s in skill]
        query = query.filter(or_(*skill_filters))

    if filter_by:
        query = query.filter(CV.job_title != filter_by)

    return query


def fallback_search_titles(parsed_data, job_title, search_by_generated_job_titles):
    """Perform fallback search using generated job titles if enabled."""
    cvs = []
    if search_by_generated_job_titles.lower() == "true":
        generated_titles = parsed_data.get("generated_titles", [])
        if generated_titles:
            # Search for job_title in the JobTitle table
            query = (
                CV.query.join(Experiences, CV.id == Experiences.cv_id)
                .join(Skills, CV.id == Skills.cv_id)
                .join(JobTitle, CV.id == JobTitle.cv_id)
                .filter(CV.path_of_cv.isnot(None))
                .filter(or_(JobTitle.title.ilike(f"%{job_title}%")))
            )
            cvs = query.all()
            if not cvs:
                # Fallback: search generated_titles in CV.job_title field
                query = query.filter(
                    or_(
                        *(
                            CV.job_title.ilike(f"%{title}%")
                            for title in generated_titles
                        )
                    )
                )
                cvs = query.all()
    return cvs


def fallback_search_skills(parsed_data):
    """Perform fallback search using generated skills if available."""
    generated_skills = parsed_data.get("generated_skills", [])
    if generated_skills:
        skill_filters = [Skills.name.ilike(f"%{s}%") for s in generated_skills]
        query = CV.query.join(Skills).filter(or_(*skill_filters))
        return query.all()
    return []


def get_valid_files(cvs, fmt):
    """Determine valid CV files based on the selected format."""
    if fmt == "normal":
        return [
            cv.path_of_cv
            for cv in cvs
            if cv.path_of_cv and os.path.isfile(cv.path_of_cv)
        ]
    elif fmt == "blind":
        return [
            cv.path_of_coded_cv
            for cv in cvs
            if cv.path_of_coded_cv and os.path.isfile(cv.path_of_coded_cv)
        ]
    else:  # For "blind with name" or "blind_with_name"
        return [
            cv.path_of_named_cv
            for cv in cvs
            if cv.path_of_named_cv and os.path.isfile(cv.path_of_named_cv)
        ]


@app.route("/download/<filename>")
def download_file(filename):
    # Check if the file exists in the output directory
    output_directory = os.path.join(app.root_path, "output")
    output_file_path = os.path.join(output_directory, filename)

    if os.path.exists(output_file_path):
        return send_file(output_file_path, as_attachment=True)

    # Check if the file exists in the uploads directory
    uploads_directory = os.path.join(app.root_path, "uploads")
    uploads_file_path = os.path.join(uploads_directory, filename)

    if os.path.exists(uploads_file_path):
        return send_file(uploads_file_path, as_attachment=True)

    # If the file is not found in either directory, return an error
    flash("File not found", "danger")


""" @app.route("/upload_cvs", methods=["POST"])
def upload_cvs():
    from tasks import Tasks  # Local import to avoid circular import

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
        job = queue.enqueue(Tasks.parse_cv, file_name, file_content)
        jobs.append({"job_id": job.id, "filename": file_name})

    return jsonify({"message": "Files uploaded successfully.", "jobs": jobs}), 200
"""


@app.route("/upload_cvs", methods=["POST"])
def upload_cvs():
    from tasks import Tasks  # Local import to avoid circular import

    if "files[]" not in request.files:
        flash("No files provided", "danger")
    files = request.files.getlist("files[]")
    if not files:
        flash("No files provided", "danger")
    jobs = []
    job_ids = []

    for file in files:
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(upload_path)  # Save the file to the upload folder

        with open(upload_path, "rb") as file_content:
            file_data = file_content.read()  # Get the binary content
            # Enqueue the parsing task
            job = queue.enqueue(Tasks.parse_cv, filename, file_data)
            logging.info(f"Enqueued job {job.id} for file {filename}")
            job_ids.append(job.id)

            jobs.append({"job_id": job.id, "filename": filename})
    redis_conn.set("pending_jobs", len(job_ids))

    flash("Files uploaded successfully", "success")
    return jsonify({"message": "Files uploaded successfully.", "jobs": jobs}), 200


@app.route("/job_status/<job_id>", methods=["GET"])
def job_status(job_id):
    """
    Check the status of a specific job.
    """
    job = queue.fetch_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found"}), 404

    return jsonify({"job_id": job.id, "status": job.get_status()}), 200


""" from rq.job import Job


@app.route("/check_jobs", methods=["GET"])
def check_jobs():
    pending_jobs = int(redis_conn.get("pending_jobs") or 0)

    # If all jobs are done, reset the counter and notify the client
    if pending_jobs <= 0:
        return jsonify({"status": "done"})

    return jsonify({"status": "processing", "pending": pending_jobs})
"""


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


def format_skills(skills_text):
    if not skills_text or not isinstance(skills_text, list):
        return "N/A"
    skills_list = [skill.strip() for skill in skills_text]
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
        if (
            key == "professional_experience"
            or key == "projects"
            and isinstance(value, list)
        ):
            return format_experience(value)  # Already formatted by format_experience
        elif key == "skills" or key == "Skills":
            return format_skills(value)  # Already formatted by format_skills
        elif key == "education" and isinstance(value, list):
            return format_education(value)  # Already formatted by format_education
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


import zipfile
from io import BytesIO


@app.route("/download_zip", methods=["POST"])
def download_zip():
    try:
        data = request.get_json()
        selected_ids = data.get("ids", [])
        file_type = data.get("file_type", "full")

        if not selected_ids:
            flash("No CVs selected.", "danger")
            return render_template("cvs.html")
        # Fetch the selected CVs from the database
        cvs = CV.query.filter(CV.id.in_(selected_ids)).all()

        if not cvs:
            flash("No CVs found with the given IDs.", "danger")
            return render_template("cvs.html")

        # Create a ZIP file in memory
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cv in cvs:
                if file_type == "full" and cv.path_of_cv:
                    file_path = cv.path_of_cv
                elif file_type == "blind" and cv.path_of_coded_cv:
                    file_path = cv.path_of_coded_cv
                elif file_type == "named" and cv.path_of_named_cv:
                    file_path = cv.path_of_named_cv
                elif file_type == "original" and cv.path_of_original_cv:
                    file_path = cv.path_of_original_cv
                else:
                    continue

                if file_path and os.path.isfile(file_path):
                    zip_file.write(file_path, os.path.basename(file_path))

        # Send the ZIP file for download
        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="cvs.zip",
        )

    except Exception as e:
        flash("An error occurred while downloading CVs", "danger")
        return render_template("cvs.html")


@app.route("/delete_selected", methods=["POST"])
def delete_selected():
    try:
        data = request.get_json()
        selected_ids = data.get("ids", [])

        if not selected_ids:
            flash("No CVs selected.", "danger")
            return render_template("cvs.html")
        # Fetch the selected CVs from the database
        cvs = CV.query.filter(CV.id.in_(selected_ids)).all()

        if not cvs:
            flash("No CVs found with the given IDs.", "danger")
            return render_template("cvs.html")
        # Delete the selected CVs
        for cv in cvs:
            db.session.delete(cv)
        db.session.commit()

        flash("Selected CVs deleted successfully.", "success")
        return render_template("cvs.html")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        flash("An error occurred while deleting CVs", "danger")
        return render_template("cvs.html")


@app.route("/settings", methods=["GET"])
def display_settings():
    try:
        settings_path = os.path.join(app.root_path, "settings.json")
        with open(settings_path, "r") as file:
            settings = json.load(file)
        return render_template("settings.html", settings=settings["configurations"])
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        flash("An error occurred while loading settings.", "danger")
        return redirect(url_for("get_cv_form"))


@app.route("/update_settings", methods=["POST"])
def update_settings():
    try:
        settings_path = os.path.join(app.root_path, "settings.json")
        with open(settings_path, "r") as file:
            settings = json.load(file)

        settings["configurations"]["LLM_Model"] = request.form.get("LLM_Model")
        settings["configurations"]["setting2"] = request.form.get("setting2")
        settings["configurations"]["setting3"] = request.form.get("setting3")
        settings["configurations"]["setting4"] = request.form.get("setting4")

        with open(settings_path, "w") as file:
            json.dump(settings, file, indent=4)

        flash("Settings updated successfully!", "success")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        flash("An error occurred while updating settings.", "danger")

    return redirect(url_for("display_settings"))


if __name__ == "__main__":

    app.secret_key = "supersecretkey"  # Needed for flash messages
    app.run(debug=True)
