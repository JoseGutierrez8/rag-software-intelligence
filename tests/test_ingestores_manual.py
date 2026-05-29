import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import GITHUB_REPO_URL, CLONE_DIR
from ingestors.git_loader    import GitLoader
from ingestors.drawio_loader import DrawioLoader
from ingestors.excel_loader  import ExcelLoader

UPLOADS = "data/uploads"
SEP = "=" * 55

def separador(titulo):
    print("\n" + SEP)
    print("  " + titulo)
    print(SEP)

# ── 1. Git ───────────────────────────────────────────────────
separador("TEST 1 — GitLoader")
git_docs = GitLoader(GITHUB_REPO_URL, CLONE_DIR).load()
print("  Total documentos:", len(git_docs))
if git_docs:
    d = git_docs[0]
    print("  Primer archivo :", d.metadata["source"])
    print("  Primeras lineas:", d.page_content[:200], "...")

# ── 2. Draw.io ───────────────────────────────────────────────
separador("TEST 2 — DrawioLoader")
drawio_files = [f for f in os.listdir(UPLOADS) if f.endswith(".drawio")]
if drawio_files:
    drawio_docs = DrawioLoader(os.path.join(UPLOADS, drawio_files[0])).load()
    print("  Total documentos:", len(drawio_docs))
    for d in drawio_docs[:3]:
        print("  [" + d.metadata["element_type"] + "]", d.page_content[:100])
else:
    print("  No se encontro archivo .drawio en data/uploads/")

# ── 3. Excel ─────────────────────────────────────────────────
separador("TEST 3 — ExcelLoader")
xlsx_files = [f for f in os.listdir(UPLOADS) if f.endswith(".xlsx")]
if xlsx_files:
    excel_docs = ExcelLoader(os.path.join(UPLOADS, xlsx_files[0])).load()
    print("  Total documentos:", len(excel_docs))
    for d in excel_docs[:4]:
        print("  [" + str(d.metadata.get("element_type", "?")) + "]",
              d.page_content[:100])
else:
    print("  No se encontro archivo .xlsx en data/uploads/")

print("\n" + SEP)
print("  Tests de ingestores completados")
print(SEP)
