"""
FASE 4 - Capa LLM: prompts + cadena RAG con memoria de conversacion.
Mover a rag_software_intelligence y ejecutar:
  python fase4_llm.py
Luego probar:
  python tests/test_llm_chain.py
"""
import os

FILES = {}

# ══════════════════════════════════════════════════════
FILES["llm/prompts.py"] = """\
\"\"\"
Prompts del Arquitecto de Software Senior.
Diseñados para forzar citacion de fuentes y evitar alucinaciones.
\"\"\"

SYSTEM_PROMPT = \"\"\"Eres un Arquitecto de Software Senior especializado en trazabilidad
de sistemas. Tienes acceso a una base de conocimiento tecnica que incluye:
- Codigo fuente de repositorios Git (con numeros de linea)
- Diagramas de arquitectura Draw.io
- Diccionarios de datos en Excel
- Documentacion tecnica

REGLAS ESTRICTAS QUE DEBES SEGUIR SIEMPRE:
1. Responde UNICAMENTE con la informacion de los documentos del contexto.
2. Cita SIEMPRE la fuente de cada afirmacion con este formato:
   [archivo.py, linea X] o [Excel: tabla.campo] o [Draw.io: Componente]
3. Si la informacion NO esta en el contexto, responde exactamente:
   "No encontre esa informacion en los documentos indexados."
4. NUNCA inventes nombres de archivos, campos, funciones o clases.
5. Para trazabilidad, muestra la cadena completa:
   campo Excel -> modelo Python -> service -> ruta API
6. Sé conciso y preciso. Prioriza la exactitud sobre la completitud.

Contexto de documentos recuperados:
{context}

Historial de conversacion:
{history}
\"\"\"

QUERY_TEMPLATE = \"\"\"Pregunta del usuario: {question}

Responde basandote exclusivamente en el contexto proporcionado arriba.
Incluye las fuentes exactas de cada dato que menciones.\"\"\"
"""

# ══════════════════════════════════════════════════════
FILES["llm/chain.py"] = """\
from typing import List, Dict, Any
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

from llm.prompts import SYSTEM_PROMPT, QUERY_TEMPLATE
from core.vector_store import VectorStoreManager


class RAGChain:
    \"\"\"
    Cadena RAG completa con memoria de conversacion.
    Combina:
    - VectorStoreManager (ChromaDB) para recuperacion semantica
    - Ollama/llama3.2 como LLM local
    - Memoria de los ultimos N turnos de conversacion
    - Prompt del Arquitecto Senior con citacion forzada
    \"\"\"

    def __init__(self, vector_store: VectorStoreManager,
                 model: str = "llama3.2",
                 top_k: int = 5,
                 memory_turns: int = 6):
        self.vector_store  = vector_store
        self.top_k         = top_k
        self.memory_turns  = memory_turns
        self.history: List[Dict[str, str]] = []

        self.llm = ChatOllama(
            model=model,
            temperature=0.1,
        )

    def ask(self, question: str) -> Dict[str, Any]:
        \"\"\"
        Procesa una pregunta y retorna la respuesta con fuentes.

        Args:
            question: Pregunta del usuario.

        Returns:
            {
              'answer'  : str,
              'sources' : List[dict],
              'chunks'  : List[Document]
            }
        \"\"\"
        # 1. Recuperar chunks relevantes
        chunks = self.vector_store.search(question, k=self.top_k)

        # 2. Construir contexto con fuentes etiquetadas
        context_parts = []
        for i, chunk in enumerate(chunks):
            src   = chunk.metadata.get("source", "desconocido")
            etype = chunk.metadata.get("element_type", "")
            sheet = chunk.metadata.get("sheet", "")
            line  = chunk.metadata.get("lines_total", "")

            if sheet:
                label = "[Excel:" + src + " hoja=" + sheet + "]"
            elif etype in ("node", "edge", "layer"):
                label = "[Draw.io:" + src + " tipo=" + etype + "]"
            else:
                label = "[" + src + "]"

            context_parts.append(label + "\\n" + chunk.page_content)

        context  = "\\n\\n---\\n\\n".join(context_parts)
        history  = self._format_history()

        # 3. Construir mensajes
        system_content = SYSTEM_PROMPT.format(context=context, history=history)
        user_content   = QUERY_TEMPLATE.format(question=question)

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_content),
        ]

        # 4. Llamar al LLM
        response = self.llm.invoke(messages)
        answer   = response.content

        # 5. Actualizar historial
        self.history.append({"role": "user",      "content": question})
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > self.memory_turns * 2:
            self.history = self.history[-(self.memory_turns * 2):]

        # 6. Extraer fuentes unicas
        sources = []
        seen    = set()
        for chunk in chunks:
            src = chunk.metadata.get("source", "?")
            if src not in seen:
                seen.add(src)
                sources.append({
                    "file"    : src,
                    "type"    : chunk.metadata.get("file_type", "?"),
                    "loader"  : chunk.metadata.get("loader", "?"),
                    "preview" : chunk.page_content[:120].replace("\\n", " "),
                })

        return {
            "answer"  : answer,
            "sources" : sources,
            "chunks"  : chunks,
        }

    def clear_history(self) -> None:
        self.history = []

    def _format_history(self) -> str:
        if not self.history:
            return "(Sin historial previo)"
        lines = []
        for msg in self.history[-self.memory_turns * 2:]:
            prefix = "Usuario" if msg["role"] == "user" else "Asistente"
            lines.append(prefix + ": " + msg["content"][:300])
        return "\\n".join(lines)
"""

# ══════════════════════════════════════════════════════
FILES["llm/__init__.py"] = ""

# ══════════════════════════════════════════════════════
FILES["tests/test_llm_chain.py"] = """\
\"\"\"
Prueba de la cadena RAG completa con los 3 casos de uso de la rubrica.
Ejecutar desde rag_software_intelligence:
  python tests/test_llm_chain.py

Requiere que el indice ChromaDB ya este construido (test_core_rag.py).
Cada pregunta puede tardar 30-90 segundos.
\"\"\"
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import OLLAMA_MODEL, CHROMA_PERSIST_DIR, TOP_K_RESULTS
from core.vector_store import VectorStoreManager
from llm.chain import RAGChain

SEP = "=" * 60

def imprimir_resultado(caso, pregunta, resultado):
    print("\\n" + SEP)
    print("  " + caso)
    print("  Pregunta: " + pregunta)
    print(SEP)
    print("  RESPUESTA:")
    print(resultado["answer"])
    print("\\n  FUENTES CITADAS:")
    for s in resultado["sources"]:
        print("    [" + s["file"] + "] " + s["preview"][:80])

# Cargar indice existente
print("\\n" + SEP)
print("  TEST LLM CHAIN - Casos de Uso de la Rubrica")
print(SEP)

vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
if not vs.load_existing():
    print("ERROR: No se encontro el indice ChromaDB.")
    print("Ejecuta primero: python tests/test_core_rag.py")
    sys.exit(1)

chain = RAGChain(vs, model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)

# CASO DE USO 1 — Trazabilidad de campo en codigo fuente
print("\\nEjecutando Caso de Uso 1 (puede tardar ~60 seg)...")
r1 = chain.ask(
    "En que archivos de codigo fuente se usa el campo id_cliente "
    "definido en el Diccionario de Datos?"
)
imprimir_resultado("CASO USO 1: Trazabilidad de campo en codigo",
                   "id_cliente en codigo fuente", r1)

# CASO DE USO 2 — Arquitectura Draw.io vs Codigo
print("\\nEjecutando Caso de Uso 2 (puede tardar ~60 seg)...")
r2 = chain.ask(
    "Como se relaciona la arquitectura del diagrama con el codigo fuente? "
    "Explica que hace cada capa segun los archivos del repositorio."
)
imprimir_resultado("CASO USO 2: Arquitectura Draw.io vs Codigo",
                   "Relacion arquitectura y codigo", r2)

# CASO DE USO 3 — Impacto de cambios en logica de negocio
print("\\nEjecutando Caso de Uso 3 (puede tardar ~60 seg)...")
r3 = chain.ask(
    "Si se cambia el campo estado en la tabla pedidos, "
    "que archivos del codigo fuente se veerian afectados y por que?"
)
imprimir_resultado("CASO USO 3: Impacto de cambios en logica de negocio",
                   "Cambio en campo estado de pedidos", r3)

print("\\n" + SEP)
print("  Tests LLM Chain completados")
print("  3 casos de uso de la rubrica ejecutados")
print(SEP)
"""

# ══════════════════════════════════════════════════════
for ruta, contenido in FILES.items():
    os.makedirs(os.path.dirname(ruta) if os.path.dirname(ruta) else ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    print("  Escrito:", ruta)

print("\nFase 4 lista.")
print("Ejecuta: python tests/test_llm_chain.py")
print("(Cada pregunta tarda ~60 segundos - Ollama procesa localmente)")
