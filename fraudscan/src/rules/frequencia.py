# regra_motor_frequencia.py
# -*- coding: utf-8 -*-
"""
Motor de Regras: Frequência e Temporalidade
-------------------------------------------
Valida:
1) Frequência máxima por período (diário/semanal/mensal/anual) por tipo de sessão
2) Intervalo mínimo (em dias) entre sessões do mesmo tipo
3) Período mínimo de repetição proibida (em dias) para certos procedimentos (ex.: reexame)
4) Proibição de múltiplas sessões no mesmo dia para tipos configurados
"""

from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime, date
import json

DateLike = Union[str, date, datetime]


class RegraMotorFrequencia:
    PERIODOS_SUPORTADOS = {"diario", "semanal", "mensal", "anual"}

    def __init__(self, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None) -> None:
        if config is None and config_path is None:
            raise ValueError("Forneça 'config' ou 'config_path'.")

        if config is None:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

        self.config = config
        self._freq_max = config.get("frequencia_maxima", {})
        self._int_min = config.get("intervalo_minimo_dias", {})
        self._rep_proib = config.get("periodo_repeticao_proibida", {})
        self._no_same_day = set(config.get("nao_permitir_mesmo_dia", []))

        for tipo, regra in self._freq_max.items():
            periodo = str(regra.get("periodo", "")).lower()
            if periodo not in self.PERIODOS_SUPORTADOS:
                raise ValueError(f"Período inválido para '{tipo}': {periodo}. Suportados: {self.PERIODOS_SUPORTADOS}")
            qtd = regra.get("quantidade")
            if not isinstance(qtd, int) or qtd < 0:
                raise ValueError(f"Quantidade inválida em frequencia_maxima para '{tipo}': {qtd}")

    @staticmethod
    def _parse_date(d: DateLike) -> date:
        if isinstance(d, date) and not isinstance(d, datetime):
            return d
        if isinstance(d, datetime):
            return d.date()
        return datetime.strptime(d, "%Y-%m-%d").date()

    @staticmethod
    def _week_year_key(dt: date) -> Tuple[int, int]:
        iso_year, iso_week, _ = dt.isocalendar()
        return iso_year, iso_week

    @staticmethod
    def _month_year_key(dt: date) -> Tuple[int, int]:
        return dt.year, dt.month

    @staticmethod
    def _year_key(dt: date) -> int:
        return dt.year

    def _period_key(self, dt: date, periodo: str) -> Tuple:
        periodo = periodo.lower()
        if periodo == "diario":
            return (dt.year, dt.month, dt.day)
        if periodo == "semanal":
            return self._week_year_key(dt)
        if periodo == "mensal":
            return self._month_year_key(dt)
        if periodo == "anual":
            return (self._year_key(dt),)
        raise ValueError(f"Período não suportado: {periodo}")

    def _count_in_period(self, historico: List[Dict[str, Any]], tipo: str, periodo: str, data_ref: date) -> int:
        key_ref = self._period_key(data_ref, periodo)
        count = 0
        for sess in historico:
            if sess.get("tipo") != tipo:
                continue
            d = self._parse_date(sess["data"])
            if self._period_key(d, periodo) == key_ref:
                count += 1
        return count

    def _last_session_date(self, historico: List[Dict[str, Any]], tipo: str, ate_data: date) -> Optional[date]:
        datas = [
            self._parse_date(s["data"])
            for s in historico
            if s.get("tipo") == tipo and self._parse_date(s["data"]) <= ate_data
        ]
        return max(datas) if datas else None

    def _same_day_count(self, historico: List[Dict[str, Any]], tipo: str, data_ref: date) -> int:
        return sum(1 for s in historico if s.get("tipo") == tipo and self._parse_date(s["data"]) == data_ref)

    def _rule_frequencia_maxima(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        proc = ctx["procedimento"]
        tipo: str = proc["tipo"]
        qtd_solic: int = int(proc.get("quantidade", 1))
        data_sol: date = self._parse_date(proc["data_solicitacao"])
        hist: List[Dict[str, Any]] = ctx.get("historico_sessoes", [])

        if tipo not in self._freq_max:
            return {
                "conforme": True,
                "mensagem": f"Sem regra de frequência configurada para '{tipo}'.",
                "evidencias": {"atual_no_periodo": 0, "limite": None}
            }

        periodo = self._freq_max[tipo]["periodo"].lower()
        limite = int(self._freq_max[tipo]["quantidade"])
        atual = self._count_in_period(hist, tipo, periodo, data_sol)
        total_pos_exec = atual + qtd_solic

        conforme = total_pos_exec <= limite
        msg = (
            f"Frequência OK: {total_pos_exec}/{limite} no período {periodo}."
            if conforme else
            f"Excede frequência: {total_pos_exec}/{limite} no período {periodo}."
        )
        return {
            "conforme": conforme,
            "mensagem": msg,
            "evidencias": {
                "periodo": periodo,
                "consumido_no_periodo": atual,
                "solicitado": qtd_solic,
                "total_pos_execucao": total_pos_exec,
                "limite": limite
            }
        }

    def _rule_intervalo_minimo(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        proc = ctx["procedimento"]
        tipo: str = proc["tipo"]
        qtd_solic: int = int(proc.get("quantidade", 1))
        data_sol: date = self._parse_date(proc["data_solicitacao"])
        hist: List[Dict[str, Any]] = ctx.get("historico_sessoes", [])

        min_days = int(self._int_min.get(tipo, 0))
        if min_days <= 0:
            return {
                "conforme": True,
                "mensagem": f"Sem intervalo mínimo configurado para '{tipo}'.",
                "evidencias": {"intervalo_minimo_dias": 0}
            }

        last_dt = self._last_session_date(hist, tipo, data_sol)
        if not last_dt:
            return {
                "conforme": True,
                "mensagem": "Não há sessões anteriores; intervalo mínimo atendido.",
                "evidencias": {"intervalo_minimo_dias": min_days, "dias_desde_ultima": None}
            }

        dias = (data_sol - last_dt).days
        conforme = dias >= min_days and (qtd_solic == 1 or min_days == 0)

        if not conforme:
            msg = f"Intervalo não atendido: {dias}d desde a última; mínimo exigido: {min_days}d."
        else:
            msg = f"Intervalo atendido: {dias}d ≥ {min_days}d."

        return {
            "conforme": conforme,
            "mensagem": msg,
            "evidencias": {
                "ultima_sessao_em": last_dt.isoformat(),
                "dias_desde_ultima": dias,
                "intervalo_minimo_dias": min_days,
                "quantidade_solicitada_mesmo_dia": qtd_solic
            }
        }

    def _rule_repeticao_proibida(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        proc = ctx["procedimento"]
        tipo: str = proc["tipo"]
        data_sol: date = self._parse_date(proc["data_solicitacao"])
        hist: List[Dict[str, Any]] = ctx.get("historico_sessoes", [])

        dias_proib = int(self._rep_proib.get(tipo, 0))
        if dias_proib <= 0:
            return {
                "conforme": True,
                "mensagem": f"Sem janela de repetição proibida para '{tipo}'.",
                "evidencias": {"janela_dias": 0}
            }

        last_dt = self._last_session_date(hist, tipo, data_sol)
        if not last_dt:
            return {
                "conforme": True,
                "mensagem": "Primeira ocorrência; janela respeitada.",
                "evidencias": {"janela_dias": dias_proib, "dias_desde_ultima": None}
            }

        dias = (data_sol - last_dt).days
        conforme = dias >= dias_proib
        msg = (
            f"Janela respeitada: {dias}d ≥ {dias_proib}d."
            if conforme else
            f"Repetição proibida: {dias}d < {dias_proib}d desde a última."
        )
        return {
            "conforme": conforme,
            "mensagem": msg,
            "evidencias": {
                "ultima_ocorrencia_em": last_dt.isoformat(),
                "dias_desde_ultima": dias,
                "janela_repeticao_proibida_dias": dias_proib
            }
        }

    def _rule_mesmo_dia(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        proc = ctx["procedimento"]
        tipo: str = proc["tipo"]
        qtd_solic: int = int(proc.get("quantidade", 1))
        data_sol: date = self._parse_date(proc["data_solicitacao"])
        hist: List[Dict[str, Any]] = ctx.get("historico_sessoes", [])

        if tipo in self._no_same_day:
            ja_realizadas_hoje = self._same_day_count(hist, tipo, data_sol)
            total_no_dia = ja_realizadas_hoje + qtd_solic
            conforme = total_no_dia <= 1
            msg = (
                "Regra de 'não permitir mesmo dia' atendida."
                if conforme else
                f"Violação: {total_no_dia} sessões no mesmo dia para '{tipo}'."
            )
            return {
                "conforme": conforme,
                "mensagem": msg,
                "evidencias": {
                    "tipo": tipo,
                    "ja_realizadas_no_dia": ja_realizadas_hoje,
                    "solicitadas_no_dia": qtd_solic,
                    "total_no_dia": total_no_dia
                }
            }

        return {
            "conforme": True,
            "mensagem": "Sem restrição de mesmo dia para este tipo.",
            "evidencias": {}
        }

    def validar(self, contexto: Dict[str, Any]) -> Dict[str, Any]:
        resultados = {
            "frequencia_maxima": self._rule_frequencia_maxima(contexto),
            "intervalo_minimo": self._rule_intervalo_minimo(contexto),
            "repeticao_proibida": self._rule_repeticao_proibida(contexto),
            "mesmo_dia": self._rule_mesmo_dia(contexto)
        }
        conforme_geral = all(bloco["conforme"] for bloco in resultados.values())
        return {
            "conforme": conforme_geral,
            "regras": resultados
        }
