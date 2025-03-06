import requests
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()

chatgpt_api_key = os.getenv("Chatgpt_API_key")
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
            "profile": "",
            "total_time_spent_at_job":""
        }},
        {{
            "organisation_name": "",
            "duration": "",
            "profile": "",
            "total_time_spent_at_job":""
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
                    "content": (
                        f"Can you parse through this text for me and extract it into {json_content} and return the JSON under the 'json' key. "
                        "Don't extract years of experience from the text, calculate the years of experience from the work experience duration. "
                        "If you encounter 'present' or 'current' it means today's date (February 2025). "
                        "Moreover, make sure the professional_experience_in_years is calculated correctly. "
                        "calculate the difference between two dates of duration and add them to time_spent_at_job and remember current or present means today"
                        "Here are some examples: "
                        "IT Specialist /Namaa (June 2017 /October 2019)  2 years, 4 months. "
                        "Software Developer /Group Banner (October 2019 /April 2020)  6 months. "
                        "Backend Developer /Craft Code (April 2020 /October 2021)  1 year, 6 months. "
                        "Full-Stack Web Developer /Freelancer (October 2021 /Present, February 2025) 3 years, 4 months. "
                        "Now add all of that to calculate the professional_experience_in_years which should be 7 years, 8 months. "
                        "### **Strict Experience Calculation Instructions:**\n"
                        "1. **Extract all jobs and their durations from the provided text.**\n"
                        "   - Example: '.Net Web Developer (Jul 2017 - Jun 2018)' → ✅ Include\n"
                        "   - Example: 'Back End Developer (Nov 2021 - Present)' → ✅ Include (Present = today)\n"
                        "   - Example: '+2 years experience' → ❌ Ignore (Not based on job dates)\n"
                        "\n"
                        "2. **Handle 'Present' or 'current' correctly.**\n"
                        "   - If 'Present' or 'current' appears, assume today's date (February 2025) for calculations.\n"
                        "\n"
                        "3. **Sum all extracted durations correctly.**\n"
                        "   - Example Calculation:\n"
                        "     - .Net Web Developer (Jul 2017 - Jun 2018) → 1 year.\n"
                        "     - Back End Developer (Nov 2021 - Present) → 3 years, 4 months.\n"
                        "   - **Final total: 4 years, 4 months.**\n"
                        "\n"
                        "4. **Extract job_title from the 'About' section or the 'Contact' section if available.**\n"
                        "\n"
                        "5. **when you are extracting job titles to add common titles related to the job title.**\n"
                        "\n"
                        "6. **Return output as JSON under the key 'json'.**\n"
                        "   - The key 'professional_experience_in_years' must match the correct total.\n"
                        "\n"
                        "**IMPORTANT: DOUBLE CHECK before finalizing. The total must be accurate.**"
                    ),
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
                "not": "",
                "common_titles": [],
                "related_skills": [],
            }
        )

        payload = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": "When extracting 'job_title', infer 'common_titles' based on similar industry roles. Similarly, infer 'related_skills' from industry standards and common competencies for that job, not from the text itself."
                    f"Ensure the output strictly follows the {json_format}, without deviation.",
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
