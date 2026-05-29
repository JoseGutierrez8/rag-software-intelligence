import os
import re
from typing import List
from langchain.schema import Document
from ingestors.base_loader import BaseLoader


class DocLoader(BaseLoader):
    """Carga documentacion tecnica en PDF o Markdown."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError("Documento no encontrado: " + self.file_path)
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".pdf":
            return self._load_pdf()
        elif ext in (".md", ".markdown", ".txt"):
            return self._load_markdown()
        else:
            raise ValueError("Extension no soportada: " + ext)

    def _load_pdf(self) -> List[Document]:
        from pypdf import PdfReader
        reader   = PdfReader(self.file_path)
        filename = os.path.basename(self.file_path)
        documents = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if not text:
                continue
            header = "[PDF: " + filename + " - Pagina " + str(page_num) + "]\n\n"
            documents.append(self._make_doc(
                content=header + text,
                source=filename, file_type=".pdf",
                page=page_num, loader="DocLoader",
            ))
        print("  [DocLoader/PDF]", len(documents), "paginas desde", filename)
        return documents

    def _load_markdown(self) -> List[Document]:
        filename  = os.path.basename(self.file_path)
        content   = self._safe_read(self.file_path)
        documents = []
        sections  = re.split(r"(?m)^(#{1,2}\s+.+)$", content)
        current_title = filename
        buffer = []
        for part in sections:
            if re.match(r"^#{1,2}\s+", part):
                if buffer:
                    text = "\n".join(buffer).strip()
                    if text:
                        header = "[MD: " + filename + " - " + current_title + "]\n\n"
                        documents.append(self._make_doc(
                            content=header + text,
                            source=filename, file_type=".md",
                            section=current_title, loader="DocLoader",
                        ))
                current_title = part.strip("# ").strip()
                buffer = []
            else:
                buffer.append(part)
        if buffer:
            text = "\n".join(buffer).strip()
            if text:
                header = "[MD: " + filename + " - " + current_title + "]\n\n"
                documents.append(self._make_doc(
                    content=header + text,
                    source=filename, file_type=".md",
                    section=current_title, loader="DocLoader",
                ))
        print("  [DocLoader/MD]", len(documents), "secciones desde", filename)
        return documents
