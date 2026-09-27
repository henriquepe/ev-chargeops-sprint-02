# Sprint 02 — entendimento e plano

Fonte: atividade FIAP ON 662437, lida em 27/09/2026. Prazo: **13/10/2026 às 23h59**. Equipe exibida: **Grupo 22**, Henrique Pires Espindola, RM 568600. A Sprint 01 usava o nome Grupo 5; preservamos esse documento em `docs/sprint-01/`.

## Demanda e rubrica

O entregável é um TXT com o link do repositório contendo um protótipo funcional, README em português e evidências. A instituição exige compreensão do código e pitch individual de três minutos na etapa presencial para validar as notas. Apoio de IA ao desenvolvimento é permitido. Não basta um documento ou telas estáticas.

| Critério | Peso | Critério de aceite técnico |
|---|---:|---|
| Lógica central alinhada à Sprint 01 | 3 | Registrar sessões, validar medidores, associar morador/unidade e calcular rateio decimal auditável; tratar interrupção, ociosidade, perdas, gratuidade, crédito e ausência de consumo |
| IA estrutural integrada | 3 | Modelo treinado no histórico; sessões atípicas retidas antes da cobrança; revisão humana registrada; previsão mensal com avaliação temporal e comparação com baseline |
| Evidências de funcionamento | 2 | API exercitada, testes reproduzíveis, capturas reais do dashboard e do fluxo de fatura |
| Autoria e compreensão | 1 | Decisões explicadas, guia de código e roteiro de pitch; limites e dados sintéticos identificados |
| README e organização | 1 | Execução reproduzível, arquitetura, comandos, desvios, evidências e histórico de commits descritivos |

## Plano de execução

1. **Domínio e persistência:** FastAPI, SQLAlchemy/Alembic, PostgreSQL no Compose e SQLite para execução rápida. Contrato normalizado independente da GoodWe. Login de gestor/morador, isolamento por unidade, ingestão idempotente, auditoria e rateio com Decimal. Validar cálculos e exceções por testes de integração.
2. **Inteligência aplicada:** detector estatístico robusto treinado em sessões históricas (mediana e MAD), regressão de consumo diário, holdout temporal, baseline semanal e previsão mensal. O detector altera a elegibilidade da cobrança. Validar anomalia, insuficiência de dados e ausência de dados futuros.
3. **Experiência funcional:** React/Vite, dashboard, filtros, simulador de cenários, revisão, demonstrativo, fechamento mensal e CSV; portal do morador protegido pela API. Testar o fluxo com servidor e navegador reais.
4. **Entrega e explicação:** instruções, justificativas de desvios, modelo de dados, evidências, checklist da rubrica, guia de estudo e pitch de três minutos. Conferir clone/instalação, build e testes.

## Decisões de escopo

- A fonte de dados será sintética e explicitamente identificada. Nenhuma credencial SEMS ou amostra real foi fornecida. Não inventar endpoints, leitura Modbus ou homologação GoodWe.
- Tarifas e taxas são hipóteses didáticas configuradas por mês, não preços reais da distribuidora. Nenhuma cobrança financeira é executada.
- A sessão pertence ao mês do início em America/Sao_Paulo, inclusive se terminar no mês seguinte. Essa simplificação será explicada no demonstrativo.
- O fechamento é persistido e imutável. Sessões retidas devem ser revisadas antes dele; tentativas de importar dados para um mês fechado são rejeitadas.
- Sessões sem identificação ou medição inconsistente não podem ser liberadas; são excluídas com justificativa. Dados corrigidos entram com novo identificador, preservando o original.
- Créditos são lançados antes do fechamento, com motivo e chave idempotente. Não há edição de uma fatura já fechada no MVP.
- Sem chatbot, clustering, gateways de pagamento ou controle elétrico físico nesta sprint. Foram opções futuras, não prioridades da Sprint 01.
- Dados pessoais das contas de demonstração são fictícios.

## Estado

Entendimento concluído; implementação e validação em andamento. Consulte `docs/evidencias/VALIDACAO.md` para o resultado efetivamente obtido.
