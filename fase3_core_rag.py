"""
FASE 3 - Core RAG: Chunking inteligente + ChromaDB
Mover a rag_software_intelligence y ejecutar:
  python fase3_core_rag.py
Luego probar:
  python tests/test_core_rag.py
"""
import os

FILES = {}

# ══════════════════════════════════════════════════════
FILES["core/chunker.py"] = """\
import re
from typing import List
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


class SmartChunker:
    \"\"\"
    Aplica estrategia de chunking segun el tipo de fuente:
    - Codigo     : por bloques de funcion/clase (preserva contexto semantico)
    - Excel      : tabla completa = un chunk (no dividir registros)
    - Draw.io    : componente completo = un chunk
    - PDF / MD   : parrafos con overlap configurable
    \"\"\"

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap

        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\\n\\n", "\\n", ". ", " ", ""],
        )
        self._code_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=50,
            separators=["\\n\\nclass ", "\\n\\ndef ", "\\n    def ", "\\n\\n", "\\n", ""],
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
"""

# ══════════════════════════════════════════════════════
FILES["core/vector_store.py"] = """\
import os
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


class VectorStoreManager:
    \"\"\"
    Gestiona la base de datos vectorial ChromaDB con embeddings de Ollama.
    - build()        : indexa documentos desde cero
    - load_existing(): carga un indice ya construido
    - search()       : busqueda semantica con metadatos de fuente
    \"\"\"

    COLLECTION = "rag_software_intelligence"

    def __init__(self, persist_dir: str, model: str = "llama3.2"):
        self.persist_dir = persist_dir
        self.embeddings  = OllamaEmbeddings(model=model)
        self.store: Optional[Chroma] = None

    def build(self, documents: List[Document]) -> None:
        \"\"\"Construye el indice vectorial desde cero con los documentos dados.\"\"\"
        if not documents:
            raise ValueError("No hay documentos para indexar.")

        print("  [VectorStore] Construyendo indice con", len(documents), "chunks...")
        print("  [VectorStore] (esto puede tardar varios minutos la primera vez)")

        # Limpiar indice anterior si existe
        if os.path.exists(self.persist_dir):
            import shutil
            shutil.rmtree(self.persist_dir)

        # Indexar en lotes para evitar timeout con Ollama
        batch_size = 50
        all_docs   = []
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            if i == 0:
                self.store = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=self.persist_dir,
                    collection_name=self.COLLECTION,
                )
            else:
                self.store.add_documents(batch)
            pct = min(100, int((i + len(batch)) / len(documents) * 100))
            print("    Progreso: " + str(pct) + "%  (" + str(i + len(batch)) + "/" + str(len(documents)) + " chunks)")

        print("  [VectorStore] Indice construido y guardado en", self.persist_dir)

    def load_existing(self) -> bool:
        \"\"\"Carga un indice existente. Retorna True si lo encontro.\"\"\"
        if not os.path.exists(self.persist_dir):
            return False
        try:
            self.store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
                collection_name=self.COLLECTION,
            )
            count = self.store._collection.count()
            print("  [VectorStore] Indice cargado:", count, "chunks")
            return count > 0
        except Exception as e:
            print("  [VectorStore] Error al cargar indice:", str(e))
            return False

    def search(self, query: str, k: int = 5) -> List[Document]:
        \"\"\"Busqueda semantica. Retorna los k chunks mas relevantes.\"\"\"
        if self.store is None:
            raise RuntimeError("Vector store no inicializado. Llama a build() o load_existing().")
        results = self.store.similarity_search(query, k=k)
        return results

    def count(self) -> int:
        if self.store is None:
            return 0
        return self.store._collection.count()
"""

# ══════════════════════════════════════════════════════
FILES["core/pipeline.py"] = """\
import os
from typing import List
from langchain.schema import Document

from config.settings import (GITHUB_REPO_URL, CLONE_DIR,
                              CHROMA_PERSIST_DIR, OLLAMA_MODEL,
                              CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RESULTS)
from ingestors.git_loader    import GitLoader
from ingestors.drawio_loader import DrawioLoader
from ingestors.excel_loader  import ExcelLoader
from ingestors.doc_loader    import DocLoader
from core.chunker             import SmartChunker
from core.vector_store        import VectorStoreManager


class IngestionPipeline:
    \"\"\"
    Orquesta la ingesta completa:
    1. Ejecuta cada loader registrado
    2. Pasa los docs por SmartChunker
    3. Inserta en VectorStoreManager (ChromaDB)
    \"\"\"

    UPLOADS_DIR = "data/uploads"

    def __init__(self):
        self.chunker      = SmartChunker(CHUNK_SIZE, CHUNK_OVERLAP)
        self.vector_store = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)

    def run(self, force_rebuild: bool = False) -> int:
        \"\"\"
        Ejecuta el pipeline completo.
        Args:
            force_rebuild: si True, reconstruye el indice aunque ya exista.
        Returns:
            Numero total de chunks indexados.
        \"\"\"
        # Si ya existe el indice y no se fuerza rebuild, lo cargamos
        if not force_rebuild and self.vector_store.load_existing():
            print("[Pipeline] Indice existente cargado.")
            return self.vector_store.count()

        print("[Pipeline] Iniciando ingesta de documentos...")
        all_docs: List[Document] = []

        # 1. Git
        if GITHUB_REPO_URL:
            try:
                docs = GitLoader(GITHUB_REPO_URL, CLONE_DIR).load()
                all_docs.extend(docs)
            except Exception as e:
                print("  [Pipeline] Error en GitLoader:", str(e))

        # 2. Draw.io
        for fname in os.listdir(self.UPLOADS_DIR):
            if fname.endswith(".drawio"):
                try:
                    path = os.path.join(self.UPLOADS_DIR, fname)
                    docs = DrawioLoader(path).load()
                    all_docs.extend(docs)
                except Exception as e:
                    print("  [Pipeline] Error en DrawioLoader:", str(e))

        # 3. Excel
        for fname in os.listdir(self.UPLOADS_DIR):
            if fname.endswith(".xlsx"):
                try:
                    path = os.path.join(self.UPLOADS_DIR, fname)
                    docs = ExcelLoader(path).load()
                    all_docs.extend(docs)
                except Exception as e:
                    print("  [Pipeline] Error en ExcelLoader:", str(e))

        # 4. PDF y Markdown
        for fname in os.listdir(self.UPLOADS_DIR):
            ext = os.path.splitext(fname)[1].lower()
            if ext in (".pdf", ".md", ".txt"):
                try:
                    path = os.path.join(self.UPLOADS_DIR, fname)
                    docs = DocLoader(path).load()
                    all_docs.extend(docs)
                except Exception as e:
                    print("  [Pipeline] Error en DocLoader:", str(e))

        if not all_docs:
            print("[Pipeline] No se encontraron documentos para indexar.")
            return 0

        print("[Pipeline] Total documentos cargados:", len(all_docs))

        # 5. Chunking
        chunks = self.chunker.chunk(all_docs)

        # 6. Vectorizacion
        self.vector_store.build(chunks)

        total = self.vector_store.count()
        print("[Pipeline] COMPLETADO:", total, "chunks en ChromaDB")
        return total

    def get_vector_store(self) -> VectorStoreManager:
        return self.vector_store
"""

# ══════════════════════════════════════════════════════
FILES["tests/test_core_rag.py"] = """\
\"\"\"
Prueba del Core RAG: pipeline completo de ingesta.
Ejecutar desde rag_software_intelligence:
  python tests/test_core_rag.py

ADVERTENCIA: La primera ejecucion puede tardar 5-15 minutos
porque Ollama genera embeddings para todos los chunks.
\"\"\"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.pipeline import IngestionPipeline

SEP = "=" * 55

print("\\n" + SEP)
print("  TEST CORE RAG - Pipeline de Ingesta")
print(SEP)
print("  AVISO: La primera vez tarda varios minutos.")
print("         Ollama generara embeddings localmente.")
print(SEP)

pipeline = IngestionPipeline()
total    = pipeline.run(force_rebuild=False)

print("\\n" + SEP)
print("  Chunks indexados en ChromaDB:", total)
print(SEP)

if total > 0:
    print("\\n  Probando busqueda semantica...")
    vs = pipeline.get_vector_store()

    consultas = [
        "id_cliente campo en tabla clientes",
        "Capa de Presentacion arquitectura",
        "precio stock producto",
    ]
    for q in consultas:
        print("\\n  Consulta: " + q)
        results = vs.search(q, k=2)
        for r in results:
            src = r.metadata.get("source", "?")
            print("    [" + src + "] " + r.page_content[:100].replace("\\n", " "))

print("\\n" + SEP)
print("  Test Core RAG completado")
print(SEP)
"""

# ══════════════════════════════════════════════════════
for ruta, contenido in FILES.items():
    os.makedirs(os.path.dirname(ruta) if os.path.dirname(ruta) else ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print("  Escrito:", ruta)

print("\nFase 3 lista.")
print("Ejecuta: python tests/test_core_rag.py")
print("(La primera vez tarda varios minutos - Ollama genera embeddings)")
