"""
Fix completo: busqueda hibrida semantica + keyword para encontrar codigo.
Ejecutar desde rag_software_intelligence:
  python fix_completo_v3.py
"""
import os

# ══════════════════════════════════════════════════════
# 1. VECTOR STORE con busqueda hibrida
# ══════════════════════════════════════════════════════
VECTOR_STORE = """\
import os, gc, re
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings


class VectorStoreManager:
    COLLECTION = "rag_software_intelligence"

    def __init__(self, persist_dir: str, model: str = "llama3.2"):
        self.persist_dir = persist_dir
        self.embeddings  = OllamaEmbeddings(model=model)
        self.store: Optional[Chroma] = None

    def build(self, documents: List[Document]) -> None:
        if not documents:
            raise ValueError("No hay documentos para indexar.")
        print("  [VectorStore] Indexando", len(documents), "chunks...")

        if self.store is not None:
            try:
                del self.store
            except Exception:
                pass
            self.store = None
            gc.collect()

        if os.path.exists(self.persist_dir):
            self._safe_rmtree(self.persist_dir)
        os.makedirs(self.persist_dir, exist_ok=True)

        batch_size = 40
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            if self.store is None:
                self.store = Chroma.from_documents(
                    documents=batch,
                    embedding=self.embeddings,
                    persist_directory=self.persist_dir,
                    collection_name=self.COLLECTION,
                )
            else:
                self.store.add_documents(batch)
            done = min(i + batch_size, len(documents))
            print("    " + str(int(done/len(documents)*100)) + "% (" + str(done) + "/" + str(len(documents)) + ")")

        total = self._count_safe()
        print("  [VectorStore] Listo:", total, "vectores en", self.persist_dir)

    def load_existing(self) -> bool:
        if not os.path.exists(self.persist_dir):
            return False
        try:
            self.store = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings,
                collection_name=self.COLLECTION,
            )
            total = self._count_safe()
            print("  [VectorStore] Indice cargado:", total, "vectores")
            return total > 0
        except Exception as e:
            print("  [VectorStore] Error:", str(e))
            return False

    def search(self, query: str, k: int = 5) -> List[Document]:
        if self.store is None:
            raise RuntimeError("VectorStore no inicializado.")

        # Busqueda semantica normal
        semantic = self.store.similarity_search(query, k=k)

        # Busqueda por keyword si la query contiene terminos de codigo
        keywords = self._extract_code_keywords(query)
        keyword_docs = []
        if keywords:
            for kw in keywords[:3]:
                try:
                    hits = self.store.similarity_search(
                        kw,
                        k=3,
                        filter={"loader": "GitLoader"},
                    )
                    keyword_docs.extend(hits)
                except Exception:
                    try:
                        # Sin filtro si falla
                        hits = self.store.similarity_search(kw, k=2)
                        keyword_docs.extend([h for h in hits
                                             if h.metadata.get("loader") == "GitLoader"])
                    except Exception:
                        pass

        # Combinar y deduplicar priorizando codigo
        seen = set()
        combined = []
        # Primero los de codigo keyword
        for doc in keyword_docs:
            key = doc.page_content[:80]
            if key not in seen:
                seen.add(key)
                combined.append(doc)
        # Luego los semanticos
        for doc in semantic:
            key = doc.page_content[:80]
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        return combined[:k + 3]  # Un poco mas para que el LLM tenga contexto

    @staticmethod
    def _extract_code_keywords(query: str) -> List[str]:
        """Extrae terminos que parecen ser nombres de codigo (snake_case, .py, def)."""
        tokens = re.findall(r'[a-zA-Z][a-z]+_[a-zA-Z_]+|\\w+\\.py|def\\s+\\w+|class\\s+\\w+', query)
        # Tambien palabras largas que parecen nombres de funcion
        words = query.split()
        for w in words:
            if '_' in w and len(w) > 5:
                tokens.append(w)
        return list(set(tokens))

    def count(self) -> int:
        return self._count_safe()

    def _count_safe(self) -> int:
        if self.store is None:
            return 0
        try:
            return self.store._collection.count()
        except Exception:
            pass
        try:
            return len(self.store.get().get("ids", []))
        except Exception:
            return 0

    @staticmethod
    def _safe_rmtree(path: str) -> None:
        import shutil, time
        for _ in range(3):
            try:
                shutil.rmtree(path)
                return
            except PermissionError:
                time.sleep(1)
        for root, dirs, files in os.walk(path, topdown=False):
            for fname in files:
                try:
                    os.remove(os.path.join(root, fname))
                except Exception:
                    pass
            for dname in dirs:
                try:
                    os.rmdir(os.path.join(root, dname))
                except Exception:
                    pass
        try:
            os.rmdir(path)
        except Exception:
            pass
"""

# ══════════════════════════════════════════════════════
# 2. GIT LOADER mejorado: headers ricos con nombres de funciones
# ══════════════════════════════════════════════════════
GIT_LOADER = """\
import os, re
from typing import List
import git
from langchain.schema import Document
from ingestors.base_loader import BaseLoader

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rb",
    ".php", ".cpp", ".c", ".h", ".rs", ".kt",
    ".sql", ".sh", ".yaml", ".yml", ".json", ".toml",
    ".md", ".txt", ".cfg", ".ini",
}
IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}


class GitLoader(BaseLoader):
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
                rel_path = os.path.relpath(filepath, repo_path).replace("\\\\", "/")
                content  = self._safe_read(filepath)
                if not content.strip():
                    continue
                lines = content.splitlines()

                # Extraer nombres de funciones y clases para el header
                funciones = re.findall(r'^(?:def|class)\\s+(\\w+)', content, re.MULTILINE)
                func_header = ""
                if funciones:
                    func_header = "\\nFunciones/Clases definidas: " + ", ".join(funciones)

                # Numerar lineas
                numbered_lines = []
                for i, line in enumerate(lines):
                    numbered_lines.append(str(i + 1).rjust(4) + ": " + line)
                numbered = "\\n".join(numbered_lines)

                # Header enriquecido con nombre de archivo Y funciones
                header = ("# Archivo: " + rel_path + func_header + "\\n\\n")

                doc = self._make_doc(
                    content=header + numbered,
                    source=rel_path,
                    file_type=ext,
                    repo_url=self.repo_url,
                    lines_total=len(lines),
                    functions=", ".join(funciones[:10]),
                    loader="GitLoader",
                )
                documents.append(doc)

        print("  [GitLoader]", len(documents), "archivos indexados")
        return documents

    def _get_repo(self) -> str:
        repo_name  = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        local_path = os.path.join(self.clone_dir, repo_name)
        if os.path.exists(local_path):
            print("  [GitLoader] Repo en", local_path)
            try:
                repo = git.Repo(local_path)
                repo.remotes.origin.pull()
            except Exception:
                pass
        else:
            print("  [GitLoader] Clonando", self.repo_url)
            os.makedirs(self.clone_dir, exist_ok=True)
            git.Repo.clone_from(self.repo_url, local_path)
        return local_path
"""

# ══════════════════════════════════════════════════════
# 3. PROMPTS mejorado: instruye al LLM a buscar en codigo
# ══════════════════════════════════════════════════════
PROMPTS = """\
SYSTEM_PROMPT = '''Eres un Arquitecto de Software Senior con acceso a:
- Codigo fuente Python del sistema (archivos .py con numeros de linea)
- Diagrama de arquitectura Draw.io (capas, componentes, conexiones)
- Diccionario de datos Excel (tablas, campos, tipos, relaciones)

REGLAS:
1. Usa SOLO la informacion de los documentos del contexto.
2. Para CADA dato que menciones, cita la fuente:
   [services/inventario_service.py, linea X] o [Excel: tabla.campo] o [Draw.io: componente]
3. Si no encuentras la informacion: "No encontre esa informacion en los documentos indexados."
4. NUNCA inventes archivos, funciones o campos.
5. Para trazabilidad muestra: campo Excel -> modelo Python -> servicio -> ruta API.
6. Cuando el contexto incluya codigo Python, analiza y explica el codigo directamente.

Contexto de documentos:
{context}

Historial:
{history}
'''

QUERY_TEMPLATE = '''Pregunta: {question}

Analiza el contexto proporcionado arriba y responde con detalle.
Si el contexto incluye codigo Python, cita el archivo y linea exacta.
Si el contexto incluye el Excel, cita la tabla y campo.
Si el contexto incluye Draw.io, cita el componente.'''
"""

# ══════════════════════════════════════════════════════
# 4. CHAIN mejorado: mas contexto, temperatura mas alta para codigo
# ══════════════════════════════════════════════════════
CHAIN = """\
from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage
from llm.prompts import SYSTEM_PROMPT, QUERY_TEMPLATE
from core.vector_store import VectorStoreManager


class RAGChain:
    def __init__(self, vector_store: VectorStoreManager,
                 model: str = "llama3.2",
                 top_k: int = 8,
                 memory_turns: int = 6):
        self.vector_store  = vector_store
        self.top_k         = top_k
        self.memory_turns  = memory_turns
        self.history: List[Dict[str, str]] = []
        self.llm = ChatOllama(model=model, temperature=0.15)

    def ask(self, question: str) -> Dict[str, Any]:
        chunks = self.vector_store.search(question, k=self.top_k)

        # Construir contexto etiquetado
        context_parts = []
        for chunk in chunks:
            src    = chunk.metadata.get("source", "?")
            loader = chunk.metadata.get("loader", "?")
            sheet  = chunk.metadata.get("sheet", "")
            etype  = chunk.metadata.get("element_type", "")
            funcs  = chunk.metadata.get("functions", "")

            if loader == "GitLoader":
                label = "[Codigo: " + src + "]"
                if funcs:
                    label += " (funciones: " + funcs + ")"
            elif loader == "ExcelLoader" and sheet:
                label = "[Excel:" + src + " hoja=" + sheet + "]"
            elif loader == "DrawioLoader":
                label = "[Draw.io:" + src + " tipo=" + etype + "]"
            else:
                label = "[" + src + "]"

            context_parts.append(label + "\\n" + chunk.page_content)

        context  = "\\n\\n---\\n\\n".join(context_parts)
        history  = self._format_history()

        messages = [
            SystemMessage(content=SYSTEM_PROMPT.format(context=context, history=history)),
            HumanMessage(content=QUERY_TEMPLATE.format(question=question)),
        ]

        response = self.llm.invoke(messages)
        answer   = response.content

        self.history.append({"role": "user",      "content": question})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > self.memory_turns * 2:
            self.history = self.history[-(self.memory_turns * 2):]

        sources = []
        seen    = set()
        for chunk in chunks:
            src = chunk.metadata.get("source", "?")
            if src not in seen:
                seen.add(src)
                sources.append({
                    "file"   : src,
                    "type"   : chunk.metadata.get("file_type", chunk.metadata.get("loader", "?")),
                    "loader" : chunk.metadata.get("loader", "?"),
                    "preview": chunk.page_content[:120].replace("\\n", " "),
                })

        return {"answer": answer, "sources": sources, "chunks": chunks}

    def clear_history(self) -> None:
        self.history = []

    def _format_history(self) -> str:
        if not self.history:
            return "(Sin historial previo)"
        lines = []
        for msg in self.history[-(self.memory_turns * 2):]:
            prefix = "Usuario" if msg["role"] == "user" else "Asistente"
            lines.append(prefix + ": " + msg["content"][:300])
        return "\\n".join(lines)
"""

# ══════════════════════════════════════════════════════
# Escribir todos los archivos
# ══════════════════════════════════════════════════════
FILES = {
    "core/vector_store.py":     VECTOR_STORE,
    "ingestors/git_loader.py":  GIT_LOADER,
    "llm/prompts.py":           PROMPTS,
    "llm/chain.py":             CHAIN,
}

for path, content in FILES.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.lstrip("\n"))
    print("Actualizado:", path)

print("""
Fix completo aplicado.

Ahora:
1. Ctrl+C en el PowerShell de Streamlit
2. Stop-Process -Name python -Force -ErrorAction SilentlyContinue
3. Remove-Item -Recurse -Force data\\chroma_db
4. Remove-Item -Recurse -Force data\\repos
5. streamlit run ui/app.py
6. Clic en Indexar / Actualizar
""")
