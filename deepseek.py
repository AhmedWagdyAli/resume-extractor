import requests
import json
import re

# Define the API endpoint and headers
url = "https://api.deepinfra.com/v1/openai/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 9s9e2oJ8JPTejnsG4lFexPHPK0MpEnGS",  # Be careful about exposing API keys.
}

# Define the payload
payload = {
    "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
    "messages": [
        {
            "role": "system",
            "content": "Can you parse through this text for me and extract it into JSON format with keys of job_title, skills, company, and certificates, and return the JSON under the 'json' key?",
        },
        {
            "role": "user",
            "content": "Project manager with 8 years of experience in normal format with skills of PHP and team leading who worked in Asgatech.",
        },
    ],
}


def main():
    # Make the POST request
    response = requests.post(
        url, headers=headers, json=payload
    )  # `json=payload` automatically converts to JSON

    # Check if the request was successful
    if response.status_code == 200:
        # Parse response JSON
        response_json = response.json()

        # Extract the assistant's message content
        content = response_json["choices"][0]["message"]["content"]

        # Extract JSON using regex
        match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
        if match:
            json_data = json.loads(match.group(1))  # Parse extracted JSON
            print(
                json.dumps(json_data["json"], indent=2)
            )  # Extract only the `json` key
        else:
            print("No JSON found.")
    else:
        print(f"Request failed with status code {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    main()
