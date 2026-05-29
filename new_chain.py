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
            context_parts.append(label + "\n" + chunk.page_content)

        context = "\n\n---\n\n".join(context_parts)
        history = self._format_history()
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
                    "type"   : chunk.metadata.get("file_type", "?"),
                    "loader" : chunk.metadata.get("loader", "?"),
                    "preview": chunk.page_content[:120].replace("\n", " "),
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
        return "\n".join(lines)
