#Técnica	Objetivo
#Hash perceptual (pHash)	Detecta imagens visualmente semelhantes
#Hash de diferença (dHash)	Detecta duplicação mesmo com redimensionamento
#Histograma de cor (RGB)	Verifica similaridade geral
#Similaridade estrutural (SSIM)	Opcional: pixel a pixel (mesmo tamanho)

import cv2
import numpy as np
from PIL import Image
import imagehash
from typing import Dict, List, Tuple
from pathlib import Path

class NFImageDuplicateAnalyzer:
    def __init__(self, image_path: str, known_images: List[str]):
        """
        :param image_path: Caminho da imagem a ser verificada
        :param known_images: Lista de caminhos de imagens para comparação
        """
        self.image_path = image_path
        self.known_images = known_images

    def compute_hashes(self, img: Image.Image) -> Dict[str, str]:
        return {
            "phash": str(imagehash.phash(img)),
            "dhash": str(imagehash.dhash(img))
        }

    def histogram_similarity(self, img1, img2) -> float:
        hist1 = cv2.calcHist([img1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([img2], [0], None, [256], [0, 256])
        sim = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        return sim

    def hamming_distance(self, hash1: str, hash2: str) -> int:
        return sum(ch1 != ch2 for ch1, ch2 in zip(hash1, hash2))

    def analyze(self) -> Dict[str, any]:
        target_img_pil = Image.open(self.image_path).convert("L").resize((256, 256))
        target_img_cv = cv2.imread(self.image_path, cv2.IMREAD_GRAYSCALE)
        target_hashes = self.compute_hashes(target_img_pil)

        duplicatas_detectadas = []

        for other_path in self.known_images:
            if not Path(other_path).is_file() or other_path == self.image_path:
                continue

            try:
                img_pil = Image.open(other_path).convert("L").resize((256, 256))
                img_cv = cv2.imread(other_path, cv2.IMREAD_GRAYSCALE)

                other_hashes = self.compute_hashes(img_pil)
                dhamming = self.hamming_distance(target_hashes["dhash"], other_hashes["dhash"])
                phamming = self.hamming_distance(target_hashes["phash"], other_hashes["phash"])
                hist_sim = self.histogram_similarity(target_img_cv, img_cv)

                if (dhamming <= 5 and phamming <= 5) or hist_sim > 0.97:
                    duplicatas_detectadas.append({
                        "imagem_comparada": other_path,
                        "dhash_distancia": dhamming,
                        "phash_distancia": phamming,
                        "hist_similaridade": round(hist_sim, 4)
                    })
            except Exception as e:
                continue

        return {
            "imagem": self.image_path,
            "total_comparadas": len(self.known_images),
            "duplicatas_detectadas": duplicatas_detectadas,
            "imagem_duplicada": bool(duplicatas_detectadas)
        }
