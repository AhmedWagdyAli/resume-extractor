import requests
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

chatgpt_api_key = os.getenv("Chatgpt_API_key")
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
            "profile": "",
            "total_of_years_spent_at_job": ""
        }},
        {{
            "organisation_name": "",
            "duration": "",
            "profile": "",
            "total_of_years_spent_at_job": ""

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
    "projects":[
        {{
            "item":"",
            "duration_of_project":"" ,
            "description":"",    
        }},
        {{
            "item":"",
            "duration_of_project":"" ,
            "description":"",    
        }}
    ]
}}"""


class ChatGPTInputData:
    def __init__(self):
        self.url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {chatgpt_api_key}",
        }

    def invoke(self, input_text):
        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": f"Can you parse through this text for me and extract it into {json_content} and return the JSON under the 'json' key. dont extract years of experience from the text, calculate the years of experience from the work experience duration. and if you encounter present it means today date",
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
            return content
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

    def prompt(self, user_prompt):
        json_format = json.dumps(
            {
                "job_title": "",
                "years_of_experience": "",
                "skills": [],
                "company": "",
                "format": "",
                "certificates": [],
            }
        )

        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": f"Can you parse through this text for me and extract it into {json_format}",
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
        }

        response = requests.post(self.url, headers=self.headers, json=payload)

        if response.status_code == 200:
            response_json = response.json()
            content = response_json["choices"][0]["message"]["content"]
            return content


if __name__ == "__main__":

    api_key = chatgpt_api_key
    url = "https://api.openai.com/v1/chat/completions"

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {
        "model": "gpt-4-turbo",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Tell me a joke."},
        ],
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        print(
            response.json()["choices"][0]["message"]["content"]
        )  # Print AI's response
    else:
        print("Error:", response.status_code, response.text)
