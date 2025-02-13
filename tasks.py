import os
import json
from werkzeug.utils import secure_filename
from models import db
from cv_service import CVService
from extract_text import ExtractText
from cv_processor import CVProcessor
from json_helper import InputData as input
from flask import Flask
from app import create_app


class Tasks:

    @staticmethod
    def parse_cv(file_name, file_content):
        app = create_app()  # Create an instance of your Flask app

        # Secure the file name
        filename = secure_filename(file_name)

        # Define the upload path
        upload_path = os.path.join("uploads", filename)

        with open(upload_path, "wb") as f:
            f.write(file_content)

        text = ExtractText.extract_based_on_extension(upload_path)

        if not text:
            raise Exception("Error processing CV.")
        llm = input.llm()

        data = llm.invoke(input.input_data(text))

        # Ensure data is a dictionary
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            raise Exception("Error: Data is not valid JSON.")

        # Define the output directory for the filled CV
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Define the output path
        output_path = os.path.join(output_dir, f"filled_{filename}.docx")
        path_of_coded_cv = os.path.join(output_dir, f"coded_{filename}.docx")
        path_of_named_cv = os.path.join(output_dir, f"name_{filename}.docx")

        # Fill the template with parsed data
        processor = CVProcessor()
        processor.fill_template(data, output_path)
        processor.fill_coded_template(data, path_of_coded_cv)
        processor.fill_name_template(data, path_of_named_cv)

        data["path_of_cv"] = output_path
        data["path_of_coded_cv"] = path_of_coded_cv
        data["path_of_named_cv"] = path_of_named_cv

        # Save parsed data to the database
        with app.app_context():  # Ensure DB operations run within Flask's context
            service = CVService(db)
            service.save_cv(data)

        # Check if the output file was created
        if not os.path.exists(output_path):
            raise Exception("Error: Output file not found.")

        return {"status": "success", "output_path": output_path}

