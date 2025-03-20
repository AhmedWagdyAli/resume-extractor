import requests
import json
import re
import os
import logging
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

deepseek_api_key = os.getenv("DeepSeek_API_key")

json_content = """{{
    "name": "",
    "email" : "",
    "phone_1": "",
    "phone_2": "",
    "address": "",
    "city": "",
    "linkedin": "",
    "professional_experience_in_years": "",
    "highest_education": "",
    "is_fresher": "yes/no",
    "is_student": "yes/no",
    "skills": ["",""],
    "job_title": "",
    common_titles:[],
    "education": [
        {{
            "institute_name": "",
            "year_of_passing": "",
            "score": ""
        }},
        {{
            "institute_name": "",
            "year_of_passing": "",
            "score": ""
        }}
    ],
    "professional_experience": [
        {{
            "organisation_name": "",
            "duration": "",
            "profile": ""
        }},
        {{
            "organisation_name": "",
            "duration": "",
            "profile": ""
        }}
    ],
    "certifications": [
        {{
            "name": "",
            "year": ""
        }},
        {{
            "name": "",
            "year": ""
        }}
    ],
}}"""


class DeepSeekInputData:
    def __init__(self):
        self.url = "https://api.deepseek.com"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + deepseek_api_key,
        }

    def invoke(self, input_text):
        # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
        client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        system_content = (
            f"Parse the provided text into structured {json_content}. "
            "Calculate years of experience based on job durations. "
            "Handle 'Present' or 'current' as today's date (February 2025). "
            "Return the result as JSON under the 'json' key."
        )

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": input_text},
            ],
            max_tokens=1024,
            temperature=0.7,
            stream=False,
        )

        # Get and strip the raw content from the API response
        raw_content = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        if raw_content.startswith("```") and raw_content.endswith("```"):
            raw_content = raw_content.strip("`")
            if raw_content.lower().startswith("json"):
                raw_content = raw_content[4:].strip()

        if not raw_content:
            logging.error("DeepSeek API returned an empty response.")
            return {}  # Return an empty dict to avoid NoneType issues

        try:
            parsed_response = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from DeepSeek response: {e}")
            logging.error(f"Raw response content: {raw_content}")
            return {}

        # If the response contains a 'json' key, return its value.
        if "json" in parsed_response:
            result = parsed_response["json"]
            logging.info(f"DeepSeek response JSON: {result}")
            return result
        # Otherwise, check if the response itself appears to follow the expected format.
        elif all(key in parsed_response for key in json_content):
            logging.info(f"DeepSeek response JSON (direct): {parsed_response}")
            return parsed_response
        else:
            logging.error("Expected key 'json' not found in response.")
            logging.error(f"Raw response content: {raw_content}")
            return {}

    def prompt(self, user_prompt):
        json_format = {
            "job_title": "",
            "years_of_experience": "",
            "skills": [],
            "company": "",
            "format": "",
            "certificates": [],
            "not": "",
            "generated_titles": [],
            "generated_skills": [],
        }

        system_instruction = (
            "When extracting 'job_title', infer 'common_titles' based on similar industry roles. "
            "Similarly, infer 'related_skills' from industry standards and common competencies for that job, not from the text itself. "
            f"Ensure the output strictly follows the {json_format}, without deviation."
        )

        client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
        )

        # Get and strip the raw content from the API response
        raw_content = response.choices[0].message.content.strip()

        # Remove markdown code fences if present
        if raw_content.startswith("```") and raw_content.endswith("```"):
            raw_content = raw_content.strip("`")
            if raw_content.lower().startswith("json"):
                raw_content = raw_content[4:].strip()

        if not raw_content:
            logging.error("DeepSeek API returned an empty response.")
            return {}  # Return an empty dict to avoid NoneType issues

        try:
            parsed_response = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON from DeepSeek response: {e}")
            logging.error(f"Raw response content: {raw_content}")
            return {}

        # If the response contains a 'json' key, return its value.
        if "json" in parsed_response:
            result = parsed_response["json"]
            logging.info(f"DeepSeek response JSON: {result}")
            return result
        # Otherwise, check if the response itself appears to follow the expected format.
        elif all(key in parsed_response for key in json_format):
            logging.info(f"DeepSeek response JSON (direct): {parsed_response}")
            return parsed_response
        else:
            logging.error("Expected key 'json' not found in response.")
            logging.error(f"Raw response content: {raw_content}")
            return {}


if __name__ == "__main__":

    # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
    client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        max_tokens=1024,
        temperature=0.7,
        stream=False,
    )

    print(response.choices[0].message.content)
