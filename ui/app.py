import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import (OLLAMA_MODEL, CHROMA_PERSIST_DIR,
                              TOP_K_RESULTS, APP_TITLE)
from core.pipeline    import IngestionPipeline
from llm.chain        import RAGChain

# ── Configuracion de pagina ────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="SoftwareArchitect",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS personalizado ──────────────────────────────────────────
st.markdown("""
<style>
  .main-title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #1F3864;
    margin-bottom: 0.2rem;
  }
  .subtitle {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 1.5rem;
  }
  .source-card {
    background: #f0f4ff;
    border-left: 4px solid #2E75B6;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    border-radius: 0 6px 6px 0;
    font-size: 0.8rem;
    font-family: monospace;
    color: #1a1a2e !important;
  }
  .source-card small {
    color: #444444 !important;
  }
  .metric-box {
    background: #1F3864;
    color: white;
    padding: 0.8rem;
    border-radius: 8px;
    text-align: center;
  }
  .stChatMessage { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

# ── Estado de sesion ───────────────────────────────────────────
if "pipeline" not in st.session_state:
    st.session_state.pipeline  = None
if "chain"    not in st.session_state:
    st.session_state.chain     = None
if "messages" not in st.session_state:
    st.session_state.messages  = []
if "indexed"  not in st.session_state:
    st.session_state.indexed   = False
if "n_chunks" not in st.session_state:
    st.session_state.n_chunks  = 0

# ── Sidebar ────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Arquitecto de Software Senior")
    st.caption("Sistema RAG de Trazabilidad | IA 2026 - UMG")
    st.divider()

    st.markdown("**Modelo LLM**")
    st.code(OLLAMA_MODEL, language=None)
    st.markdown("**Vector DB**")
    st.code("ChromaDB (local)", language=None)

    st.divider()
    st.markdown("**Base de Conocimiento**")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Chunks", st.session_state.n_chunks)
    with col2:
        status = "Listo" if st.session_state.indexed else "Pendiente"
        st.metric("Estado", status)

    st.divider()

    if st.button("Indexar / Actualizar base de conocimiento",
                 use_container_width=True, type="primary"):
        with st.spinner("Cargando documentos e indexando..."):
            try:
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=True)
                st.session_state.pipeline = pipeline
                st.session_state.chain    = RAGChain(
                    pipeline.get_vector_store(),
                    model=OLLAMA_MODEL,
                    top_k=TOP_K_RESULTS,
                )
                st.session_state.indexed  = True
                st.session_state.n_chunks = n
                st.session_state.messages = []
                st.success("Base de conocimiento lista: " + str(n) + " chunks")
                st.rerun()
            except Exception as e:
                st.error("Error al indexar: " + str(e))

    if st.session_state.indexed:
        if st.button("Cargar indice existente",
                     use_container_width=True):
            with st.spinner("Cargando indice..."):
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=False)
                st.session_state.pipeline = pipeline
                st.session_state.chain    = RAGChain(
                    pipeline.get_vector_store(),
                    model=OLLAMA_MODEL,
                    top_k=TOP_K_RESULTS,
                )
                st.session_state.indexed  = True
                st.session_state.n_chunks = n
                st.rerun()

    if st.session_state.chain and st.button("Limpiar historial",
                                             use_container_width=True):
        st.session_state.messages = []
        st.session_state.chain.clear_history()
        st.rerun()

    st.divider()
    st.markdown("**Ejemplos de consulta:**")
    ejemplos = [
        "Que tablas tiene el sistema y cuales son sus relaciones?",
        "En que archivos se usa el campo id_producto?",
        "Explica las capas de la arquitectura del sistema de inventario",
        "Que hace la funcion registrar_entrada y que archivos involucra?",
        "Si cambio el campo stock_minimo, que archivos se veerian afectados?",
        "Que roles de usuario existen y que permisos tiene cada uno?",
        "Como funciona el ciclo de vida de un pedido de compra?",
        "Que tipos de movimiento de inventario existen?",
        "Que campos tiene la tabla movimientos y para que sirve cada uno?",
        "Como se generan las alertas de stock minimo en el codigo?",
    ]
    for ej in ejemplos:
        if st.button(ej, use_container_width=True, key="ej_" + ej[:20]):
            st.session_state["pregunta_rapida"] = ej

# ── Area principal ─────────────────────────────────────────────
st.markdown('<div class="main-title">Arquitecto de Software Senior</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sistema RAG de Inteligencia y Trazabilidad '
            '| IA 2026 — UMG</div>', unsafe_allow_html=True)

# Inicializacion automatica si hay indice existente
if not st.session_state.indexed:
    from core.vector_store import VectorStoreManager
    vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
    if vs.load_existing():
        st.session_state.pipeline = None
        st.session_state.chain    = RAGChain(vs, model=OLLAMA_MODEL,
                                              top_k=TOP_K_RESULTS)
        st.session_state.indexed  = True
        st.session_state.n_chunks = vs.count()

if not st.session_state.indexed:
    st.info("Para comenzar, haz clic en **Indexar / Actualizar** "
            "en el panel izquierdo.")
    st.markdown("Este sistema analiza:")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Codigo fuente Git**\nNavega el repositorio "
                    "con trazabilidad por linea")
    with col2:
        st.markdown("**Diagramas Draw.io**\nExplica arquitectura "
                    "y relaciones entre componentes")
    with col3:
        st.markdown("**Diccionario Excel**\nRastrear campos desde "
                    "la BD hasta el codigo")
else:
    # Mostrar historial de mensajes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "sources" in msg:
                with st.expander("Fuentes citadas (" + str(len(msg["sources"])) + ")"):
                    for src in msg["sources"]:
                        st.markdown(
                            '<div class="source-card">'
                            + src["file"] + " [" + src["type"] + "]<br>"
                            + "<small>" + src["preview"][:100] + "...</small>"
                            + "</div>",
                            unsafe_allow_html=True,
                        )

    # Capturar pregunta rapida del sidebar
    pregunta_rapida = st.session_state.pop("pregunta_rapida", None)

    # Input de chat
    prompt = st.chat_input("Escribe tu consulta tecnica aqui...")
    if pregunta_rapida:
        prompt = pregunta_rapida

    if prompt and st.session_state.chain:
        # Mostrar pregunta
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Obtener respuesta
        with st.chat_message("assistant"):
            with st.spinner("Consultando la base de conocimiento..."):
                try:
                    result  = st.session_state.chain.ask(prompt)
                    answer  = result["answer"]
                    sources = result["sources"]

                    st.markdown(answer)
                    with st.expander("Fuentes citadas (" + str(len(sources)) + ")"):
                        for src in sources:
                            st.markdown(
                                '<div class="source-card">'
                                + src["file"] + " [" + src["type"] + "]<br>"
                                + "<small>" + src["preview"][:100] + "...</small>"
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                    st.session_state.messages.append({
                        "role"   : "assistant",
                        "content": answer,
                        "sources": sources,
                    })
                except Exception as e:
                    err = "Error al procesar la consulta: " + str(e)
                    st.error(err)
                    st.session_state.messages.append({
                        "role": "assistant", "content": err
                    })
        st.rerun()
