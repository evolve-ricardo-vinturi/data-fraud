
from abc import ABC, abstractmethod
from typing import Dict

class NotaFiscalTemplateBase(ABC):
    @abstractmethod
    def parse(self, text: str) -> Dict:
        pass
