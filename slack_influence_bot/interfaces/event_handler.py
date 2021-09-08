from typing import Dict, Any
from abc import ABC, abstractmethod


class EventHandler(ABC):
    @abstractmethod
    def handle_event(self, event: Dict[str, Any]) -> None:
        pass
