from abc import ABC, abstractmethod
from typing import List
from langchain.schema import Document


class BaseLoader(ABC):
    """Interfaz comun para todos los ingestores del sistema RAG."""

    @abstractmethod
    def load(self) -> List[Document]:
        pass

    def _make_doc(self, content: str, **meta) -> Document:
        return Document(page_content=content.strip(), metadata=meta)

    def _safe_read(self, path: str, encoding: str = "utf-8") -> str:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
