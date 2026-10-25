# CONTEXT_RULES | TaskAnalyzer

**Base:** especificação SDD da Fase 1, versão 1.0 (13/09/2026). Este documento orienta geração, revisão e homologação de código assistido por IA.

## Contrato que não pode ser alterado silenciosamente

- `analyze_tasks(tarefas)` retorna as quatro chaves definidas na Fase 1: `quantidade_tarefas`, `tempo_medio_conclusao_min`, `taxa_atraso_percentual`, `indicadores_por_prioridade`.
- Dados exigidos: `id_tarefa` (inteiro a partir de zero), `data_criacao`, `data_inicio`, `prazo`, `prioridade`, `status`; `data_conclusao` opcional conforme o estado.
- Prioridades válidas: `baixa`, `média`, `alta`. Status válidos: `concluída`, `pendente`, `cancelada`.
- Datas sempre em UTC; arquivos JSON utilizam ISO 8601 com `Z` ou `+00:00`.
- Duração da execução: `data_conclusao - data_inicio`, em minutos; *não* subtrair `data_criacao`.
- Atraso: somente concluídas para as quais `data_conclusao > prazo`. Prazo igual à conclusão não constitui atraso.
- Divisões sem tarefas concluídas resultam em média e percentual `0.0`. Arredondamento em duas casas decimais.

## Arquitetura e segurança

- Python 3.11 ou superior; type hints em todas as funções e métodos; PEP 8 e responsabilidade única.
- Tratamento de erros por `TaskValidationError`; não usar `except:` genérico nem ocultar erros.
- Logs estruturados via `logging` sem identificadores de tarefas ou dados pessoais.
- Não persistir dados em arquivos ou bancos de dados; o JSON demonstrativo é somente entrada de leitura.
- Nenhuma biblioteca externa em produção. `pytest` é a única dependência de desenvolvimento autorizada.
- Separação entre validação, agregação, apresentação e testes.
- Não introduzir recursos, campos obrigatórios ou parâmetros públicos sem respaldo documental; qualquer adaptação deve ser isolada e explicada.
- Alterações de comportamento precisam ser cobertas pelo Test Harness e submetidas à revisão humana.

## Divergências entre etapas - decisões documentadas

1. A Fase 1 (§1.3.3) menciona ignorar tarefas com datas inconsistentes, enquanto seu Cenário 2 e a Fase 2 pedem exceção específica. Decisão: **rejeitar a entrada inteira com `TaskValidationError`**, expondo qual tarefa e campo estão inválidos. Evita estatísticas parciais sem aviso.
2. A Fase 2 acrescenta totais por status e médias em horas, mas a Fase 1 proíbe alterar suas saídas. Decisão: manter `analyze_tasks` estritamente no contrato original e publicar `resumo_fase2(tarefas)` como adaptador independente.
3. A Fase 1 não define o denominador da taxa de atraso. Decisão: *concluídas atrasadas / concluídas x 100*, pois a definição se refere a tarefas concluídas após o prazo. Zeros são tratados.
4. `quantidade_tarefas` considera todos os registros válidos, inclusive pendentes e cancelados. Duração e atraso consideram apenas as concluídas.

## Homologação humana

- Revisar código contra `specs/task_analyzer_spec.md` e o documento inicial original.
- Executar cenários de sucesso, de exceção e de borda; conferir indicadores manualmente.
- Confirmar workflow GitHub Actions e execução Docker sem confundir configuração com evidência real.
- Inspecionar as alterações de Pull Requests antes da integração na `main`.
