"""
Reemplaza ui/app.py con interfaz profesional para presentacion.
Ejecutar desde rag_software_intelligence:
  python fix_ui_pro.py
"""

CONTENT = r'''
import streamlit as st
import sys, os, io, tempfile, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import (OLLAMA_MODEL, CHROMA_PERSIST_DIR,
                              TOP_K_RESULTS, APP_TITLE)
from core.pipeline import IngestionPipeline
from llm.chain     import RAGChain

# ── Configuracion de pagina ──────────────────────────────────────
st.set_page_config(
    page_title="RAG — Arquitecto de Software Senior | UMG 2026",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS profesional ──────────────────────────────────────────────
st.markdown("""
<style>
/* ── Fuentes y base ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ── Ocultar elementos default de Streamlit ── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* ── Header institucional ── */
.inst-header {
    background: linear-gradient(135deg, #0d1b2a 0%, #1b2a3b 50%, #0d1b2a 100%);
    border-bottom: 3px solid #c8a951;
    padding: 1.2rem 2rem;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.inst-left { display: flex; flex-direction: column; }
.inst-title {
    font-size: 1.4rem; font-weight: 700;
    color: #ffffff; margin: 0; letter-spacing: 0.3px;
}
.inst-subtitle {
    font-size: 0.78rem; color: #c8a951;
    margin: 0.1rem 0 0 0; font-weight: 400;
}
.inst-right { text-align: right; }
.inst-badge {
    background: #c8a951; color: #0d1b2a;
    padding: 0.25rem 0.8rem; border-radius: 20px;
    font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.5px;
}
.inst-course {
    font-size: 0.72rem; color: #8899aa;
    margin-top: 0.3rem;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #0d1b2a;
    border-right: 1px solid #1e3a5f;
}
section[data-testid="stSidebar"] * { color: #e0e8f0 !important; }
.sidebar-section {
    background: #142233;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.8rem;
    margin: 0.5rem 0;
}
.sidebar-label {
    font-size: 0.7rem; font-weight: 600;
    color: #c8a951 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.3rem;
}
.sidebar-value {
    font-size: 0.85rem; font-weight: 500;
    color: #ffffff !important;
}
.status-badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}
.status-listo    { background: #0f3d2e; color: #4ade80; border: 1px solid #166534; }
.status-pendiente{ background: #3d1f0f; color: #fb923c; border: 1px solid #7c2d12; }

/* ── Mensajes del chat ── */
.chat-user {
    background: linear-gradient(135deg, #1e3a5f, #1b3050);
    border: 1px solid #2e5080;
    border-radius: 12px 12px 2px 12px;
    padding: 0.9rem 1.1rem;
    margin: 0.8rem 0;
    max-width: 85%;
    margin-left: auto;
    color: #e8f0fe !important;
}
.chat-assistant {
    background: #0f1e2e;
    border: 1px solid #1e3a5f;
    border-left: 3px solid #c8a951;
    border-radius: 2px 12px 12px 12px;
    padding: 0.9rem 1.1rem;
    margin: 0.8rem 0;
    max-width: 95%;
    color: #d0dce8 !important;
}
.chat-label-user {
    font-size: 0.7rem; color: #7ca9d4;
    font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 0.3rem;
}
.chat-label-asst {
    font-size: 0.7rem; color: #c8a951;
    font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 0.3rem;
}

/* ── Fuentes citadas ── */
.sources-container {
    background: #0a1520;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.7rem;
    margin-top: 0.7rem;
}
.sources-title {
    font-size: 0.72rem; color: #c8a951;
    font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 0.5rem;
}
.source-item {
    background: #142233;
    border-left: 3px solid #1e6fba;
    border-radius: 0 6px 6px 0;
    padding: 0.5rem 0.7rem;
    margin: 0.3rem 0;
    font-size: 0.78rem;
    font-family: 'Courier New', monospace;
    color: #a0c4e8 !important;
}
.source-item .src-file { color: #7dd3fc; font-weight: 600; }
.source-item .src-type { color: #c8a951; font-size: 0.68rem; }
.source-item .src-prev { color: #6b8a9e; font-size: 0.72rem; margin-top: 0.2rem; }

/* ── Seccion de voz ── */
.voice-container {
    background: #0f1e2e;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin: 0.8rem 0;
}
.voice-title {
    font-size: 0.8rem; color: #c8a951;
    font-weight: 600; text-transform: uppercase;
    letter-spacing: 0.5px; margin-bottom: 0.7rem;
    display: flex; align-items: center; gap: 0.4rem;
}

/* ── Pantalla de bienvenida ── */
.welcome-card {
    background: #0f1e2e;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 1.5rem;
    text-align: center;
    margin: 0.5rem 0;
}
.welcome-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.welcome-title { font-size: 1rem; font-weight: 600; color: #c8a951; }
.welcome-desc  { font-size: 0.82rem; color: #7a95aa; margin-top: 0.3rem; }

/* ── Input del chat ── */
.stChatInputContainer { border-top: 1px solid #1e3a5f !important; }

/* ── Métricas ── */
[data-testid="metric-container"] {
    background: #142233;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Estado de sesion ─────────────────────────────────────────────
for key, val in [("pipeline",None),("chain",None),("messages",[]),
                 ("indexed",False),("n_chunks",0)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Funciones de voz ─────────────────────────────────────────────
def transcribir_audio(audio_bytes: bytes) -> str:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio, language="es-ES")
    except Exception:
        return ""
    finally:
        try: os.remove(tmp_path)
        except: pass

def texto_a_voz(texto: str) -> bytes:
    from gtts import gTTS
    limpio = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    limpio = re.sub(r"\*(.+?)\*",     r"\1", limpio)
    limpio = re.sub(r"`(.+?)`",       r"\1", limpio)
    limpio = re.sub(r"#{1,6}\s*",     "",    limpio)
    limpio = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", limpio)
    limpio = re.sub(r"^\s*[-*+]\s+", "",    limpio, flags=re.MULTILINE)
    limpio = re.sub(r"\*+",           "",    limpio)
    limpio = re.sub(r"_+",            "",    limpio)
    limpio = re.sub(r"\s+",           " ",   limpio).strip()
    tts = gTTS(text=limpio[:800], lang="es", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()

# ── Auto-cargar indice ───────────────────────────────────────────
if not st.session_state.indexed:
    from core.vector_store import VectorStoreManager
    vs = VectorStoreManager(CHROMA_PERSIST_DIR, OLLAMA_MODEL)
    if vs.load_existing():
        st.session_state.chain    = RAGChain(vs, model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
        st.session_state.indexed  = True
        st.session_state.n_chunks = vs.count()

# ── SIDEBAR ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 1rem 0;">
        <div style="font-size:2rem;">🏛️</div>
        <div style="font-size:0.95rem; font-weight:700; color:#ffffff;">RAG Software Intelligence</div>
        <div style="font-size:0.7rem; color:#c8a951; margin-top:0.2rem;">
            Universidad Mariano Galvez
        </div>
        <div style="font-size:0.68rem; color:#556677; margin-top:0.1rem;">
            Inteligencia Artificial — Noveno Ciclo 2026
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Chunks", st.session_state.n_chunks)
    with col2:
        st.metric("Estado", "Listo" if st.session_state.indexed else "Pendiente")

    st.markdown("""
    <div class="sidebar-section">
        <div class="sidebar-label">Motor LLM</div>
        <div class="sidebar-value">Ollama · llama3.2</div>
        <div class="sidebar-label" style="margin-top:0.5rem;">Vector DB</div>
        <div class="sidebar-value">ChromaDB · Local</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("⚡  Indexar / Actualizar conocimiento",
                 use_container_width=True, type="primary"):
        with st.spinner("Procesando documentos..."):
            try:
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=True)
                st.session_state.pipeline  = pipeline
                st.session_state.chain     = RAGChain(pipeline.get_vector_store(),
                                                       model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
                st.session_state.indexed   = True
                st.session_state.n_chunks  = n
                st.session_state.messages  = []
                st.success(str(n) + " vectores indexados")
                st.rerun()
            except Exception as e:
                st.error("Error: " + str(e))

    if st.session_state.indexed:
        if st.button("📂  Cargar indice existente", use_container_width=True):
            with st.spinner("Cargando..."):
                pipeline = IngestionPipeline()
                n = pipeline.run(force_rebuild=False)
                st.session_state.pipeline = pipeline
                st.session_state.chain    = RAGChain(pipeline.get_vector_store(),
                                                      model=OLLAMA_MODEL, top_k=TOP_K_RESULTS)
                st.session_state.indexed  = True
                st.session_state.n_chunks = n
                st.rerun()

    if st.session_state.chain:
        if st.button("🗑️  Limpiar historial", use_container_width=True):
            st.session_state.messages = []
            st.session_state.chain.clear_history()
            st.rerun()

    st.divider()
    st.markdown('<div class="sidebar-label">Consultas de ejemplo</div>',
                unsafe_allow_html=True)

    ejemplos = [
        "Que tablas define el Diccionario_Inventario.xlsx y cuales son sus claves foraneas",
        "En que archivos de codigo se usa el campo id_producto definido en la tabla productos",
        "Explica las capas de la arquitectura del sistema de inventario",
        "Que hace la funcion registrar_entrada y que archivos involucra?",
        "Si cambio el campo stock_minimo, que archivos se veerian afectados?",
        "Cuales son los roles validos en la clase RolUsuario del archivo usuario.py",
        "Como funciona el metodo cambiar_estado en el modelo pedido.py",
        "Que tipos de movimiento de inventario existen?",
        "Que campos tiene la tabla movimientos segun el Diccionario_Inventario.xlsx",
        "Como funciona la funcion verificar_stock_minimo en alerta_service.py",
    ]
    for ej in ejemplos:
        if st.button(ej, use_container_width=True, key="ej_" + ej[:25]):
            st.session_state["pregunta_rapida"] = ej

    st.divider()
    st.markdown("""
    <div style="font-size:0.65rem; color:#445566; text-align:center; padding:0.3rem;">
        Sistema RAG · IA 2026 · UMG<br>
        Ingenieria en Sistemas de Informacion
    </div>
    """, unsafe_allow_html=True)

# ── AREA PRINCIPAL ───────────────────────────────────────────────
st.markdown("""
<div class="inst-header">
    <div class="inst-left">
        <div class="inst-title">🏗️ Arquitecto de Software Senior Virtual</div>
        <div class="inst-subtitle">
            Sistema de Inteligencia y Trazabilidad de Software — RAG
        </div>
    </div>
    <div class="inst-right">
        <div class="inst-badge">UMG · IA 2026</div>
        <div class="inst-course">
            Ingenieria en Sistemas de Informacion<br>
            Noveno Ciclo · Seccion A
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.indexed:
    cols = st.columns(3)
    items = [
        ("💻", "Codigo Fuente Git",
         "Indexa repositorios Python con trazabilidad por archivo y numero de linea"),
        ("📐", "Diagramas Draw.io",
         "Parsea arquitecturas XML: capas, nodos y conexiones entre componentes"),
        ("📊", "Diccionario Excel",
         "Lee tablas, campos, tipos de datos y relaciones de claves foraneas"),
    ]
    for col, (icon, title, desc) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="welcome-card">
                <div class="welcome-icon">{icon}</div>
                <div class="welcome-title">{title}</div>
                <div class="welcome-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)
    st.info("Para comenzar, haz clic en **⚡ Indexar / Actualizar conocimiento** en el panel izquierdo.")

else:
    # ── SECCION DE VOZ ────────────────────────────────────────
    st.markdown('<div class="voice-container"><div class="voice-title">🎙️ Comandos de Voz</div>',
                unsafe_allow_html=True)
    col_mic, col_tts = st.columns([2, 1])
    with col_mic:
        audio_input = st.audio_input("Graba tu consulta")
        if audio_input is not None:
            with st.spinner("Transcribiendo..."):
                texto = transcribir_audio(audio_input.read())
            if texto:
                st.success("✔ " + texto)
                st.session_state["pregunta_rapida"] = texto
            else:
                st.warning("No se pudo transcribir. Habla claro en español.")
    with col_tts:
        st.markdown("**Reproducir ultima respuesta**")
        if st.session_state.messages:
            ultimas = [m for m in st.session_state.messages if m["role"] == "assistant"]
            if ultimas:
                if st.button("🔊 Leer en voz alta", use_container_width=True):
                    with st.spinner("Generando audio..."):
                        try:
                            ab = texto_a_voz(ultimas[-1]["content"])
                            st.audio(ab, format="audio/mp3", autoplay=True)
                        except Exception as e:
                            st.error("Error TTS: " + str(e))
        else:
            st.caption("Haz una consulta primero")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ── HISTORIAL DEL CHAT ────────────────────────────────────
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"""
            <div class="chat-user">
                <div class="chat-label-user">🧑 Tu consulta</div>
                {msg["content"]}
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="chat-assistant">
                <div class="chat-label-asst">🏗️ Arquitecto Senior</div>
                {msg["content"]}
            </div>""", unsafe_allow_html=True)
            if "sources" in msg and msg["sources"]:
                src_html = '<div class="sources-container"><div class="sources-title">📎 Fuentes citadas (' + str(len(msg["sources"])) + ')</div>'
                for s in msg["sources"]:
                    src_html += (
                        '<div class="source-item">'
                        '<span class="src-file">' + s["file"] + '</span> '
                        '<span class="src-type">[' + s["type"] + ']</span>'
                        '<div class="src-prev">' + s["preview"][:100] + '...</div>'
                        '</div>'
                    )
                src_html += '</div>'
                st.markdown(src_html, unsafe_allow_html=True)

    # ── INPUT ─────────────────────────────────────────────────
    pregunta_rapida = st.session_state.pop("pregunta_rapida", None)
    prompt = st.chat_input("Escribe tu consulta tecnica aqui...")
    if pregunta_rapida:
        prompt = pregunta_rapida

    if prompt and st.session_state.chain:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(f"""
        <div class="chat-user">
            <div class="chat-label-user">🧑 Tu consulta</div>
            {prompt}
        </div>""", unsafe_allow_html=True)

        with st.spinner("Consultando base de conocimiento..."):
            try:
                result  = st.session_state.chain.ask(prompt)
                answer  = result["answer"]
                sources = result["sources"]

                st.markdown(f"""
                <div class="chat-assistant">
                    <div class="chat-label-asst">🏗️ Arquitecto Senior</div>
                    {answer}
                </div>""", unsafe_allow_html=True)

                if sources:
                    src_html = '<div class="sources-container"><div class="sources-title">📎 Fuentes citadas (' + str(len(sources)) + ')</div>'
                    for s in sources:
                        src_html += (
                            '<div class="source-item">'
                            '<span class="src-file">' + s["file"] + '</span> '
                            '<span class="src-type">[' + s["type"] + ']</span>'
                            '<div class="src-prev">' + s["preview"][:100] + '...</div>'
                            '</div>'
                        )
                    src_html += '</div>'
                    st.markdown(src_html, unsafe_allow_html=True)

                try:
                    ab = texto_a_voz(answer)
                    st.audio(ab, format="audio/mp3", autoplay=True)
                except Exception:
                    pass

                st.session_state.messages.append({
                    "role": "assistant", "content": answer, "sources": sources,
                })
            except Exception as e:
                st.error("Error: " + str(e))
        st.rerun()
'''

with open("ui/app.py", "w", encoding="utf-8") as f:
    f.write(CONTENT.lstrip("\n"))

print("ui/app.py actualizado con interfaz profesional.")
print("Reinicia Streamlit:")
print("  streamlit run ui/app.py --server.fileWatcherType none")
