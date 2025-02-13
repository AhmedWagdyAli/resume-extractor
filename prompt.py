import requests
import json
import re


class DeepSeekPrompt:
    def __init__(self):
        self.url = "https://api.deepinfra.com/v1/openai/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer Xp0HxdNqIlrWfQhMRzEPchU5KDx1cZ0F",
        }

    def prompt(self, user_prompt):
        json_format = {
            "job_title": "",
            "years_of_experience": "",
            "skills": "",
            "company": "",
            "format": "",
            "certificates": "",
        }
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            "messages": [
                {
                    "role": "system",
                    "content": f"Can you parse through this text for me and extract it into {json_format} and return the JSON under the 'json' key?",
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
            print(content)

            # Extract JSON using regex
            match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if match:
                json_data = json.loads(match.group(1))  # Parse extracted JSON
                return json_data["json"]
            else:
                print("No JSON found.")

        else:
            response.raise_for_status()


def main():
    user_prompt = input("Enter your prompt: ")
    deepSeek = DeepSeekPrompt()
    result = deepSeek.prompt(user_prompt)
    print(result)
    """  if result:
        print(json.dumps(result, indent=2))
    else:
        print("No valid JSON response received.") """


if __name__ == "__main__":
    main()
