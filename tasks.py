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
from chatgpt_service import ChatGPTInputData as ChatGPT
import time
import logging
from redis import Redis
from service_switcher import ServiceSwitcher

# Configure logging
logging.basicConfig(level=logging.DEBUG)

redis_conn = Redis()


class Tasks:

    @staticmethod
    def parse_cv(file_name, file_content):
        app = create_app()  # Create an instance of your Flask app

        # Secure the file name
        filename = secure_filename(file_name)
        logging.debug(f"Processing file: {filename}")
        # Define the upload path
        upload_path = os.path.join("uploads", filename)

        with open(upload_path, "wb") as f:
            f.write(file_content)

        text = ExtractText.extract_based_on_extension(upload_path)

        if not text:
            raise Exception("Error processing CV.")
        """  chatgpt = ChatGPT()
        data = chatgpt.invoke(input.input_data(text))
        logging.debug(f"Data received from ChatGPT: {data}") """
        parsed_data = ServiceSwitcher.parseService(text)

        if not isinstance(parsed_data, dict):
            try:
                parsed_data = json.loads(parsed_data)
                logging.debug(f"Data received from service: {parsed_data}")
            except json.JSONDecodeError as e:
                logging.error(f"Error decoding JSON: {e}")
        # Define the output directory for the filled CV
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        today_date = time.strftime("%Y%m%d")
        unique_filename = f"{today_date}.docx"
        path = os.path.join(app.root_path, "output", unique_filename)
        path_of_coded_cv = os.path.join(app.root_path, "output", f"B_{unique_filename}")
        path_of_named_cv = os.path.join(app.root_path, "output", f"BN{unique_filename}")

        logging.debug(f"Output paths: {path}, {path_of_coded_cv}, {path_of_named_cv}")

        # Fill the template with parsed data
        processor = CVProcessor()
        processor.fill_template(parsed_data, path)
        processor.fill_coded_template(parsed_data, path_of_coded_cv)
        processor.fill_name_template(parsed_data, path_of_named_cv)

        parsed_data["path_of_cv"] = path
        parsed_data["path_of_coded_cv"] = path_of_coded_cv
        parsed_data["path_of_named_cv"] = path_of_named_cv
        parsed_data["path_of_original_cv"] = upload_path

        # Save parsed data to the database
        with app.app_context():  # Ensure DB operations run within Flask's context
            service = CVService(db)
            service.save_cv(parsed_data)

        # Check if the output file was created
        if not os.path.exists(path):
            logging.error(f"Output file not found at path: {path}")
            raise Exception("Error: Output file not found.")
        redis_conn.decr("pending_jobs")
        return {"status": "success", "output_path": path}
