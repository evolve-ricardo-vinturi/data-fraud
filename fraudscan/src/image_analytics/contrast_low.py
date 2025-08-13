#Desvio Padrão	Interpretação
#< 10	Muito baixo contraste
#10–20	Baixo contraste
#> 20	Contraste adequado
import cv2
import numpy as np
from typing import Dict

class NFImageContrastAnalyzer:
    def __init__(self, image_path: str, threshold: float = 15.0):
        """
        :param image_path: Caminho da imagem da NF
        :param threshold: Limiar de contraste (quanto menor, mais exigente)
        """
        self.image_path = image_path
        self.threshold = threshold

    def analyze(self) -> Dict[str, any]:
        # Carrega a imagem em tons de cinza
        image = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Imagem inválida ou não encontrada")

        # Calcula o desvio padrão dos níveis de cinza
        std_dev = np.std(image)

        return {
            "contraste_std": round(float(std_dev), 2),
            "limite_contraste_baixo": self.threshold,
            "contraste_baixo": std_dev < self.threshold,
            "mensagem": "Contraste abaixo do ideal" if std_dev < self.threshold else "Contraste adequado"
        }
