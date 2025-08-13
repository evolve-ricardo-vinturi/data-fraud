
import requests
import requests_pkcs12
from lxml import etree
from typing import Dict, Any

class NFValidator:
    def __init__(self, consumer_key: str, consumer_secret: str, cert_path: str, cert_password: str, endpoint_base: str = "https://gateway.apiserpro.serpro.gov.br/api-consultanfe/v1"):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.cert_path = cert_path
        self.cert_password = cert_password
        self.token = None
        self.endpoint_base = endpoint_base

    def authenticate(self) -> None:
        auth = (self.consumer_key, self.consumer_secret)
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        resp = requests_pkcs12.post(
            "https://autenticacao.serpro.gov.br/authenticate",
            data={"grant_type": "client_credentials"},
            headers=headers,
            auth=auth,
            pkcs12_filename=self.cert_path,
            pkcs12_password=self.cert_password,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        self.token = data.get("access_token")
        if not self.token:
            raise RuntimeError("Token não retornado na autenticação")

    def consulta_nfe(self, chave_acesso: str) -> Dict[str, Any]:
        assert self.token, "Autentique antes de chamar consulta_nfe()"
        url = f"{self.endpoint_base}/notas/{chave_acesso}"
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/xml"}
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        xml = etree.fromstring(resp.content)
        ns = {"n": "http://www.portalfiscal.inf.br/nfe"}
        def t(tag): return xml.find(f".//n:{tag}", namespaces=ns)
        dados = {
            "nNF": t("nNF").text if t("nNF") is not None else None,
            "dhEmi": t("dhEmi").text if t("dhEmi") is not None else None,
            "vNF": t("vNF").text if t("vNF") is not None else None,
            "emit_CNPJ": t("CNPJ").text if t("CNPJ") is not None else None,
            "dest_CNPJ": xml.find(".//n:dest/n:CNPJ", namespaces=ns).text if xml.find(".//n:dest/n:CNPJ", namespaces=ns) is not None else None,
        }
        return dados

    def validar(self, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            self.authenticate()

        oficial = self.consulta_nfe(ocr_data["chave_acesso"].replace(" ", "").strip())
        validacoes = {}

        def get_nested(d, path):
            cur = d
            for p in path.split("."):
                cur = cur.get(p) if isinstance(cur, dict) else None
                if cur is None:
                    return None
            return cur

        mappings = {
            "numero_nota": "nNF",
            "data_emissao": "dhEmi",
            "valor_total": "vNF",
            "prestador.cnpj": "emit_CNPJ",
        }

        inconsistencias = []

        for ocr_key, oficial_key in mappings.items():
            ocr_v = get_nested(ocr_data, ocr_key)
            oficial_v = oficial.get(oficial_key)
            match = ocr_v and oficial_v and str(ocr_v) == str(oficial_v)
            validacoes[ocr_key] = {
                "ocr": ocr_v,
                "oficial": oficial_v,
                "match": match
            }
            if not match:
                inconsistencias.append({
                    "campo": ocr_key,
                    "valor_ocr": ocr_v,
                    "valor_oficial": oficial_v,
                    "conforme": False
                })

        return {
            "oficial": oficial,
            "validacoes": validacoes,
            "inconsistencias": inconsistencias
        }
