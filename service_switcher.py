import requests
import json
import os
from chatgpt_service import ChatGPTInputData as ChatGpt
from deepseek_service import DeepSeekInputData as DeepSeek
import logging


class ServiceSwitcher:
    @staticmethod
    def parseService(text):
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        with open(settings_path, "r") as file:
            settings = json.load(file)

        service = settings["configurations"].get("LLM_Model", "chatgpt").lower()

        if service == "chatgpt":
            chatgpt = ChatGpt()
            data = chatgpt.invoke(text)
            logging.debug(f"Data received from ChatGPT: {data}")
            return data
        elif service == "deepseek":
            deep_seek = DeepSeek()
            data = deep_seek.invoke(text)

            logging.debug(f"Data received from DeepSeek: {data}")
            return data

    @staticmethod
    def togglePromptService(text):
        settings_path = os.path.join(os.path.dirname(__file__), "settings.json")
        with open(settings_path, "r") as file:
            settings = json.load(file)

        service = settings["configurations"].get("LLM_Model", "chatgpt").lower()

        if service == "chatgpt":
            chatgpt = ChatGpt()
            parse = chatgpt.prompt(text)
            data = json.loads(parse)

            return data
        elif service == "deepseek":
            deep_seek = DeepSeek()
            data = deep_seek.prompt(text)

            return data
