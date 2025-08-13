
import json
from typing import Dict

class RegraMotorTEA:
    def __init__(self, config_path: str = "config_regras_tea.json"):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.regras = {
            "elegibilidade": self.regra_elegibilidade,
            "cobertura": self.regra_cobertura_tea,
            "limites": self.regra_limite_sessoes
        }

    def validar(self, contexto: Dict) -> Dict:
        resultado = {}
        for nome, regra in self.regras.items():
            resultado[nome] = regra(contexto)
        resultado["conforme"] = all(r["conforme"] for r in resultado.values())
        return resultado

    def regra_elegibilidade(self, ctx: Dict) -> Dict:
        if not ctx["beneficiario"]["ativo"]:
            return {"conforme": False, "mensagem": "Beneficiário inativo"}

        idade = ctx["beneficiario"]["idade"]
        idade_max = self.config["elegibilidade"]["idade_maxima"]
        if idade > idade_max:
            return {"conforme": False, "mensagem": f"Idade do beneficiário excede o limite de {idade_max} anos"}

        if ctx["beneficiario"]["carencia_dias"] > 0:
            return {"conforme": False, "mensagem": f"Carência de {ctx['beneficiario']['carencia_dias']} dias não cumprida"}

        return {"conforme": True, "mensagem": "Beneficiário elegível"}

    def regra_cobertura_tea(self, ctx: Dict) -> Dict:
        cid = ctx["procedimento"]["cid"]
        tipo = ctx["procedimento"]["tipo"]
        if not any(cid.startswith(prefixo) for prefixo in self.config["cobertura"]["cid_validos"]):
            return {"conforme": False, "mensagem": f"CID {cid} não compatível com TEA"}

        if tipo not in self.config["cobertura"]["tipos_terapia"]:
            return {"conforme": False, "mensagem": f"Terapia '{tipo}' não coberta para TEA"}

        return {"conforme": True, "mensagem": "Procedimento compatível com TEA"}

    def regra_limite_sessoes(self, ctx: Dict) -> Dict:
        idade = ctx["beneficiario"]["idade"]
        tipo = ctx["procedimento"]["tipo"]
        solicitadas = ctx["procedimento"]["quantidade"]

        limites = self.config["limites_sessoes"]

        if tipo not in limites:
            return {"conforme": False, "mensagem": f"Tipo de terapia '{tipo}' não parametrizado"}

        faixa = "ate_12" if idade <= 12 else "acima_12"
        limite = limites[tipo].get(faixa, 0)

        if solicitadas > limite:
            return {
                "conforme": False,
                "mensagem": f"{solicitadas} sessões excedem o limite de {limite} para '{tipo}' na faixa etária"
            }

        return {
            "conforme": True,
            "mensagem": f"{solicitadas} sessões estão dentro do limite autorizado para '{tipo}'"
        }
