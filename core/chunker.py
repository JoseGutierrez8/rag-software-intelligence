import re
from typing import List
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


class SmartChunker:
    """
    Aplica estrategia de chunking segun el tipo de fuente:
    - Codigo     : por bloques de funcion/clase (preserva contexto semantico)
    - Excel      : tabla completa = un chunk (no dividir registros)
    - Draw.io    : componente completo = un chunk
    - PDF / MD   : parrafos con overlap configurable
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=50,
            separators=["\n\nclass ", "\n\ndef ", "\n    def ", "\n\n", "\n", ""],
        )

    def chunk(self, documents: List[Document]) -> List[Document]:
        result = []
        for doc in documents:
            loader    = doc.metadata.get("loader", "")
            file_type = doc.metadata.get("file_type", "")
            chunks    = self._chunk_document(doc, loader, file_type)
            result.extend(chunks)
        print("  [SmartChunker]", len(documents), "docs ->", len(result), "chunks")
        return result

    def _chunk_document(self, doc: Document, loader: str, file_type: str) -> List[Document]:
        # Excel y Draw.io: no dividir, cada documento ya es atomico
        if loader in ("ExcelLoader", "DrawioLoader"):
            return [doc]

        # Codigo fuente: splitter orientado a funciones
        if file_type in (".py", ".js", ".ts", ".java", ".cs", ".go",
                         ".rb", ".php", ".cpp", ".c", ".rs"):
            return self._split_with(doc, self._code_splitter)

        # PDF, MD, texto general: splitter de parrafos
        return self._split_with(doc, self._text_splitter)

    @staticmethod
    def _split_with(doc: Document, splitter) -> List[Document]:
        texts = splitter.split_text(doc.page_content)
        chunks = []
        for i, text in enumerate(texts):
            meta = dict(doc.metadata)
            meta["chunk_index"] = i
            meta["chunk_total"] = len(texts)
            chunks.append(Document(page_content=text, metadata=meta))
        return chunks if chunks else [doc]
