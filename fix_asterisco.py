"""
Corrige el TTS para que no lea asteriscos, guiones ni markdown.
Ejecutar desde rag_software_intelligence:
  python fix_asterisco.py
"""
import re

with open("ui/app.py", "r", encoding="utf-8") as f:
    content = f.read()

old = '''def texto_a_voz(texto: str) -> bytes:
    from gtts import gTTS
    tts = gTTS(text=texto[:800], lang="es", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()'''

new = '''def texto_a_voz(texto: str) -> bytes:
    from gtts import gTTS
    import re
    # Limpiar markdown antes de enviar al TTS
    limpio = texto
    limpio = re.sub(r"\*\*(.+?)\*\*", r"\\1", limpio)   # **negrita**
    limpio = re.sub(r"\*(.+?)\*",     r"\\1", limpio)   # *cursiva*
    limpio = re.sub(r"`(.+?)`",       r"\\1", limpio)   # `codigo`
    limpio = re.sub(r"#{1,6}\s*",     "",     limpio)   # # titulos
    limpio = re.sub(r"\[(.+?)\]\(.*?\)", r"\\1", limpio) # [links](url)
    limpio = re.sub(r"^\s*[-*+]\s+", "", limpio, flags=re.MULTILINE) # listas
    limpio = re.sub(r"\*+",           "",     limpio)   # asteriscos sueltos
    limpio = re.sub(r"_+",            "",     limpio)   # guiones bajos
    limpio = re.sub(r"\s+",           " ",    limpio).strip()
    tts = gTTS(text=limpio[:800], lang="es", slow=False)
    buf = io.BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    return buf.read()'''

if old in content:
    content = content.replace(old, new)
    with open("ui/app.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Fix aplicado correctamente.")
else:
    # Buscar y reemplazar solo la linea del gTTS
    old2 = '    tts = gTTS(text=texto[:800], lang="es", slow=False)'
    new2 = '''    import re
    limpio = texto
    limpio = re.sub(r"\\*\\*(.+?)\\*\\*", r"\\1", limpio)
    limpio = re.sub(r"\\*(.+?)\\*",       r"\\1", limpio)
    limpio = re.sub(r"`(.+?)`",           r"\\1", limpio)
    limpio = re.sub(r"#{1,6}\\s*",        "",     limpio)
    limpio = re.sub(r"\\*+",              "",     limpio)
    limpio = re.sub(r"_+",               "",     limpio)
    limpio = re.sub(r"\\s+",             " ",    limpio).strip()
    tts = gTTS(text=limpio[:800], lang="es", slow=False)'''
    if old2 in content:
        content = content.replace(old2, new2)
        with open("ui/app.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("Fix aplicado (metodo alternativo).")
    else:
        print("No se encontro el bloque. Revisa ui/app.py manualmente.")

print("\nReinicia Streamlit:")
print("  streamlit run ui/app.py --server.fileWatcherType none")
