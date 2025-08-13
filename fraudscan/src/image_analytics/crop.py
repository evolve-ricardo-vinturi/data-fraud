import cv2
import numpy as np
from typing import Dict

class NFImageCropAnalyzer:
    def __init__(self, image_path: str, crop_threshold: float = 0.3):
        """
        :param image_path: Caminho da imagem da nota fiscal
        :param crop_threshold: Percentual máximo de corte tolerado (ex: 0.3 = 30%)
        """
        self.image_path = image_path
        self.crop_threshold = crop_threshold

    def analyze(self) -> Dict[str, any]:
        image = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Imagem inválida ou não encontrada.")

        # Aplica threshold adaptativo para destacar regiões com conteúdo
        _, thresh = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        thresh = 255 - thresh  # Inverter: conteúdo vira branco

        # Detecta contornos externos
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return {
                "mensagem": "Nenhum conteúdo significativo detectado.",
                "recorte_detectado": True,
                "percentual_util": 0.0
            }

        # Encontra bounding box que cobre o maior contorno (área útil)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        area_util = w * h

        # Área da imagem original
        area_total = image.shape[0] * image.shape[1]

        # Calcula percentual aproveitado
        percentual_util = area_util / area_total
        corte_detectado = percentual_util < (1 - self.crop_threshold)

        return {
            "largura_imagem": image.shape[1],
            "altura_imagem": image.shape[0],
            "area_total": area_total,
            "area_util_detectada": area_util,
            "percentual_util": round(percentual_util * 100, 2),
            "recorte_detectado": corte_detectado,
            "mensagem": "Corte excessivo (>30%)" if corte_detectado else "Imagem com área preservada"
        }
