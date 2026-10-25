# TaskAnalyzer | Bootcamp III - Entrega Final

Analisador de tarefas em **Python 3.11+** conforme a especificação SDD da Fase 1 (versão 1.0, 13/09/2026), com testes automatizados, GitHub Actions, Docker e governança de IA.

**CI:** conferir o resultado efetivo na aba **Actions** deste repositório após a publicação.

## Contrato funcional

- Entradas: `id_tarefa` inteiro (0+), `data_criacao`, `data_inicio`, `prazo` (todos em UTC), `data_conclusao` opcional, `prioridade` (`baixa`, `média`, `alta`) e `status` (`concluída`, `pendente`, `cancelada`).
- `analyze_tasks` calcula `quantidade_tarefas`, `tempo_medio_conclusao_min`, `taxa_atraso_percentual` e `indicadores_por_prioridade`.
- Duração = conclusão menos **início**, em minutos. Só tarefas concluídas podem estar atrasadas; prazo igual à conclusão não é atraso.
- Dados inválidos geram `TaskValidationError`; listas sem concluídas retornam médias e taxa `0.0`.
- `resumo_fase2` fornece, em interface separada, contagens por status e médias em horas exigidas na Fase 2.

A política para datas inconsistentes e o denominador da taxa estão documentados em [specs/task_analyzer_spec.md](specs/task_analyzer_spec.md) e [CONTEXT_RULES.md](CONTEXT_RULES.md).

## Instalação e testes

No terminal, a partir da raiz do repositório:

```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_harness.py -v
```

**Validação local:** 65 testes aprovados no ambiente de desenvolvimento (25/10/2026). Testes aprovados não implicam cobertura de código de 100%.

## Uso da aplicação

```bash
python -m src.task_analyzer examples/tasks_valid.json
python -m src.task_analyzer examples/tasks_valid.json --fase2
python -m src.task_analyzer examples/tasks_invalid.json
```

O primeiro comando produz **5 tarefas, média de 80 minutos e taxa de atraso de 33,33%**. O terceiro demonstra uma inconsistência intencional e termina com código de saída 2.

## Docker

Com Docker Desktop em execução:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from tests
```

O resultado esperado é a aprovação da suíte de testes no contêiner. Esta execução deve ser comprovada no ambiente de publicação.

## GitHub Actions

O workflow [.github/workflows/ci.yml](.github/workflows/ci.yml) executa a suíte em Python 3.11 e em Docker Compose, em jobs separados. Gatilhos: `push` na `main`, `pull_request` para `main` e execução manual. Evidência de sucesso exige execução real visível na aba Actions.

## Organização

```text
sdd-task-analyzer/
├── .github/workflows/ci.yml
├── CONTEXT_RULES.md
├── Dockerfile
├── docker-compose.yml
├── README.md
├── requirements.txt
├── pytest.ini
├── specs/
│   ├── task_analyzer_spec.md
│   ├── requirements.yaml
│   └── system_design_document.pdf
├── src/
│   ├── __init__.py
│   └── task_analyzer.py
├── tests/
│   └── test_harness.py
├── examples/
│   ├── tasks_valid.json
│   └── tasks_invalid.json
└── docs/
    └── relatorio_governanca_etica.pdf
```

## Governança e homologação

O desenvolvimento foi auxiliado por IA e verificado com testes automatizados. As regras de contexto exigem revisão humana, restrição de dependências, logs sem identificadores, ausência de persistência e aderência ao SDD. O [relatório técnico](docs/relatorio_governanca_etica.pdf) apresenta riscos, decisões de projeto e evidências disponíveis, distinguindo validação local de CI/Docker ainda não comprovados.

**Entrega AVA:** repositório público com workflow verificado, relatório técnico PDF e link de apresentação técnica no YouTube (aproximadamente 5 minutos).


## Homologação Técnica - Fase 3

A aplicação TaskAnalyzer foi submetida a testes automatizados e validações de infraestrutura.

### Testes Locais
- 65 testes executados com Pytest.
- 65 testes aprovados.
- Resultado: `65 passed`.

### Integração Contínua (CI/CD)
- Workflow configurado no GitHub Actions.
- Execução automática realizada após o push na branch `main`.
- Resultado do workflow: aprovado.

### Containerização com Docker
- Imagem construída utilizando Docker.
- Testes executados em ambiente containerizado.
- Resultado: `65 passed in 0.85s`.
- Código de saída: `0`.

### Homologação
As verificações realizadas confirmaram a aprovação dos testes automatizados nos ambientes local e Docker, além da execução bem-sucedida do workflow de integração contínua.

Data da validação: 25/10/2026.
