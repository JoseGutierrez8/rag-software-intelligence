import os, re
from typing import List, Optional
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import gc


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
            try: del self.store
            except: pass
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

        # 1. Busqueda semantica
        semantic = self.store.similarity_search(query, k=k)

        # 2. Busqueda por keyword exacto en el texto de los chunks (sin embeddings)
        keyword_docs = []
        keywords = self._extract_keywords(query)
        for kw in keywords[:4]:
            try:
                raw = self.store._collection.get(
                    where_document={"$contains": kw},
                    limit=4,
                    include=["documents", "metadatas"],
                )
                docs_text = raw.get("documents", [])
                docs_meta = raw.get("metadatas", [])
                for text, meta in zip(docs_text, docs_meta):
                    keyword_docs.append(Document(page_content=text, metadata=meta or {}))
            except Exception as ex:
                pass  # Si falla el keyword search, continuar con semantico

        # 3. Combinar priorizando keyword (codigo) sobre semantico
        seen = set()
        combined = []
        for doc in keyword_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                combined.append(doc)
        for doc in semantic:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        return combined[:k + 4]

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        tokens = []
        # Palabras con guion_bajo (nombres de funciones y campos)
        tokens += re.findall(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b', query.lower())
        # Palabras que terminan en .py
        tokens += re.findall(r'\w+\.py\b', query)
        # Palabras largas en CamelCase (nombres de clases)
        tokens += re.findall(r'\b[A-Z][a-z]+[A-Z]\w+\b', query)
        # Palabras clave de inventario
        for w in query.split():
            w = w.strip("?.,")
            if len(w) > 7 and w.isalpha():
                tokens.append(w)
        return list(set(t for t in tokens if len(t) > 3))

    def count(self) -> int:
        return self._count_safe()

    def _count_safe(self) -> int:
        if self.store is None:
            return 0
        try:
            return self.store._collection.count()
        except:
            pass
        try:
            return len(self.store.get().get("ids", []))
        except:
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
                try: os.remove(os.path.join(root, fname))
                except: pass
            for dname in dirs:
                try: os.rmdir(os.path.join(root, dname))
                except: pass
        try: os.rmdir(path)
        except: pass
