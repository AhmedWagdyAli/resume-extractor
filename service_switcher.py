import requests
from chatgpt_service import ChatGPTInputData as ChatGpt
from deepseek_service import DeepSeekInputData as DeepSeek


class ServiceSwitcher:
    def toggleService(service, text):
        if service == "chatgpt":
            chatgpt = ChatGpt()
            parsed_text = chatgpt.invoke(input.input_data(text))
            return parsed_text
        elif service == "deepseek":
            deep_seek = DeepSeek()
            parsed_text = deep_seek.invoke(input.input_data(text))
            return parsed_text
