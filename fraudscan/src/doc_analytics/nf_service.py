
from src.text_analytics.template.nf_template_sp import NotaFiscalSaoPauloTemplate
from src.text_analytics.nota_fiscal_ocr import NotaFiscalOCR
from src.text_analytics.serpro_api import NFValidator
import json

class NFService():

    def __init__(self):
        pass

    def nf_extract(self, image_path):
        ocr = NotaFiscalOCR(template=NotaFiscalSaoPauloTemplate())
        resultado = ocr.processar(image_path)
        print("🧾 Dados extraídos via OCR:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))  

        # Etapa 2: Validação (substitua pelas suas credenciais e certificado)
        validator = NFValidator(
            consumer_key="SEU_CONSUMER_KEY",
            consumer_secret="SEU_CONSUMER_SECRET",
            cert_path="certificado.p12",
            cert_password="SENHA_DO_CERTIFICADO"
        )

        resultado_validacao = validator.validar(resultado)

        print("\n✅ Resultado da Validação:")
        print(json.dumps(resultado_validacao["validacoes"], indent=4, ensure_ascii=False))

        if resultado_validacao["inconsistencias"]:
            print("\n⚠️ Inconsistências encontradas:")
            for i in resultado_validacao["inconsistencias"]:
                print(f"- Campo: {i['campo']}")
                print(f"  OCR:     {i['valor_ocr']}")
                print(f"  Oficial: {i['valor_oficial']}")
                print(f"  Conforme: {i['conforme']}")
        else:
            print("\n🎉 Todos os campos conferem com a nota oficial!")