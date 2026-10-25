"""Test Harness derivado dos cenários de aceite da Fase 1 e da Fase 2."""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.task_analyzer import TaskValidationError, analyze_tasks, resumo_fase2

RAIZ = Path(__file__).resolve().parents[1]


def _exemplo() -> list[dict[str, Any]]:
    return json.loads((RAIZ / "examples/tasks_valid.json").read_text(encoding="utf-8"))


def _tarefa() -> dict[str, Any]:
    return deepcopy(_exemplo()[0])


def test_cenario_1_metricas_gerais_conforme_sdd() -> None:
    resultado = analyze_tasks(_exemplo())
    assert resultado == {
        "quantidade_tarefas": 5,
        "tempo_medio_conclusao_min": 80.0,
        "taxa_atraso_percentual": 33.33,
        "indicadores_por_prioridade": {
            "baixa": {"quantidade_tarefas": 1, "tempo_medio_conclusao_min": 0.0, "taxa_atraso_percentual": 0.0},
            "média": {"quantidade_tarefas": 2, "tempo_medio_conclusao_min": 120.0, "taxa_atraso_percentual": 100.0},
            "alta": {"quantidade_tarefas": 2, "tempo_medio_conclusao_min": 60.0, "taxa_atraso_percentual": 0.0},
        },
    }


def test_fase2_resumo_em_horas_sem_mudar_contrato_original() -> None:
    assert resumo_fase2(_exemplo()) == {
        "total_tarefas": 5,
        "total_concluidas": 3,
        "total_pendentes": 1,
        "total_canceladas": 1,
        "tempo_medio_conclusao_horas": 1.33,
        "tempo_medio_conclusao_horas_por_prioridade": {"baixa": 0.0, "média": 2.0, "alta": 1.0},
        "taxa_atraso_percentual": 33.33,
    }


def test_cenario_2_conclusao_antes_inicio_falha() -> None:
    invalida = json.loads((RAIZ / "examples/tasks_invalid.json").read_text(encoding="utf-8"))
    with pytest.raises(TaskValidationError, match="data_conclusao.*data_inicio"):
        analyze_tasks(invalida)


def test_fase2_conclusao_antes_criacao_falha() -> None:
    tarefa = _tarefa()
    tarefa["data_conclusao"] = "2026-08-31T23:00:00Z"
    with pytest.raises(TaskValidationError, match="data_conclusao.*data_criacao"):
        analyze_tasks([tarefa])


def test_casos_de_borda_lista_vazia() -> None:
    assert analyze_tasks([]) == {
        "quantidade_tarefas": 0,
        "tempo_medio_conclusao_min": 0.0,
        "taxa_atraso_percentual": 0.0,
        "indicadores_por_prioridade": {
            chave: {"quantidade_tarefas": 0, "tempo_medio_conclusao_min": 0.0, "taxa_atraso_percentual": 0.0}
            for chave in ("baixa", "média", "alta")
        },
    }
    assert resumo_fase2([])["tempo_medio_conclusao_horas"] == 0.0


@pytest.mark.parametrize("status", ["pendente", "cancelada"])
def test_casos_de_borda_sem_concluidas(status: str) -> None:
    tarefa = _tarefa()
    tarefa["status"] = status
    tarefa["data_conclusao"] = None
    geral = analyze_tasks([tarefa])
    assert geral["tempo_medio_conclusao_min"] == 0.0
    assert geral["taxa_atraso_percentual"] == 0.0


def test_fase1_duracao_e_inicio_nao_criacao() -> None:
    tarefa = _tarefa()
    tarefa["data_criacao"] = "2026-08-30T08:00:00Z"
    assert analyze_tasks([tarefa])["tempo_medio_conclusao_min"] == 90.0


def test_igualdade_com_prazo_nao_atrasada() -> None:
    tarefa = _tarefa()
    tarefa["prazo"] = tarefa["data_conclusao"]
    assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 0.0


def test_1_segundo_atraso_conta() -> None:
    tarefa = _tarefa()
    tarefa["prazo"] = "2026-09-01T10:29:59Z"
    assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 100.0


def test_pendente_venceu_prazo_nao_conta_como_atrasada() -> None:
    tarefa = _tarefa()
    tarefa["status"] = "pendente"
    tarefa["data_conclusao"] = None
    tarefa["prazo"] = "2020-01-01T00:00:00Z"
    assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 0.0


def test_cancelada_venceu_prazo_nao_conta_como_atrasada() -> None:
    tarefa = _tarefa()
    tarefa["status"] = "cancelada"
    tarefa["data_conclusao"] = None
    tarefa["prazo"] = "2020-01-01T00:00:00Z"
    assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 0.0


def test_inicio_igual_conclusao_valido() -> None:
    tarefa = _tarefa()
    tarefa["data_conclusao"] = tarefa["data_inicio"]
    assert analyze_tasks([tarefa])["tempo_medio_conclusao_min"] == 0.0


def test_criacao_igual_inicio_valido() -> None:
    tarefa = _tarefa()
    tarefa["data_inicio"] = tarefa["data_criacao"]
    assert analyze_tasks([tarefa])["tempo_medio_conclusao_min"] == 150.0


def test_id_zero_e_valido() -> None:
    assert analyze_tasks([_tarefa()])["quantidade_tarefas"] == 1


def test_sem_mutacao_dos_registros() -> None:
    tarefas = _exemplo()
    copia = deepcopy(tarefas)
    analyze_tasks(tarefas)
    assert tarefas == copia


def test_aceita_datetime_python_utc() -> None:
    tarefa = _tarefa()
    for chave in ("data_criacao", "data_inicio", "data_conclusao", "prazo"):
        tarefa[chave] = datetime.fromisoformat(tarefa[chave].replace("Z", "+00:00"))
    assert analyze_tasks([tarefa])["tempo_medio_conclusao_min"] == 90.0


def test_aceita_iso_offset_utc_explicito() -> None:
    tarefa = _tarefa()
    tarefa["prazo"] = "2026-09-01T11:00:00+00:00"
    assert analyze_tasks([tarefa])["taxa_atraso_percentual"] == 0.0


def test_saida_somente_campos_contratados() -> None:
    assert set(analyze_tasks(_exemplo())) == {
        "quantidade_tarefas", "tempo_medio_conclusao_min",
        "taxa_atraso_percentual", "indicadores_por_prioridade",
    }


def test_quantidade_por_prioridade_soma_total() -> None:
    saida = analyze_tasks(_exemplo())
    assert sum(x["quantidade_tarefas"] for x in saida["indicadores_por_prioridade"].values()) == saida["quantidade_tarefas"]


def test_fase2_contadores_nao_confundem_pendentes_canceladas() -> None:
    saida = resumo_fase2(_exemplo())
    assert saida["total_tarefas"] == (saida["total_concluidas"] + saida["total_pendentes"] + saida["total_canceladas"])


def test_logs_estruturados_sem_identificadores(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("INFO", logger="src.task_analyzer"):
        analyze_tasks(_exemplo())
    dados = json.loads(caplog.records[-1].message)
    assert dados == {"evento": "analise_concluida", "tarefas": 5, "concluidas": 3, "pendentes": 1, "canceladas": 1}
    assert "id_tarefa" not in caplog.records[-1].message


def test_cli_exemplo_valido_sucesso() -> None:
    processo = subprocess.run(
        [sys.executable, "-m", "src.task_analyzer", "examples/tasks_valid.json"],
        cwd=RAIZ, capture_output=True, text=True, check=False,
    )
    assert processo.returncode == 0
    assert json.loads(processo.stdout)["tempo_medio_conclusao_min"] == 80.0


def test_cli_exemplo_invalido_erro_tratado() -> None:
    processo = subprocess.run(
        [sys.executable, "-m", "src.task_analyzer", "examples/tasks_invalid.json"],
        cwd=RAIZ, capture_output=True, text=True, check=False,
    )
    assert processo.returncode == 2
    assert "Erro de validação" in processo.stderr


def test_cli_resumo_fase2() -> None:
    processo = subprocess.run(
        [sys.executable, "-m", "src.task_analyzer", "examples/tasks_valid.json", "--fase2"],
        cwd=RAIZ, capture_output=True, text=True, check=False,
    )
    assert processo.returncode == 0
    assert json.loads(processo.stdout)["total_concluidas"] == 3


@pytest.mark.parametrize("alteracao,mensagem", [
    ({"id_tarefa": -1}, "id_tarefa"),
    ({"id_tarefa": True}, "id_tarefa"),
    ({"id_tarefa": "1"}, "id_tarefa"),
    ({"id_tarefa": 1.0}, "id_tarefa"),
    ({"prioridade": "media"}, "prioridade"),
    ({"prioridade": "urgente"}, "prioridade"),
    ({"prioridade": None}, "prioridade"),
    ({"status": "concluida"}, "status"),
    ({"status": "aberta"}, "status"),
    ({"data_criacao": "2026-09-01"}, "data_criacao"),
    ({"data_criacao": "2026-09-01T08:00:00"}, "data_criacao"),
    ({"data_criacao": "2026-09-01T08:00:00+03:00"}, "data_criacao"),
    ({"data_inicio": "2026-08-31T09:00:00Z"}, "data_inicio"),
    ({"data_inicio": "data inválida"}, "data_inicio"),
    ({"data_conclusao": "2026-09-01T07:00:00Z"}, "data_conclusao"),
    ({"data_conclusao": "2026-09-01T08:30:00Z"}, "data_conclusao"),
    ({"data_conclusao": "2026-09-01T10:30:00+01:00"}, "data_conclusao"),
    ({"prazo": None}, "prazo"),
    ({"prazo": "2026-02-30T10:00:00Z"}, "prazo"),
    ({"status": "pendente"}, "data_conclusao"),
    ({"status": "cancelada"}, "data_conclusao"),
    ({"data_conclusao": None}, "data_conclusao"),
    ({"titulo": "não autorizado"}, "campos não previstos"),
])
def test_campos_invalidos_geram_excecao(alteracao: dict[str, Any], mensagem: str) -> None:
    tarefa = _tarefa()
    tarefa.update(alteracao)
    with pytest.raises(TaskValidationError, match=mensagem):
        analyze_tasks([tarefa])


@pytest.mark.parametrize("campo", [
    "id_tarefa", "data_criacao", "data_inicio", "prazo", "prioridade", "status",
])
def test_campo_obrigatorio_ausente(campo: str) -> None:
    tarefa = _tarefa()
    tarefa.pop(campo)
    with pytest.raises(TaskValidationError, match="campos obrigatórios ausentes"):
        analyze_tasks([tarefa])


@pytest.mark.parametrize("entrada", [None, 10, {}, "texto", [None], [{"invalido": True}]])
def test_estrutura_de_entrada_invalida(entrada: Any) -> None:
    with pytest.raises(TaskValidationError):
        analyze_tasks(entrada)


def test_id_duplicado_falha() -> None:
    with pytest.raises(TaskValidationError, match="duplicado"):
        analyze_tasks([_tarefa(), _tarefa()])


def test_nao_ha_persistencia_de_dados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    analyze_tasks(_exemplo())
    assert list(tmp_path.iterdir()) == []


def test_entrada_invalida_falha_antes_de_agregar() -> None:
    tarefas = _exemplo()
    tarefas[-1]["prioridade"] = "urgente"
    with pytest.raises(TaskValidationError, match="Tarefa 5"):
        analyze_tasks(tarefas)


def test_arredondamento_geral_duas_casas() -> None:
    tarefas = _exemplo()
    assert analyze_tasks(tarefas)["taxa_atraso_percentual"] == 33.33
    assert resumo_fase2(tarefas)["tempo_medio_conclusao_horas"] == 1.33


def test_aceita_tupla() -> None:
    assert analyze_tasks(tuple(_exemplo()))["quantidade_tarefas"] == 5
