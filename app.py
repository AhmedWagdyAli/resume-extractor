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
from cv_processor import CVProcessor

load_dotenv()
app = Flask(__name__)

redis_conn = Redis(host="localhost", port=6379)  # Connect to Redis--
queue = Queue(connection=redis_conn, default_timeout=600)
app.config["UPLOAD_FOLDER"] = "./uploads"
app.config["TEMPLATE_FOLDER"] = "./templates"  # For Word templates
app.config["OUTPUT_FOLDER"] = "./output"  # For filled CVs
""" app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
) """
app.config["SQLALCHEMY_DATABASE_URI"] = (
    "mysql+mysqlconnector://cvflask_user:yourpassword@localhost:3306/cvflask"
)
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
    """     app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+mysqlconnector://cvflask_user:password@localhost:3306/cvflask"
    ) """

    app.config["SQLALCHEMY_DATABASE_URI"] = (
        "mysql+mysqlconnector://cvflask_user:yourpassword@localhost:3306/cvflask"
    )
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
        if any(keyword in line for keyword in keywords):
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

    file = request.files["file"]
    filename = secure_filename(file.filename)

    # Define the upload path (keep the original filename with its extension)
    upload_path = os.path.join(app.root_path, "uploads", filename)
    # Save the uploaded file to the target path
    file.save(upload_path)
    # Process the CV
    text = ExtractText.extract_based_on_extension(upload_path)

    parsed_data = ServiceSwitcher.parseService(text)

    # print(parsed_data)
    job_title = parsed_data.get("job_title", "No job title")
    initials = "".join(
        [name[0].upper() for name in parsed_data.get("name", "").split() if name]
    )
    today_date = time.strftime("%Y%m%d")
    unique_filename = f"{initials}_{today_date}_{job_title}.docx"
    path = os.path.join(app.root_path, "output", f"F_{unique_filename}")
    path_of_coded_cv = os.path.join(app.root_path, "output", f"B_{unique_filename}")
    path_of_named_cv = os.path.join(app.root_path, "output", f"BN_{unique_filename}")

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
    cv_processor = CVProcessor()
    cv_processor.fill_template(
        parsed_data, os.path.join(app.config["OUTPUT_FOLDER"], f"F_{unique_filename}")
    )
    cv_processor.fill_coded_template(
        parsed_data,
        os.path.join(app.config["OUTPUT_FOLDER"], f"B_{unique_filename}"),
    )
    cv_processor.fill_name_template(
        parsed_data,
        os.path.join(app.config["OUTPUT_FOLDER"], f"BN_{unique_filename}"),
    )
    flash("Operation successful!", "success")  # "success" is the category

    return render_template("cvs.html")


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
        if any(keyword in line for keyword in keywords):
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
