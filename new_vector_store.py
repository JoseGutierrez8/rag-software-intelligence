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

        semantic = self.store.similarity_search(query, k=k)

        keywords = self._extract_code_keywords(query)
        keyword_docs = []
        for kw in keywords[:3]:
            try:
                hits = self.store.similarity_search(
                    kw, k=3,
                    filter={"loader": "GitLoader"},
                )
                keyword_docs.extend(hits)
            except Exception:
                try:
                    hits = self.store.similarity_search(kw, k=2)
                    keyword_docs.extend([h for h in hits
                                         if h.metadata.get("loader") == "GitLoader"])
                except Exception:
                    pass

        seen = set()
        combined = []
        for doc in keyword_docs:
            key = doc.page_content[:80]
            if key not in seen:
                seen.add(key)
                combined.append(doc)
        for doc in semantic:
            key = doc.page_content[:80]
            if key not in seen:
                seen.add(key)
                combined.append(doc)

        return combined[:k + 3]

    @staticmethod
    def _extract_code_keywords(query: str) -> List[str]:
        tokens = re.findall(r'[a-zA-Z][a-z]+_[a-zA-Z_]+|\w+\.py', query)
        for w in query.split():
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
