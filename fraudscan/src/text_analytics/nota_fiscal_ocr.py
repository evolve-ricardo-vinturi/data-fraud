
import cv2
import pytesseract
from typing import Dict
from template.nf_template_base import NotaFiscalTemplateBase

class NotaFiscalOCR:
    def __init__(self, template: NotaFiscalTemplateBase, lang: str = "por"):
        self.template = template
        self.lang = lang

    def preprocess_image(self, image_path: str):
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 3)
        return gray

    def extract_text(self, image) -> str:
        config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(image, lang=self.lang, config=config)

    def processar(self, image_path: str) -> Dict:
        image = self.preprocess_image(image_path)
        text = self.extract_text(image)
        return self.template.parse(text)