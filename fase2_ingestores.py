"""
FASE 2 — Ingestores Multiformato
Coloca este archivo en:
  rag_software_intelligence\\
Y ejecuta:
  python fase2_ingestores.py
"""

import os, textwrap

BASE = "."   # ya estamos dentro de rag_software_intelligence

FILES = {

# ══════════════════════════════════════════════════════════════════
# BASE LOADER (actualizado con helpers adicionales)
# ══════════════════════════════════════════════════════════════════
"ingestors/base_loader.py": '''
from abc import ABC, abstractmethod
from typing import List
from langchain.schema import Document


class BaseLoader(ABC):
    """Interfaz común para todos los ingestores del sistema RAG."""

    @abstractmethod
    def load(self) -> List[Document]:
        """
        Carga la fuente de datos y retorna una lista de Document.
        Cada Document incluye:
          - page_content : texto extraído
          - metadata     : {source, file_type, line, sheet, ...}
        """

    def _make_doc(self, content: str, **meta) -> Document:
        """Crea un Document con metadata estandarizada."""
        return Document(page_content=content.strip(), metadata=meta)

    def _safe_read(self, path: str, encoding: str = "utf-8") -> str:
        """Lee un archivo de texto con fallback a latin-1."""
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                return f.read()
''',

# ══════════════════════════════════════════════════════════════════
# GIT LOADER
# ══════════════════════════════════════════════════════════════════
"ingestors/git_loader.py": '''
import os
import shutil
from typing import List

import git
from langchain.schema import Document

from ingestors.base_loader import BaseLoader

# Extensiones de código que sí indexamos
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".cs", ".go", ".rb",
    ".php", ".cpp", ".c", ".h", ".rs", ".kt", ".scala",
    ".sql", ".sh", ".yaml", ".yml", ".json", ".toml",
    ".md", ".txt", ".cfg", ".ini",
}

# Carpetas y archivos que ignoramos siempre
IGNORE_DIRS  = {".git", "__pycache__", "node_modules", ".venv",
                "venv", "dist", "build", ".mypy_cache"}
IGNORE_FILES = {".DS_Store", "Thumbs.db", "*.pyc", "*.pyo"}


class GitLoader(BaseLoader):
    """
    Clona un repositorio Git (local o remoto) e indexa su código fuente.

    Cada archivo de código se convierte en un Document con metadata:
      source      : ruta relativa dentro del repo
      file_type   : extensión del archivo (e.g. '.py')
      repo_url    : URL del repositorio
      lines_total : total de líneas del archivo
    """

    def __init__(self, repo_url: str, clone_dir: str):
        """
        Args:
            repo_url  : URL de GitHub/GitLab o ruta local al repo.
            clone_dir : Directorio donde se clonará/buscará el repo.
        """
        self.repo_url  = repo_url
        self.clone_dir = clone_dir

    # ──────────────────────────────────────────────────────────────
    def load(self) -> List[Document]:
        repo_path = self._get_repo()
        documents = []

        for root, dirs, files in os.walk(repo_path):
            # Filtrar carpetas ignoradas
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext not in CODE_EXTENSIONS:
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, repo_path)

                content = self._safe_read(filepath)
                if not content.strip():
                    continue

                # Enriquecer con números de línea para trazabilidad
                lines = content.splitlines()
                numbered = "\n".join(
                    f"{i+1:>4}: {line}" for i, line in enumerate(lines)
                )

                doc = self._make_doc(
                    content=f"# Archivo: {rel_path}\n\n{numbered}",
                    source=rel_path,
                    file_type=ext,
                    repo_url=self.repo_url,
                    lines_total=len(lines),
                    loader="GitLoader",
                )
                documents.append(doc)

        print(f"  [GitLoader] {len(documents)} archivos indexados desde {self.repo_url}")
        return documents

    # ──────────────────────────────────────────────────────────────
    def _get_repo(self) -> str:
        """Clona el repo si no existe; lo actualiza si ya existe."""
        repo_name  = self.repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        local_path = os.path.join(self.clone_dir, repo_name)

        if os.path.exists(local_path):
            print(f"  [GitLoader] Repo ya existe en {local_path}, actualizando...")
            try:
                repo = git.Repo(local_path)
                repo.remotes.origin.pull()
            except Exception:
                pass  # Si falla el pull usamos la versión local
        else:
            print(f"  [GitLoader] Clonando {self.repo_url} en {local_path}...")
            os.makedirs(self.clone_dir, exist_ok=True)
            git.Repo.clone_from(self.repo_url, local_path)

        return local_path
''',

# ══════════════════════════════════════════════════════════════════
# DRAWIO LOADER
# ══════════════════════════════════════════════════════════════════
"ingestors/drawio_loader.py": '''
import os
from typing import List
from xml.etree import ElementTree as ET

from langchain.schema import Document

from ingestors.base_loader import BaseLoader


class DrawioLoader(BaseLoader):
    """
    Parsea diagramas Draw.io (.drawio / .xml) y extrae:
      - Nodos (componentes de la arquitectura)
      - Conexiones entre nodos (relaciones / flechas)
      - Etiquetas de capas (swimlanes)

    Cada elemento del diagrama se convierte en un Document con metadata:
      source      : ruta del archivo .drawio
      file_type   : '.drawio'
      element_type: 'node' | 'edge' | 'layer'
      element_id  : ID interno del elemento
      loader      : 'DrawioLoader'
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    # ──────────────────────────────────────────────────────────────
    def load(self) -> List[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Archivo Draw.io no encontrado: {self.file_path}")

        tree = ET.parse(self.file_path)
        root = tree.getroot()

        # El XML de Draw.io tiene la estructura:
        # <mxGraphModel> → <root> → <mxCell> (uno por elemento)
        cells     = root.findall(".//mxCell")
        documents = []
        filename  = os.path.basename(self.file_path)

        nodes   = {}   # id → label
        edges   = []   # lista de (source_id, target_id, label)
        layers  = {}   # id → nombre de capa

        # ── Primera pasada: identificar todos los elementos ──────
        for cell in cells:
            cell_id    = cell.get("id", "")
            style      = cell.get("style", "")
            value      = self._clean_html(cell.get("value", ""))
            source_id  = cell.get("source", "")
            target_id  = cell.get("target", "")
            vertex     = cell.get("vertex", "0") == "1"
            edge       = cell.get("edge",   "0") == "1"
            parent     = cell.get("parent", "")

            # Detectar swimlanes (capas contenedoras)
            if "swimlane" in style and value:
                layers[cell_id] = value

            # Nodos regulares con contenido
            elif vertex and value and cell_id not in ("0", "1"):
                nodes[cell_id] = value

            # Aristas / conexiones
            elif edge and (source_id or target_id):
                edges.append((source_id, target_id, value))

        # ── Documentos de capas ──────────────────────────────────
        for layer_id, layer_name in layers.items():
            doc = self._make_doc(
                content=(
                    f"Capa de arquitectura: {layer_name}\n"
                    f"Esta capa agrupa componentes relacionados con: {layer_name}."
                ),
                source=filename,
                file_type=".drawio",
                element_type="layer",
                element_id=layer_id,
                loader="DrawioLoader",
            )
            documents.append(doc)

        # ── Documentos de nodos ──────────────────────────────────
        for node_id, label in nodes.items():
            doc = self._make_doc(
                content=f"Componente de arquitectura: {label}",
                source=filename,
                file_type=".drawio",
                element_type="node",
                element_id=node_id,
                loader="DrawioLoader",
            )
            documents.append(doc)

        # ── Documentos de conexiones ─────────────────────────────
        for src_id, tgt_id, label in edges:
            src_label = nodes.get(src_id) or layers.get(src_id) or src_id
            tgt_label = nodes.get(tgt_id) or layers.get(tgt_id) or tgt_id
            edge_label = f" [{label}]" if label else ""

            doc = self._make_doc(
                content=(
                    f"Relación en arquitectura: "
                    f"{src_label} → {tgt_label}{edge_label}\n"
                    f"El componente '{src_label}' se conecta con '{tgt_label}'."
                ),
                source=filename,
                file_type=".drawio",
                element_type="edge",
                element_id=f"{src_id}->{tgt_id}",
                loader="DrawioLoader",
            )
            documents.append(doc)

        print(
            f"  [DrawioLoader] {len(layers)} capas, "
            f"{len(nodes)} nodos, {len(edges)} conexiones "
            f"→ {len(documents)} documentos"
        )
        return documents

    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _clean_html(text: str) -> str:
        """Elimina etiquetas HTML básicas de los labels de Draw.io."""
        import re
        text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()
''',

# ══════════════════════════════════════════════════════════════════
# EXCEL LOADER
# ══════════════════════════════════════════════════════════════════
"ingestors/excel_loader.py": '''
import os
from typing import List

import openpyxl
from langchain.schema import Document

from ingestors.base_loader import BaseLoader


class ExcelLoader(BaseLoader):
    """
    Lee diccionarios de datos en archivos Excel (.xlsx).

    Genera tres tipos de Document por cada hoja:
      1. Resumen de tabla  : nombre, nro. campos y descripción general.
      2. Detalle de campo  : un Document por cada fila de datos.
      3. Relaciones        : extrae FKs para construir grafo de dependencias.

    Metadata de cada Document:
      source     : nombre del archivo Excel
      file_type  : '.xlsx'
      sheet      : nombre de la hoja (= nombre de la tabla)
      row        : número de fila (para campos individuales)
      field_name : nombre del campo (para trazabilidad)
      loader     : 'ExcelLoader'
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    # ──────────────────────────────────────────────────────────────
    def load(self) -> List[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Archivo Excel no encontrado: {self.file_path}")

        wb       = openpyxl.load_workbook(self.file_path, data_only=True)
        filename = os.path.basename(self.file_path)
        documents = []

        for sheet_name in wb.sheetnames:
            ws   = wb[sheet_name]
            rows = list(ws.iter_rows(values_only=True))

            if len(rows) < 2:
                continue  # Hoja vacía o solo encabezado

            # ── Detectar fila de encabezado ──────────────────────
            # La primera fila no vacía con varias celdas llenas
            header_row_idx = None
            for i, row in enumerate(rows):
                non_empty = [c for c in row if c is not None]
                if len(non_empty) >= 2:
                    header_row_idx = i
                    break

            if header_row_idx is None:
                continue

            headers = [str(c).strip() if c else "" for c in rows[header_row_idx]]
            data_rows = rows[header_row_idx + 1:]

            # ── Documento resumen de la tabla ────────────────────
            resumen = self._make_doc(
                content=(
                    f"Tabla de base de datos: {sheet_name}\n"
                    f"Columnas del diccionario: {', '.join(h for h in headers if h)}\n"
                    f"Total de campos definidos: {len(data_rows)}"
                ),
                source=filename,
                file_type=".xlsx",
                sheet=sheet_name,
                element_type="table_summary",
                loader="ExcelLoader",
            )
            documents.append(resumen)

            # ── Documento por campo ──────────────────────────────
            for row_idx, row in enumerate(data_rows, start=header_row_idx + 2):
                if all(v is None for v in row):
                    continue  # Fila completamente vacía

                campo_dict = {}
                for h, val in zip(headers, row):
                    if h and val is not None:
                        campo_dict[h] = str(val).strip()

                if not campo_dict:
                    continue

                # Construir texto descriptivo del campo
                field_name = (
                    campo_dict.get("Campo")
                    or campo_dict.get("Field")
                    or list(campo_dict.values())[0]
                )
                lines = [f"Campo '{field_name}' en tabla '{sheet_name}':"]
                for k, v in campo_dict.items():
                    if v and v.lower() not in ("none", "null", "—", "-"):
                        lines.append(f"  {k}: {v}")

                doc = self._make_doc(
                    content="\n".join(lines),
                    source=filename,
                    file_type=".xlsx",
                    sheet=sheet_name,
                    row=row_idx,
                    field_name=field_name,
                    element_type="field",
                    loader="ExcelLoader",
                )
                documents.append(doc)

                # ── Detectar relaciones FK ───────────────────────
                fk_val = campo_dict.get("FK") or campo_dict.get("Relaciones") or ""
                if fk_val and fk_val not in ("—", "-", ""):
                    rel_doc = self._make_doc(
                        content=(
                            f"Relación de clave foránea: "
                            f"tabla '{sheet_name}', campo '{field_name}' "
                            f"referencia a {fk_val}"
                        ),
                        source=filename,
                        file_type=".xlsx",
                        sheet=sheet_name,
                        field_name=field_name,
                        element_type="foreign_key",
                        loader="ExcelLoader",
                    )
                    documents.append(rel_doc)

        print(f"  [ExcelLoader] {len(documents)} documentos desde {filename}")
        return documents
''',

# ══════════════════════════════════════════════════════════════════
# DOC LOADER (PDF + Markdown)
# ══════════════════════════════════════════════════════════════════
"ingestors/doc_loader.py": '''
import os
from typing import List

from langchain.schema import Document

from ingestors.base_loader import BaseLoader


class DocLoader(BaseLoader):
    """
    Carga documentación técnica en formato PDF o Markdown.

    Para PDF    : extrae texto página a página usando pypdf.
    Para Markdown: divide por secciones (encabezados ##).

    Metadata:
      source    : nombre del archivo
      file_type : '.pdf' o '.md'
      page      : número de página (PDF) o sección (MD)
      loader    : 'DocLoader'
    """

    def __init__(self, file_path: str):
        self.file_path = file_path

    # ──────────────────────────────────────────────────────────────
    def load(self) -> List[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Documento no encontrado: {self.file_path}")

        ext = os.path.splitext(self.file_path)[1].lower()

        if ext == ".pdf":
            return self._load_pdf()
        elif ext in (".md", ".markdown", ".txt"):
            return self._load_markdown()
        else:
            raise ValueError(f"DocLoader no soporta la extensión: {ext}")

    # ──────────────────────────────────────────────────────────────
    def _load_pdf(self) -> List[Document]:
        from pypdf import PdfReader

        reader    = PdfReader(self.file_path)
        filename  = os.path.basename(self.file_path)
        documents = []

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if not text:
                continue

            doc = self._make_doc(
                content=f"[PDF: {filename} — Página {page_num}]\n\n{text}",
                source=filename,
                file_type=".pdf",
                page=page_num,
                loader="DocLoader",
            )
            documents.append(doc)

        print(f"  [DocLoader/PDF] {len(documents)} páginas desde {filename}")
        return documents

    # ──────────────────────────────────────────────────────────────
    def _load_markdown(self) -> List[Document]:
        filename  = os.path.basename(self.file_path)
        content   = self._safe_read(self.file_path)
        documents = []

        # Dividir por encabezados de primer y segundo nivel
        import re
        sections = re.split(r"(?m)^(#{1,2}\s+.+)$", content)

        current_title = filename
        buffer        = []

        for part in sections:
            if re.match(r"^#{1,2}\s+", part):
                # Guardar sección anterior
                if buffer:
                    text = "\n".join(buffer).strip()
                    if text:
                        documents.append(self._make_doc(
                            content=f"[MD: {filename} — {current_title}]\n\n{text}",
                            source=filename,
                            file_type=".md",
                            section=current_title,
                            loader="DocLoader",
                        ))
                current_title = part.strip("# ").strip()
                buffer = []
            else:
                buffer.append(part)

        # Última sección
        if buffer:
            text = "\n".join(buffer).strip()
            if text:
                documents.append(self._make_doc(
                    content=f"[MD: {filename} — {current_title}]\n\n{text}",
                    source=filename,
                    file_type=".md",
                    section=current_title,
                    loader="DocLoader",
                ))

        print(f"  [DocLoader/MD] {len(documents)} secciones desde {filename}")
        return documents
''',

# ══════════════════════════════════════════════════════════════════
# INFRA LOADER
# ══════════════════════════════════════════════════════════════════
"ingestors/infra_loader.py": '''
import os
from typing import List

from langchain.schema import Document

from ingestors.base_loader import BaseLoader

INFRA_EXTENSIONS = {
    "Dockerfile", ".dockerfile",
    ".yaml", ".yml",
    ".toml", ".env.example",
}


class InfraLoader(BaseLoader):
    """
    Lee archivos de infraestructura:
      - Dockerfile / docker-compose.yaml
      - Manifiestos de Kubernetes (.yaml)
      - Archivos de configuración (.toml, .env.example)

    Puede recibir un archivo individual o un directorio completo.

    Metadata:
      source    : nombre del archivo
      file_type : extensión o 'Dockerfile'
      loader    : 'InfraLoader'
    """

    def __init__(self, path: str):
        """
        Args:
            path: Ruta a un archivo de infra individual o a un directorio.
        """
        self.path = path

    # ──────────────────────────────────────────────────────────────
    def load(self) -> List[Document]:
        documents = []

        if os.path.isfile(self.path):
            doc = self._load_file(self.path)
            if doc:
                documents.append(doc)
        elif os.path.isdir(self.path):
            for root, _, files in os.walk(self.path):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    if self._is_infra_file(fname):
                        doc = self._load_file(fpath)
                        if doc:
                            documents.append(doc)
        else:
            raise FileNotFoundError(f"Ruta no encontrada: {self.path}")

        print(f"  [InfraLoader] {len(documents)} archivos de infraestructura indexados")
        return documents

    # ──────────────────────────────────────────────────────────────
    def _load_file(self, filepath: str):
        filename = os.path.basename(filepath)
        ext      = os.path.splitext(filename)[1].lower() or filename

        content = self._safe_read(filepath)
        if not content.strip():
            return None

        # Detectar tipo específico para enriquecer el contexto
        infra_type = self._detect_type(filename, content)

        return self._make_doc(
            content=(
                f"[Infraestructura — {infra_type}]\n"
                f"Archivo: {filename}\n\n"
                f"{content}"
            ),
            source=filename,
            file_type=ext,
            infra_type=infra_type,
            loader="InfraLoader",
        )

    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _is_infra_file(filename: str) -> bool:
        name_lower = filename.lower()
        if name_lower in ("dockerfile", ".env.example", "makefile"):
            return True
        ext = os.path.splitext(filename)[1].lower()
        return ext in (".yaml", ".yml", ".toml", ".dockerfile", ".env")

    @staticmethod
    def _detect_type(filename: str, content: str) -> str:
        name_lower = filename.lower()
        if "dockerfile" in name_lower:
            return "Dockerfile"
        if "docker-compose" in name_lower:
            return "Docker Compose"
        if "kubernetes" in name_lower or ("apiVersion" in content and "kind:" in content):
            return "Kubernetes Manifest"
        if name_lower.endswith((".yaml", ".yml")):
            return "YAML Config"
        if name_lower.endswith(".toml"):
            return "TOML Config"
        if ".env" in name_lower:
            return "Variables de Entorno"
        return "Archivo de Infraestructura"
''',

# ══════════════════════════════════════════════════════════════════
# SCRIPT DE PRUEBA DE INGESTORES
# ══════════════════════════════════════════════════════════════════
"tests/test_ingestores_manual.py": '''
"""
Prueba manual de todos los ingestores.
Ejecutar desde la raíz del proyecto:
  python tests/test_ingestores_manual.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config.settings import GITHUB_REPO_URL, CLONE_DIR
from ingestors.git_loader    import GitLoader
from ingestors.drawio_loader import DrawioLoader
from ingestors.excel_loader  import ExcelLoader

UPLOADS = "data/uploads"

def separador(titulo):
    print(f"\n{'═'*55}")
    print(f"  {titulo}")
    print('═'*55)

# ── 1. Git ───────────────────────────────────────────────────────
separador("TEST 1 — GitLoader")
git_docs = GitLoader(GITHUB_REPO_URL, CLONE_DIR).load()
print(f"  Total documentos: {len(git_docs)}")
if git_docs:
    d = git_docs[0]
    print(f"  Primer archivo : {d.metadata['source']}")
    print(f"  Primeras líneas: {d.page_content[:200]}...")

# ── 2. Draw.io ───────────────────────────────────────────────────
separador("TEST 2 — DrawioLoader")
drawio_files = [f for f in os.listdir(UPLOADS) if f.endswith(".drawio")]
if drawio_files:
    drawio_docs = DrawioLoader(os.path.join(UPLOADS, drawio_files[0])).load()
    print(f"  Total documentos: {len(drawio_docs)}")
    for d in drawio_docs[:3]:
        print(f"  [{d.metadata['element_type']}] {d.page_content[:100]}")
else:
    print("  ⚠️  No se encontró archivo .drawio en data/uploads/")

# ── 3. Excel ─────────────────────────────────────────────────────
separador("TEST 3 — ExcelLoader")
xlsx_files = [f for f in os.listdir(UPLOADS) if f.endswith(".xlsx")]
if xlsx_files:
    excel_docs = ExcelLoader(os.path.join(UPLOADS, xlsx_files[0])).load()
    print(f"  Total documentos: {len(excel_docs)}")
    for d in excel_docs[:4]:
        print(f"  [{d.metadata.get('element_type','?')}] {d.page_content[:100]}")
else:
    print("  ⚠️  No se encontró archivo .xlsx en data/uploads/")

print(f"\n{'═'*55}")
print("  ✅  Tests de ingestores completados")
print('═'*55)
''',

}

# ══════════════════════════════════════════════════════════════════
# ESCRIBIR ARCHIVOS
# ══════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("  FASE 2 — Ingestores Multiformato")
print("═"*60)

for ruta, contenido in FILES.items():
    path = os.path.join(BASE, ruta)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(contenido).lstrip("\n"))
    print(f"  ✔  {ruta}")

print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ✅  Fase 2 completa — 5 ingestores implementados            ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  Ahora ejecuta la prueba de ingestores:                      ║
║                                                              ║
║    python tests/test_ingestores_manual.py                    ║
║                                                              ║
║  Deberías ver:                                               ║
║    TEST 1 → archivos del repo clonados                       ║
║    TEST 2 → nodos y capas del diagrama Draw.io               ║
║    TEST 3 → tablas y campos del Excel                        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
""")
