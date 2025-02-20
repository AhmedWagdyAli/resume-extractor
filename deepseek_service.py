import requests
import json
import re
import os
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
    "applied_for_profile": "",
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
        self.url = "https://api.deepinfra.com/v1/openai/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + deepseek_api_key,
        }

    def invoke(self, input_text):
        # for backward compatibility, you can still use `https://api.deepseek.com/v1` as `base_url`.
        client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
        system_content = (
            f"Can you parse through this text for me and extract it into {json_content} and return the JSON under the 'json' key?",
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

        return response.choices[0].message.content


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
