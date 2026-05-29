"""
Ejecutar desde rag_software_intelligence con:
  python fix_git_loader.py
"""
import os

GIT_LOADER = "ingestors/git_loader.py"

CONTENT = r'''
import os
from typing import List

import git
from langchain.schema import Document

from ingestors.base_loader import BaseLoader

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rb",
    ".php", ".cpp", ".c", ".h", ".rs", ".kt", ".scala",
    ".sql", ".sh", ".yaml", ".yml", ".json", ".toml",
    ".md", ".txt", ".cfg", ".ini",
}

IGNORE_DIRS  = {".git", "__pycache__", "node_modules", ".venv",
                "venv", "dist", "build", ".mypy_cache"}


class GitLoader(BaseLoader):
    """
    Clona un repositorio Git (local o remoto) e indexa su codigo fuente.
    Cada archivo se convierte en un Document con metadata:
      source      : ruta relativa dentro del repo
      file_type   : extension del archivo (.py, .js, etc.)
      repo_url    : URL del repositorio
      lines_total : total de lineas del archivo
    """

    def __init__(self, repo_url: str, clone_dir: str):
        self.repo_url  = repo_url
        self.clone_dir = clone_dir

    def load(self) -> List[Document]:
        repo_path = self._get_repo()
        documents = []

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in CODE_EXTENSIONS:
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, repo_path)

                content = self._safe_read(filepath)
                if not content.strip():
                    continue

                lines = content.splitlines()
                numbered_lines = []
                for i, line in enumerate(lines):
                    numbered_lines.append(str(i + 1).rjust(4) + ": " + line)
                numbered = "\n".join(numbered_lines)

                header  = "# Archivo: " + rel_path + "\n\n"
                doc = self._make_doc(
                    content=header + numbered,
                    source=rel_path,
                    file_type=ext,
                    repo_url=self.repo_url,
                    lines_total=len(lines),
                    loader="GitLoader",
                )
                documents.append(doc)

        print("  [GitLoader]", len(documents), "archivos indexados desde", self.repo_url)
        return documents

    def _get_repo(self) -> str:
        repo_name  = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        local_path = os.path.join(self.clone_dir, repo_name)

        if os.path.exists(local_path):
            print("  [GitLoader] Repo ya existe en", local_path, ", actualizando...")
            try:
                repo = git.Repo(local_path)
                repo.remotes.origin.pull()
            except Exception:
                pass
        else:
            print("  [GitLoader] Clonando", self.repo_url, "en", local_path, "...")
            os.makedirs(self.clone_dir, exist_ok=True)
            git.Repo.clone_from(self.repo_url, local_path)

        return local_path
'''

with open(GIT_LOADER, "w", encoding="utf-8") as f:
    f.write(CONTENT.lstrip("\n"))

print("Archivo corregido:", GIT_LOADER)
print("Ahora ejecuta: python tests/test_ingestores_manual.py")
