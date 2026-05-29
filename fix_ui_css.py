"""
Corrige el color de texto en el panel de fuentes citadas.
Ejecutar desde rag_software_intelligence:
  python fix_ui_css.py
"""
with open("ui/app.py", "r", encoding="utf-8") as f:
    content = f.read()

old_css = """\
  .source-card {
    background: #f0f4ff;
    border-left: 4px solid #2E75B6;
    padding: 0.5rem 0.8rem;
    margin: 0.3rem 0;
    border-radius: 0 6px 6px 0;
    font-size: 0.8rem;
    font-family: monospace;
  }"""

new_css = """\
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
  }"""

if old_css in content:
    content = content.replace(old_css, new_css)
    with open("ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("CSS corregido en ui/app.py")
    print("Reinicia Streamlit: Ctrl+C en el PowerShell donde corre, luego streamlit run ui/app.py")
else:
    print("Aplicando correccion alternativa...")
    content = content.replace(
        'font-family: monospace;\n  }',
        'font-family: monospace;\n    color: #1a1a2e !important;\n  }\n  .source-card small {\n    color: #444444 !important;\n  }'
    )
    with open("ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("CSS corregido.")
    print("Reinicia Streamlit: Ctrl+C y luego streamlit run ui/app.py")
