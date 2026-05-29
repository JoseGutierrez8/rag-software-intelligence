"""
Configura el entorno completo del proyecto RAG.
Ejecutar una sola vez después del scaffold:
  python setup.py
"""
import subprocess, sys, shutil, os

def run(cmd, desc):
    print(f"\n⏳  {desc}...")
    result = subprocess.run(cmd, shell=True, capture_output=False, text=True)
    if result.returncode != 0:
        print(f"  ⚠️  Advertencia en: {desc}")
    else:
        print(f"  ✔  {desc}")
    return result.returncode == 0

print("\n" + "═"*60)
print("  RAG Software Intelligence — Setup")
print("═"*60)

# 1. Entorno virtual
if not os.path.exists(".venv"):
    run(f"{sys.executable} -m venv .venv", "Creando entorno virtual (.venv)")
else:
    print("  ✔  Entorno virtual ya existe")

# 2. Instalar dependencias
pip = ".venv\\Scripts\\pip.exe" if sys.platform == "win32" else ".venv/bin/pip"
run(f"{pip} install --upgrade pip -q", "Actualizando pip")
run(f"{pip} install -r requirements.txt -q", "Instalando dependencias (puede tardar ~2 min)")

# 3. Crear .env desde ejemplo
if not os.path.exists(".env"):
    shutil.copy(".env.example", ".env")
    print("  ✔  Archivo .env creado desde .env.example")
else:
    print("  ✔  .env ya existe")

# 4. Crear directorios de datos
for d in ["data/repos", "data/chroma_db", "data/uploads"]:
    os.makedirs(d, exist_ok=True)
print("  ✔  Directorios data/ creados")

print("""
╔══════════════════════════════════════════════════════════════╗
║  ✅  Setup completo                                          ║
║                                                              ║
║  Próximos pasos:                                             ║
║  1. Copia tus archivos de dataset a data/uploads/            ║
║     - Arquitectura_EcommerceApp.drawio                       ║
║     - Diccionario_Datos_EcommerceApp.xlsx                    ║
║  2. Avisa a Claude: "Setup listo, comenzamos Fase 2"         ║
╚══════════════════════════════════════════════════════════════╝
""")
