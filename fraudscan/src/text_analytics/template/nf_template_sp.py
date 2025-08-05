
import re
from nf_template_base import NotaFiscalTemplateBase
from typing import Dict

class NotaFiscalSaoPauloTemplate(NotaFiscalTemplateBase):
    def parse(self, text: str) -> Dict:
        def get(p, flags=0):
            match = re.search(p, text, flags)
            return match.group(1).strip() if match else None

        return {
            "modelo": "NFS-e - São Paulo",
            "numero_nota": get(r"Numero da Nota\s+(\d+)"),
            "data_emissao": get(r"Data e Hora de Emissao\s+([\d/: ]+)"),
            "codigo_verificacao": get(r"Codigo de Verificacao\s+([\w\-]+)"),
            "prestador": {
                "cnpj": get(r"PRESTADOR DE SERVICOS.*?CPF/CNPJ\s*:\s*([\d./\-]+)", re.DOTALL),
                "inscricao_municipal": get(r"Inscricao Municipal:\s*([\d\.\-]+)"),
                "razao_social": get(r"Nome/Razao Social:\s*(.+?)\s+Endereco", re.DOTALL),
                "endereco": get(r"Endereco:\s*(.+?)\s+Municipio", re.DOTALL),
                "municipio": get(r"Municipio:\s*(.+?)\s+UF"),
                "uf": get(r"UF:\s*(\w{2})")
            },
            "tomador": {
                "cnpj": get(r"TOMADOR DE SERVICOS.*?CPF/CNPJ\s*:\s*([\d./\-]+)", re.DOTALL),
                "razao_social": get(r"TOMADOR DE SERVICOS.*?Nome/Razao Social:\s*(.*?)\s+Endereco", re.DOTALL),
                "endereco": get(r"Endereco:\s*(.+?)\s+Municipio", re.DOTALL),
                "municipio": get(r"Municipio:\s*(.+?)\s+UF"),
                "uf": get(r"UF:\s*(\w{2})"),
                "email": get(r"E-mail:\s*([\w\.\-\+]+@[\w\.\-]+\.\w+)")
            },
            "intermediario": {
                "cnpj": get(r"INTERMEDIARIO DE SERVICOS.*?CPF/CNPJ\s*:\s*(.*?)\s+Nome", re.DOTALL),
                "razao_social": get(r"Nome/Razao Social:\s*(.*?)\s+DISCRIMINACAO", re.DOTALL)
            },
            "servico": {
                "descricao": get(r"DISCRIMINACAO DOS SERVICOS\s+(.*?)\n", re.DOTALL),
                "valor_total": get(r"VALOR TOTAL DO SERVICO\s*=\s*R\$?\s*([\d.,]+)"),
                "codigo_servico": get(r"Codigo do Servico\s+([\d\-]+)"),
                "descricao_servico": get(r"- (.+?)\.", re.DOTALL),
                "base_calculo": get(r"Base de Calculo \(R\$.*?\)\s+([\d.,]+)"),
                "aliquota": get(r"Aliquota\s+\(%\)\s+([\d.,]+)"),
                "valor_iss": get(r"Valor do ISS \(R\$.*?\)\s+([\d.,]+)"),
                "valor_aprox_tributos": get(r"Valor Aproximado dos Tributos \/ Fonte\s+=\s+R\$ ([\d.,]+)"),
                "ibpt_percentual": get(r"\(([\d.,]+%)\) \/ IBPT")
            },
            "informacoes_adicionais": get(r"OUTRAS INFORMACOES\s+\(1\)\s*(.*)", re.DOTALL)
        }
