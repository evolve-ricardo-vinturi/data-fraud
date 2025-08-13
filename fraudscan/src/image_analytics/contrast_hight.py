#Desvio Padrão	Interpretação
#< 10	Muito baixo contraste
#10–20	Contraste ideal p/ OCR
#20–50	Contraste normal
#50–80	Alto contraste
#> 80	Contraste excessivo (suspeito)
import cv2
import numpy as np
from typing import Dict

class NFImageHighContrastAnalyzer:
    def __init__(self, image_path: str, high_threshold: float = 80.0):
        """
        :param image_path: Caminho da imagem da NF
        :param high_threshold: Limiar para contraste excessivo
        """
        self.image_path = image_path
        self.high_threshold = high_threshold

    def analyze(self) -> Dict[str, any]:
        # Carrega a imagem em escala de cinza
        image = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Imagem inválida ou não encontrada.")

        # Calcula o desvio padrão dos níveis de intensidade (contraste)
        std_dev = np.std(image)

        return {
            "contraste_std": round(float(std_dev), 2),
            "limite_contraste_excessivo": self.high_threshold,
            "contraste_excessivo": std_dev > self.high_threshold,
            "mensagem": "Contraste excessivamente alto" if std_dev > self.high_threshold else "Contraste dentro do limite"
        }
