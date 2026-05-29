"""
Agrega interfaz de voz (STT + TTS) a la app de Streamlit.
Ejecutar desde rag_software_intelligence:
  python fix_voz.py
Requiere internet para Google STT y gTTS.
"""

CONTENT = r'''
import streamlit as st
import sys, os, io, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import (OLLAMA_MODEL, CHROMA_PERSIST_DIR,
                              TOP_K_RESULTS, APP_TITLE)
from core.pipeline    import IngestionPipeline
from llm.chain        import RAGChain

# ── Configuracion ──────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="SoftwareArchitect",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  .main-title { font-size:1.8rem; font-weight:700; color:#1F3864; margin-bottom:0.2rem; }
  .subtitle   { font-size:0.85rem; color:#666; margin-bottom:1.5rem; }
  .source-card {
    background:#f0f4ff; border-left:4px solid #2E75B6;
    padding:0.5rem 0.8rem; margin:0.3rem 0;
    border-radius:0 6px 6px 0; font-size:0.8rem;
    font-family:monospace; color:#1a1a2e !important;
  }
  .source-card small { color:#444444 !important; }
  .voice-section {
    background:#f8f9fa; border:2px dashed #2E75B6;
    border-radius:10px; padding:1rem; margin:1rem 0;
  }
</style>
""", unsafe_allow_html=True)

# ── Estado de sesion ───────────────────────────────────────
for key, val in [("pipeline",None),("chain",None),("messages",[]),
                 ("indexed",False),("n_chunks",0)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Funciones de voz ───────────────────────────────────────
def transcribir_audio(audio_bytes: bytes) -> str:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        texto = recognizer.recognize_google(audio, language="es-ES")
        return texto
    except sr.UnknownValueError:
        return ""
    except Exception as e:
        return ""
    finally:
        try:
            os.remove(tmp_path)
        except:
            pass

def texto_a_voz(texto: str) -> bytes:
    from gtts import gTTS
    tts = gTTS(text=texto[:800], lang="es", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

# ── Sidebar ────────────────────────────────────────────────
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
        st.metric("Estado", "Listo" if st.session_state.indexed else "Pendiente")
    st.divider()

    if st.button("Indexar / Actualizar base de conocimiento",
                 use_container_width=True, type="primary"):
        with st.spinner("Cargando documentos e indexando..."):
            try:
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=True)
                st.session_state.pipeline  = pipeline
                st.session_state.chain     = RAGChain(pipeline.get_vector_store(),
                                                       model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
                st.session_state.indexed   = True
                st.session_state.n_chunks  = n
                st.session_state.messages  = []
                st.success("Base de conocimiento lista: " + str(n) + " chunks")
                st.rerun()
            except Exception as e:
                st.error("Error al indexar: " + str(e))

    if st.session_state.indexed:
        if st.button("Cargar indice existente", use_container_width=True):
            with st.spinner("Cargando indice..."):
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=False)
                st.session_state.pipeline = pipeline
                st.session_state.chain    = RAGChain(pipeline.get_vector_store(),
                                                      model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
                st.session_state.indexed  = True
                st.session_state.n_chunks = n
                st.rerun()

    if st.session_state.chain:
        if st.button("Limpiar historial", use_container_width=True):
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

# ── Area principal ─────────────────────────────────────────
st.markdown('<div class="main-title">Arquitecto de Software Senior</div>',
            unsafe_allow_html=True)
st.markdown('<div class="subtitle">Sistema RAG de Inteligencia y Trazabilidad '
            '| IA 2026 — UMG</div>', unsafe_allow_html=True)

# Auto-cargar indice si existe
if not st.session_state.indexed:
    from core.vector_store import VectorStoreManager
    vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
    if vs.load_existing():
        st.session_state.chain    = RAGChain(vs, model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
        st.session_state.indexed  = True
        st.session_state.n_chunks = vs.count()

if not st.session_state.indexed:
    st.info("Para comenzar, haz clic en **Indexar / Actualizar** en el panel izquierdo.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Codigo fuente Git**\nNavega el repositorio con trazabilidad por linea")
    with col2:
        st.markdown("**Diagramas Draw.io**\nExplica arquitectura y relaciones entre componentes")
    with col3:
        st.markdown("**Diccionario Excel**\nRastrear campos desde la BD hasta el codigo")
else:
    # ── SECCION DE VOZ ─────────────────────────────────────
    st.markdown('<div class="voice-section">', unsafe_allow_html=True)
    st.markdown("🎙️ **Comandos de Voz** — Graba tu consulta o escucha la ultima respuesta")
    col_mic, col_tts = st.columns([2, 1])

    with col_mic:
        audio_input = st.audio_input("Graba tu consulta en voz")
        if audio_input is not None:
            with st.spinner("Transcribiendo audio..."):
                texto = transcribir_audio(audio_input.read())
            if texto:
                st.success("Transcripcion: " + texto)
                st.session_state["pregunta_rapida"] = texto
            else:
                st.warning("No se pudo transcribir. Habla claro y en espanol.")

    with col_tts:
        st.markdown("**Reproducir ultima respuesta**")
        if st.session_state.messages:
            ultimas = [m for m in st.session_state.messages if m["role"] == "assistant"]
            if ultimas:
                if st.button("Leer respuesta en voz alta", use_container_width=True):
                    with st.spinner("Generando audio..."):
                        try:
                            audio_bytes = texto_a_voz(ultimas[-1]["content"])
                            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                        except Exception as e:
                            st.error("Error TTS: " + str(e))
        else:
            st.caption("Haz una consulta primero")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── HISTORIAL DE CHAT ──────────────────────────────────
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

    # Pregunta rapida del sidebar o voz
    pregunta_rapida = st.session_state.pop("pregunta_rapida", None)
    prompt = st.chat_input("Escribe tu consulta tecnica aqui...")
    if pregunta_rapida:
        prompt = pregunta_rapida

    if prompt and st.session_state.chain:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

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
                    # Auto-reproducir respuesta en voz
                    try:
                        audio_bytes = texto_a_voz(answer)
                        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                    except Exception:
                        pass  # Si falla el TTS la respuesta igual se muestra

                    st.session_state.messages.append({
                        "role": "assistant", "content": answer, "sources": sources,
                    })
                except Exception as e:
                    err = "Error: " + str(e)
                    st.error(err)
                    st.session_state.messages.append({"role": "assistant", "content": err})
        st.rerun()
'''

with open("ui/app.py", "w", encoding="utf-8") as f:
    f.write(CONTENT.lstrip("\n"))

print("ui/app.py actualizado con soporte de voz.")
print("Reinicia Streamlit:")
print("  streamlit run ui/app.py --server.fileWatcherType none")
