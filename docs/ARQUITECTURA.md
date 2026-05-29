# Arquitectura del Sistema RAG

## Diagrama de componentes

```
┌─────────────────────────────────────────────────────┐
│                  FUENTES DE DATOS                    │
│  Git Repo │ Draw.io │ Excel │ PDF/MD │ Dockerfile   │
└────────────────────────┬────────────────────────────┘
                         │
              ┌──────────▼──────────┐
              │  CAPA DE INGESTA    │
              │  (ingestors/)       │
              │  BaseLoader ──▶     │
              │  GitLoader          │
              │  DrawioLoader       │
              │  ExcelLoader        │
              │  DocLoader          │
              └──────────┬──────────┘
                         │ List[Document]
              ┌──────────▼──────────┐
              │  CORE RAG           │
              │  SmartChunker       │
              │  VectorStoreManager │
              │  (ChromaDB)         │
              └──────────┬──────────┘
                         │ búsqueda semántica
              ┌──────────▼──────────┐
              │  CAPA LLM           │
              │  RAGChain           │
              │  Prompts            │
              │  Ollama/llama3.2    │
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │  INTERFAZ           │
              │  Streamlit Chat     │
              │  Panel de fuentes   │
              └─────────────────────┘
```

## Estrategia de Chunking

| Tipo de fuente | Estrategia | Tamaño aprox. |
|---|---|---|
| Código Python | Por función/clase | 500-1000 tokens |
| Excel (diccionario) | Por tabla completa | 200-400 tokens |
| Draw.io | Por componente | 100-300 tokens |
| PDF / Markdown | Por párrafo + overlap | 800 tokens / 100 overlap |

## Seguridad
- Claves en `.env` (nunca en código)
- `.env` en `.gitignore`
- `.env.example` como referencia pública
