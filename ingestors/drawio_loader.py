import os
import re
from typing import List
from xml.etree import ElementTree as ET
from langchain.schema import Document
from ingestors.base_loader import BaseLoader


class DrawioLoader(BaseLoader):
    """Parsea diagramas Draw.io y extrae nodos, capas y conexiones."""

    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> List[Document]:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError("Archivo no encontrado: " + self.file_path)

        tree     = ET.parse(self.file_path)
        root     = tree.getroot()
        cells    = root.findall(".//mxCell")
        filename = os.path.basename(self.file_path)
        documents = []
        nodes  = {}
        edges  = []
        layers = {}

        for cell in cells:
            cell_id   = cell.get("id", "")
            style     = cell.get("style", "")
            value     = self._clean_html(cell.get("value", ""))
            source_id = cell.get("source", "")
            target_id = cell.get("target", "")
            vertex    = cell.get("vertex", "0") == "1"
            edge      = cell.get("edge",   "0") == "1"

            if "swimlane" in style and value:
                layers[cell_id] = value
            elif vertex and value and cell_id not in ("0", "1"):
                nodes[cell_id] = value
            elif edge and (source_id or target_id):
                edges.append((source_id, target_id, value))

        for layer_id, layer_name in layers.items():
            text = "Capa de arquitectura: " + layer_name
            documents.append(self._make_doc(
                content=text,
                source=filename, file_type=".drawio",
                element_type="layer", element_id=layer_id,
                loader="DrawioLoader",
            ))

        for node_id, label in nodes.items():
            text = "Componente de arquitectura: " + label
            documents.append(self._make_doc(
                content=text,
                source=filename, file_type=".drawio",
                element_type="node", element_id=node_id,
                loader="DrawioLoader",
            ))

        for src_id, tgt_id, label in edges:
            src_label  = nodes.get(src_id) or layers.get(src_id) or src_id
            tgt_label  = nodes.get(tgt_id) or layers.get(tgt_id) or tgt_id
            edge_label = (" [" + label + "]") if label else ""
            text = ("Relacion en arquitectura: "
                    + src_label + " -> " + tgt_label + edge_label)
            documents.append(self._make_doc(
                content=text,
                source=filename, file_type=".drawio",
                element_type="edge",
                element_id=src_id + "->" + tgt_id,
                loader="DrawioLoader",
            ))

        print("  [DrawioLoader]", len(layers), "capas,",
              len(nodes), "nodos,", len(edges), "conexiones ->",
              len(documents), "documentos")
        return documents

    @staticmethod
    def _clean_html(text: str) -> str:
        text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return text.strip()
