import os
from typing import List
from langchain.schema import Document
from ingestors.base_loader import BaseLoader


class InfraLoader(BaseLoader):
    """Lee archivos de infraestructura: Dockerfile, docker-compose, K8s."""

    def __init__(self, path: str):
        self.path = path

    def load(self) -> List[Document]:
        documents = []
        if os.path.isfile(self.path):
            doc = self._load_file(self.path)
            if doc:
                documents.append(doc)
        elif os.path.isdir(self.path):
            for root, _, files in os.walk(self.path):
                for fname in files:
                    if self._is_infra_file(fname):
                        doc = self._load_file(os.path.join(root, fname))
                        if doc:
                            documents.append(doc)
        print("  [InfraLoader]", len(documents), "archivos de infraestructura")
        return documents

    def _load_file(self, filepath: str):
        filename = os.path.basename(filepath)
        content  = self._safe_read(filepath)
        if not content.strip():
            return None
        infra_type = self._detect_type(filename, content)
        header = "[Infraestructura - " + infra_type + "]\nArchivo: " + filename + "\n\n"
        return self._make_doc(
            content=header + content,
            source=filename,
            file_type=os.path.splitext(filename)[1] or filename,
            infra_type=infra_type, loader="InfraLoader",
        )

    @staticmethod
    def _is_infra_file(filename: str) -> bool:
        name = filename.lower()
        if name in ("dockerfile", ".env.example", "makefile"):
            return True
        ext = os.path.splitext(filename)[1].lower()
        return ext in (".yaml", ".yml", ".toml", ".env")

    @staticmethod
    def _detect_type(filename: str, content: str) -> str:
        name = filename.lower()
        if "dockerfile" in name:
            return "Dockerfile"
        if "docker-compose" in name:
            return "Docker Compose"
        if name.endswith((".yaml", ".yml")):
            return "YAML Config"
        if name.endswith(".toml"):
            return "TOML Config"
        if ".env" in name:
            return "Variables de Entorno"
        return "Archivo de Infraestructura"
