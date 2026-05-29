# Guía de Instalación

## Requisitos
- Python 3.10+
- Git 2.x
- Ollama con modelo llama3.2

## Pasos

```bash
# 1. Clonar o abrir el proyecto
cd rag_software_intelligence

# 2. Ejecutar setup (crea .venv e instala dependencias)
python setup.py

# 3. Activar entorno virtual
.venv\Scripts\activate          # Windows
source .venv/bin/activate        # Mac/Linux

# 4. Verificar Ollama
ollama list   # debe mostrar llama3.2

# 5. Lanzar la app
streamlit run ui/app.py
```

## Variables de entorno (.env)

| Variable | Descripción | Default |
|---|---|---|
| OLLAMA_MODEL | Modelo LLM local | llama3.2 |
| CHROMA_PERSIST_DIR | Ruta de la BD vectorial | ./data/chroma_db |
| GITHUB_REPO_URL | Repo a indexar | (tu repo) |
