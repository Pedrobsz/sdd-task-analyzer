# Contrato SDD - TaskAnalyzer | Versão 1.0 alinhada à Fase 1

**Rastreabilidade:** Entrega Inicial do Bootcamp III, versão 1.0 de 13/09/2026, §§1-4; requisitos complementares da Fase 2; automação, Docker e governança da Fase 3.

## Objetivo

Analisar um conjunto de tarefas, calcular médias de conclusão por prioridade e geral, verificar atrasos e expor métricas por prioridade com comportamento determinístico.

## Interface principal

`analyze_tasks(tarefas: Sequence[Mapping[str, Any]]) -> ResultadoFase1`

Cada tarefa possui:

| Campo | Tipo | Obrigatório | Validação |
|---|---|---|---|
| `id_tarefa` | int | Sim | Inteiro >= 0 e único na lista; `bool` não é aceito |
| `data_criacao` | datetime UTC | Sim | ISO 8601 com `Z` ou `+00:00` no JSON |
| `data_inicio` | datetime UTC | Sim | Não anterior a `data_criacao` |
| `data_conclusao` | datetime UTC ou null | Não | Exigida para status `concluída`; proibida para os demais |
| `prazo` | datetime UTC | Sim | Instante limite com data e hora |
| `prioridade` | string enum | Sim | `baixa`, `média`, `alta` (com acento) |
| `status` | string enum | Sim | `concluída`, `pendente`, `cancelada` (com acento) |

O módulo aceita objetos `datetime` timezone-aware em UTC em chamadas Python e strings ISO 8601 UTC em arquivos JSON. Não altera os registros recebidos.

## Retorno da interface original

```json
{
  "quantidade_tarefas": 5,
  "tempo_medio_conclusao_min": 80.0,
  "taxa_atraso_percentual": 33.33,
  "indicadores_por_prioridade": {
    "baixa": {"quantidade_tarefas": 1, "tempo_medio_conclusao_min": 0.0, "taxa_atraso_percentual": 0.0},
    "média": {"quantidade_tarefas": 2, "tempo_medio_conclusao_min": 120.0, "taxa_atraso_percentual": 100.0},
    "alta": {"quantidade_tarefas": 2, "tempo_medio_conclusao_min": 60.0, "taxa_atraso_percentual": 0.0}
  }
}
```

### Fórmulas adotadas

- `quantidade_tarefas`: quantidade de registros válidos, inclusive pendentes e canceladas.
- `tempo_medio_conclusao_min`: soma dos minutos `(data_conclusao - data_inicio)` das concluídas, dividida pela quantidade de concluídas.
- `taxa_atraso_percentual`: `100 x concluídas_com(data_conclusao > prazo) / concluídas`.
- Para prioridades, aplicar as mesmas fórmulas apenas às tarefas daquela prioridade.
- Sem concluídas, as médias e a taxa são `0.0` (não ocorre divisão por zero).
- Arredondar a duas casas decimais. Prazo exato (`data_conclusao == prazo`) não está atrasado.

## Contrato suplementar da Fase 2

`resumo_fase2(tarefas)` retorna separadamente:

- `total_tarefas`, `total_concluidas`, `total_pendentes`, `total_canceladas`;
- `tempo_medio_conclusao_horas` e `tempo_medio_conclusao_horas_por_prioridade`;
- `taxa_atraso_percentual` com a mesma regra da Fase 1.

Essa função adapta a unidade da média para horas e não altera as quatro chaves da `analyze_tasks`.

## Casos de aceite rastreáveis

**Cenário 1 (sucesso):** cinco tarefas demonstrativas, três concluídas, uma pendente e uma cancelada. Durações em minutos: 90, 120, 30. Média geral = 80 min; uma das três concluídas atrasada = 33,33%. Alta = 60 min e 0%; média = 120 min e 100%; baixa = 0.0 e 0%.

**Cenário 2 (erro):** `data_conclusao` anterior a `data_inicio` ou a `data_criacao` gera `TaskValidationError` com campo identificado. A Fase 1 também descreve ignorar dados inconsistentes; como seu próprio cenário 2 e a Fase 2 exigem erro tratado, **prevalece a exceção explícita**, sem descartar dados silenciosamente.

**Casos de borda:** lista vazia, apenas pendentes/canceladas, conclusão exatamente no prazo e identificadores duplicados.

## Restrições técnicas

Python 3.11+, type hints, SRP, `logging`, sem persistência, sem bibliotecas externas de produção, testes em `pytest`. Docker e GitHub Actions automatizam a execução da mesma suíte.

## Ambiguidades resolvidas expressamente

A Fase 1 não explicita o denominador da taxa nem a contagem de tarefas consideradas por status. As interpretações escolhidas constam em `CONTEXT_RULES.md`. Não são apresentadas como fórmulas textualmente fornecidas no documento original.
