from abc import ABC, abstractmethod
from typing import List
from .client import Message, Event

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: List[Message]) -> str:
        pass

    @abstractmethod
    def extract_events(self, text: str) -> List[Event]:
        pass
