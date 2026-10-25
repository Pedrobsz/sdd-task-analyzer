"""Análise de tarefas conforme o contrato SDD da Fase 1 do Bootcamp III.

Entradas Python aceitam datetime com UTC; arquivos JSON usam ISO 8601 com Z.
A saída de analyze_tasks preserva os quatro campos definidos na Fase 1.
resumo_fase2 implementa as métricas complementares pedidas na Fase 2.
"""

from __future__ import annotations

import argparse
import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal, TypedDict

Prioridade = Literal["baixa", "média", "alta"]
Status = Literal["concluída", "pendente", "cancelada"]
PRIORIDADES: tuple[Prioridade, ...] = ("baixa", "média", "alta")
STATUS_VALIDOS: tuple[Status, ...] = ("concluída", "pendente", "cancelada")
CAMPOS_OBRIGATORIOS = frozenset(
    {"id_tarefa", "data_criacao", "data_inicio", "prazo", "prioridade", "status"}
)
CAMPOS_PERMITIDOS = CAMPOS_OBRIGATORIOS | {"data_conclusao"}
LOGGER = logging.getLogger(__name__)


class TaskValidationError(ValueError):
    """Informa a violação do contrato, com indicação da tarefa e do campo."""


class Indicador(TypedDict):
    quantidade_tarefas: int
    tempo_medio_conclusao_min: float
    taxa_atraso_percentual: float


class ResultadoFase1(Indicador):
    indicadores_por_prioridade: dict[str, Indicador]


class ResumoFase2(TypedDict):
    total_tarefas: int
    total_concluidas: int
    total_pendentes: int
    total_canceladas: int
    tempo_medio_conclusao_horas: float
    tempo_medio_conclusao_horas_por_prioridade: dict[str, float]
    taxa_atraso_percentual: float


@dataclass(frozen=True, slots=True)
class Tarefa:
    id_tarefa: int
    data_criacao: datetime
    data_inicio: datetime
    data_conclusao: datetime | None
    prazo: datetime
    prioridade: Prioridade
    status: Status


@dataclass(frozen=True, slots=True)
class Agregado:
    total: int
    concluidas: int
    pendentes: int
    canceladas: int
    atrasadas: int
    duracao_minutos: float


def _erro(indice: int, descricao: str) -> TaskValidationError:
    return TaskValidationError(f"Tarefa {indice}: {descricao}.")


def _data_utc(valor: Any, campo: str, indice: int) -> datetime:
    """Converte ISO 8601 UTC ou datetime UTC, rejeitando datas sem fuso."""
    if isinstance(valor, datetime):
        data = valor
    elif isinstance(valor, str):
        if "T" not in valor:
            raise _erro(indice, f"'{campo}' exige data e hora ISO 8601 em UTC")
        try:
            data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError as exc:
            raise _erro(indice, f"'{campo}' possui data/hora inválida") from exc
    else:
        raise _erro(indice, f"'{campo}' exige datetime UTC ou string ISO 8601")
    if data.tzinfo is None or data.utcoffset() is None:
        raise _erro(indice, f"'{campo}' deve informar fuso UTC (Z ou +00:00)")
    if data.utcoffset() != timedelta(0):
        raise _erro(indice, f"'{campo}' deve estar em UTC (offset +00:00)")
    return data.astimezone(timezone.utc)


def _validar_tarefa(item: Any, indice: int) -> Tarefa:
    if not isinstance(item, Mapping):
        raise _erro(indice, "registro deve ser objeto com campos nomeados")
    if any(not isinstance(chave, str) for chave in item):
        raise _erro(indice, "nomes de campos devem ser texto")
    faltantes = CAMPOS_OBRIGATORIOS - item.keys()
    extras = item.keys() - CAMPOS_PERMITIDOS
    if faltantes:
        raise _erro(indice, f"campos obrigatórios ausentes: {', '.join(sorted(faltantes))}")
    if extras:
        raise _erro(indice, f"campos não previstos no contrato: {', '.join(sorted(extras))}")

    identificador = item["id_tarefa"]
    if type(identificador) is not int or identificador < 0:
        raise _erro(indice, "'id_tarefa' deve ser inteiro maior ou igual a zero")

    prioridade = item["prioridade"]
    if not isinstance(prioridade, str) or prioridade not in PRIORIDADES:
        raise _erro(indice, "'prioridade' deve ser baixa, média ou alta")
    status = item["status"]
    if not isinstance(status, str) or status not in STATUS_VALIDOS:
        raise _erro(indice, "'status' deve ser concluída, pendente ou cancelada")

    criacao = _data_utc(item["data_criacao"], "data_criacao", indice)
    inicio = _data_utc(item["data_inicio"], "data_inicio", indice)
    prazo = _data_utc(item["prazo"], "prazo", indice)
    conclusao_bruta = item.get("data_conclusao")
    conclusao = (
        None if conclusao_bruta is None
        else _data_utc(conclusao_bruta, "data_conclusao", indice)
    )

    if inicio < criacao:
        raise _erro(indice, "'data_inicio' não pode anteceder 'data_criacao'")
    if conclusao is not None and conclusao < criacao:
        raise _erro(indice, "'data_conclusao' não pode anteceder 'data_criacao'")
    if conclusao is not None and conclusao < inicio:
        raise _erro(indice, "'data_conclusao' não pode anteceder 'data_inicio'")
    if status == "concluída" and conclusao is None:
        raise _erro(indice, "status 'concluída' exige 'data_conclusao'")
    if status != "concluída" and conclusao is not None:
        raise _erro(indice, "apenas tarefas concluídas podem informar 'data_conclusao'")

    return Tarefa(
        id_tarefa=identificador,
        data_criacao=criacao,
        data_inicio=inicio,
        data_conclusao=conclusao,
        prazo=prazo,
        prioridade=prioridade,
        status=status,
    )


def _validar_lista(tarefas: Sequence[Mapping[str, Any]]) -> list[Tarefa]:
    if not isinstance(tarefas, (list, tuple)):
        raise TaskValidationError("'tarefas' deve ser lista ou tupla de registros.")
    registros: list[Tarefa] = []
    identificadores: set[int] = set()
    for indice, item in enumerate(tarefas, start=1):
        validada = _validar_tarefa(item, indice)
        if validada.id_tarefa in identificadores:
            raise _erro(indice, f"'id_tarefa' duplicado: {validada.id_tarefa}")
        identificadores.add(validada.id_tarefa)
        registros.append(validada)
    return registros


def _agregar(tarefas: Sequence[Tarefa]) -> Agregado:
    concluidas = [tarefa for tarefa in tarefas if tarefa.status == "concluída"]
    atrasadas = sum(
        1 for tarefa in concluidas
        if tarefa.data_conclusao is not None and tarefa.data_conclusao > tarefa.prazo
    )
    duracao = sum(
        (tarefa.data_conclusao - tarefa.data_inicio).total_seconds() / 60
        for tarefa in concluidas if tarefa.data_conclusao is not None
    )
    return Agregado(
        total=len(tarefas),
        concluidas=len(concluidas),
        pendentes=sum(1 for tarefa in tarefas if tarefa.status == "pendente"),
        canceladas=sum(1 for tarefa in tarefas if tarefa.status == "cancelada"),
        atrasadas=atrasadas,
        duracao_minutos=duracao,
    )


def _indicador(agregado: Agregado) -> Indicador:
    """Taxa de atraso = concluídas atrasadas / concluídas; sem divisão por zero."""
    media = agregado.duracao_minutos / agregado.concluidas if agregado.concluidas else 0.0
    taxa = 100 * agregado.atrasadas / agregado.concluidas if agregado.concluidas else 0.0
    return {
        "quantidade_tarefas": agregado.total,
        "tempo_medio_conclusao_min": round(media, 2),
        "taxa_atraso_percentual": round(taxa, 2),
    }


def _registrar_resumo(agregado: Agregado) -> None:
    if LOGGER.isEnabledFor(logging.INFO):
        LOGGER.info(json.dumps({
            "evento": "analise_concluida",
            "tarefas": agregado.total,
            "concluidas": agregado.concluidas,
            "pendentes": agregado.pendentes,
            "canceladas": agregado.canceladas,
        }, ensure_ascii=False))


def analyze_tasks(tarefas: Sequence[Mapping[str, Any]]) -> ResultadoFase1:
    """Retorna EXATAMENTE os 4 campos definidos no contrato SDD original.

    Métricas gerais e por prioridade incluem todas as tarefas na quantidade,
    mas a média e o atraso têm como denominador apenas as concluídas.
    Dados inconsistentes geram TaskValidationError; a escolha resolve a
    divergência documentada entre Fase 1 (§1.3.3) e Cenário 2/Fase 2.
    """
    registros = _validar_lista(tarefas)
    geral = _agregar(registros)
    por_prioridade = {
        prioridade: _indicador(_agregar([
            tarefa for tarefa in registros if tarefa.prioridade == prioridade
        ]))
        for prioridade in PRIORIDADES
    }
    _registrar_resumo(geral)
    return {**_indicador(geral), "indicadores_por_prioridade": por_prioridade}


def resumo_fase2(tarefas: Sequence[Mapping[str, Any]]) -> ResumoFase2:
    """Adaptador explícito: métricas adicionais da Fase 2 sem alterar a Fase 1."""
    registros = _validar_lista(tarefas)
    geral = _agregar(registros)
    prioridades = {
        prioridade: _agregar([t for t in registros if t.prioridade == prioridade])
        for prioridade in PRIORIDADES
    }
    _registrar_resumo(geral)
    return {
        "total_tarefas": geral.total,
        "total_concluidas": geral.concluidas,
        "total_pendentes": geral.pendentes,
        "total_canceladas": geral.canceladas,
        "tempo_medio_conclusao_horas": round(
            geral.duracao_minutos / geral.concluidas / 60, 2
        ) if geral.concluidas else 0.0,
        "tempo_medio_conclusao_horas_por_prioridade": {
            prioridade: round(ag.duracao_minutos / ag.concluidas / 60, 2)
            if ag.concluidas else 0.0
            for prioridade, ag in prioridades.items()
        },
        "taxa_atraso_percentual": _indicador(geral)["taxa_atraso_percentual"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analisador de produtividade TaskAnalyzer")
    parser.add_argument("arquivo", type=Path, help="Lista JSON de tarefas")
    parser.add_argument("--fase2", action="store_true", help="Exibe o resumo complementar da Fase 2")
    parser.add_argument("--verbose", action="store_true", help="Exibe log estruturado (sem dados pessoais)")
    args = parser.parse_args(argv)
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        conteudo: Any = json.loads(args.arquivo.read_text(encoding="utf-8"))
        resultado = resumo_fase2(conteudo) if args.fase2 else analyze_tasks(conteudo)
    except (TaskValidationError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Erro de validação: {exc}\n")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
