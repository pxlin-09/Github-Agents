from openai import OpenAI

from .base import Model


class OpenAIModel(Model):
    def __init__(self, model: str):
        self.client = OpenAI()
        self.model = model

    def generate(self, input_items, tools):
        return self.client.responses.create(
            model=self.model,
            input=input_items,
            tools=tools,
        )
