
#Aplica compressão JPEG para gerar diferenças;
#Gera a imagem ELA com realce;
#Calcula média, desvio padrão e máximo de diferença por pixel;
#Detecta se há indícios de edição localizada com base forense.

from PIL import Image, ImageChops, ImageEnhance
import numpy as np
import os
from typing import Dict

class NFImageELAAnalyzer:
    def __init__(self, image_path: str, quality: int = 90, diff_enhance: float = 20.0):
        self.image_path = image_path
        self.quality = quality
        self.diff_enhance = diff_enhance

    def perform_ela(self) -> Image.Image:
        original = Image.open(self.image_path).convert('RGB')
        temp_path = "temp_ela.jpg"
        original.save(temp_path, "JPEG", quality=self.quality)

        compressed = Image.open(temp_path)
        ela_image = ImageChops.difference(original, compressed)
        enhancer = ImageEnhance.Brightness(ela_image)
        ela_image = enhancer.enhance(self.diff_enhance)

        os.remove(temp_path)
        return ela_image

    def analyze(self) -> Dict[str, any]:
        ela_img = self.perform_ela()
        ela_np = np.asarray(ela_img).astype(np.int32)

        red_channel = ela_np[:, :, 0]
        mean = np.mean(red_channel)
        std = np.std(red_channel)
        max_val = np.max(red_channel)

        suspeita = std > 15 and max_val > 60

        return {
            "media_diferenca": round(float(mean), 2),
            "desvio_padrao": round(float(std), 2),
            "diferenca_maxima": int(max_val),
            "suspeita_de_edicao": suspeita,
            "mensagem": "Indícios de edição localizada detectados" if suspeita else "Nenhum indício forte de edição localizado"
        }
