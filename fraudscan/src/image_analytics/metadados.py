
import exifread
from typing import Dict, Any

class NFImageMetadataAnalyzer:
    SUSPECT_SOFTWARES = [
        "Adobe Photoshop", "GIMP", "Corel", "Paint.NET", "Pixelmator",
        "Snapseed", "Photoscape", "Photopea", "Lightroom", "VSCO", "Canva"
    ]

    def __init__(self, image_path: str):
        self.image_path = image_path

    def extract_metadata(self) -> Dict[str, str]:
        with open(self.image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
        return {tag: str(value) for tag, value in tags.items()}

    def detect_suspect_software(self, software_str: str) -> Dict[str, Any]:
        for suspect in self.SUSPECT_SOFTWARES:
            if suspect.lower() in software_str.lower():
                return {
                    "editado_por_software_suspeito": True,
                    "nome_software_detectado": suspect
                }
        return {
            "editado_por_software_suspeito": False,
            "nome_software_detectado": None
        }

    def analyze(self) -> Dict[str, Any]:
        metadata = self.extract_metadata()
        software_raw = metadata.get("Software", "") or metadata.get("Image Software", "")

        software_info = self.detect_suspect_software(software_raw)

        return {
            "software_detectado": software_raw or "Não informado",
            **software_info,
            "data_criacao": metadata.get("EXIF DateTimeOriginal") or metadata.get("Image DateTime") or "Desconhecida",
            "data_modificacao": metadata.get("EXIF DateTimeDigitized") or "Desconhecida",
            "fabricante_camera": metadata.get("Image Make", "Desconhecida"),
            "modelo_camera": metadata.get("Image Model", "Desconhecido"),
            "tem_metadados": bool(metadata),
            "total_tags": len(metadata),
            "todas_as_tags": metadata
        }

    def validar_integridade(self) -> Dict[str, Any]:
        analise = self.analyzer.analyze()

        suspeitas = []

        if analise["editado_por_software_suspeito"]:
            suspeitas.append(f"Imagem editada por software suspeito: {analise['nome_software_detectado']}")

        if analise["data_criacao"] != analise["data_modificacao"]:
            suspeitas.append("Data de modificação diferente da data de criação (possível edição)")

        if analise["fabricante_camera"] == "Desconhecida" or analise["modelo_camera"] == "Desconhecido":
            suspeitas.append("Informações da câmera ausentes ou removidas")

        if not analise["tem_metadados"] or analise["total_tags"] < 5:
            suspeitas.append("Metadados ausentes ou muito reduzidos (possível limpeza de evidências)")

        return {
            "imagem": self.image_path,
            "suspeitas": suspeitas,
            "analise_detalhada": analise,
            "imagem_suspeita": bool(suspeitas)
        }
