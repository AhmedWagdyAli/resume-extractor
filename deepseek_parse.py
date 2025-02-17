import requests
import json
import re

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
            "Authorization": "Bearer 8wJ9bPrW1FrPgyR0orndCIrpjujezzec",
        }

    def invoke(self, input_text):
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            "messages": [
                {
                    "role": "system",
                    "content": f"Can you parse through this text for me and extract it into {json_content} and return the JSON under the 'json' key?",
                },
                {
                    "role": "user",
                    "content": input_text,
                },
            ],
        }

        response = requests.post(self.url, headers=self.headers, json=payload)

        if response.status_code == 200:
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]

            # Extract JSON using regex
            match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if match:
                json_data = json.loads(match.group(1))  # Parse extracted JSON
                return json_data["json"]
            else:
                print("No JSON found.")
                return None
        else:
            response.raise_for_status()
