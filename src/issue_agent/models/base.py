from abc import ABC, abstractmethod
from typing import Any


class Model(ABC):
    @abstractmethod
    def generate(
        self,
        input_items: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ):
        pass