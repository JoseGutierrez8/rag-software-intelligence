from dotenv import load_dotenv
import os

load_dotenv()

# LLM
LLM_PROVIDER    = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "llama3.2")

# Vector Store
VECTOR_STORE      = os.getenv("VECTOR_STORE", "chroma")
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
CHUNK_SIZE        = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP     = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K_RESULTS     = int(os.getenv("TOP_K_RESULTS", "5"))

# Ingesta
GITHUB_REPO_URL = os.getenv("GITHUB_REPO_URL", "")
CLONE_DIR       = os.getenv("CLONE_DIR", "./data/repos")

# App
APP_TITLE = os.getenv("APP_TITLE", "RAG — Arquitecto de Software Senior")
APP_PORT  = int(os.getenv("APP_PORT", "8501"))

# Extensiones de código aceptadas
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rb",
    ".php", ".cpp", ".c", ".h", ".rs", ".kt", ".scala",
    ".sql", ".sh", ".yaml", ".yml", ".json", ".toml",
}

# Extensiones a ignorar en repos Git
IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico",
    ".pdf", ".zip", ".tar", ".gz", ".exe", ".dll",
    ".pyc", ".pyo", ".DS_Store",
}
