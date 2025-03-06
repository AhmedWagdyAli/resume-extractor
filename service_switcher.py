import requests
import json
import os
from chatgpt_service import ChatGPTInputData as ChatGpt
from deepseek_service import DeepSeekInputData as DeepSeek


class ServiceSwitcher:
    @staticmethod
    def toggleService(text):
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        with open(settings_path, "r") as file:
            settings = json.load(file)

        service = settings["configurations"].get("LLM_Model", "chatgpt")

        if service == "chatgpt":
            chatgpt = ChatGpt()
            parsed_text = chatgpt.invoke(input.input_data(text))
            return parsed_text
        elif service == "deepseek":
            deep_seek = DeepSeek()
            parsed_text = deep_seek.invoke(input.input_data(text))
            return parsed_text
