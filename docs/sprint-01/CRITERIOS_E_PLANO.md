# Criterios de aceite e plano de execucao

## Entendimento dos criterios de aceite

O entregavel formal da Sprint 01 e um arquivo `.txt` contendo o link do repositorio do grupo. Esse repositorio deve conter um `README.md` bem elaborado, em portugues claro, com o documento central de pesquisa e proposta da equipe.

Para cumprir o enunciado e maximizar a rubrica, o repositorio deve conter:

- Nome da equipe e RMs dos integrantes.
- Descricao clara do problema e do contexto GoodWe/FIAP.
- Resultado das tres frentes de pesquisa.
- Ao menos uma opcao de aprofundamento por frente.
- Diagrama de arquitetura como imagem referenciada no README.
- Modelo de rateio com variaveis, criterios e excecoes.
- Papel da IA como parte estrutural da solucao.
- Plano da Sprint 02 com ordem de desenvolvimento e tecnologias.
- Fontes consultadas ao final.

## Rubrica traduzida em checklist pratico

| Rubrica | Para atender bem | Evidencia criada |
| --- | --- | --- |
| Problema claro e embasado | Explicar dor de condominios/campus: identificacao, medicao, rateio, transparencia e auditoria | `README.md`, secoes "Resumo" e "Frente 1" |
| Tres frentes documentadas | Cobrir contexto, regulacao/tecnica e arquitetura/IA com analise propria | `README.md`, secoes "Frente 1", "Frente 2" e "Frente 3" |
| Arquitetura e rateio definidos | Mostrar camadas, fluxo de dados, formula de cobranca e excecoes | `docs/arquitetura-ev-chargeops.svg` e secao "Modelo de rateio" |
| IA estrutural | Definir uso real de IA em previsao, anomalia e perfis | Secao "Papel da IA" |
| README organizado e autoral | Texto direto, fontes consultadas, decisoes justificadas | `README.md` completo |

## Plano de execucao da Sprint 01

1. Completar dados da equipe
   - Preencher nome da equipe e RMs no `README.md`.
   - Confirmar se o repositorio sera publico ou privado com acesso ao professor.

2. Revisar fontes
   - Conferir links citados no README.
   - Adicionar qualquer fonte consultada diretamente pela equipe.
   - Evitar fonte nao verificada ou gerada apenas por IA.

3. Validar escolhas tecnicas
   - Confirmar se o MVP usara FastAPI/PostgreSQL/React.
   - Confirmar se havera acesso real ao SEMS+ na Sprint 02.
   - Caso nao haja acesso, manter simulador como fonte primaria do prototipo.

4. Ajustar diagrama
   - Se a equipe preferir, converter o SVG para PNG.
   - Manter a imagem em `docs/` e a referencia no README.

5. Subir repositorio
   - Criar repo `ev-chargeops-sprint-01`.
   - Subir `README.md`, `docs/arquitetura-ev-chargeops.svg`, `docs/arquitetura-ev-chargeops.mmd` e este plano.
   - Atualizar `entrega.txt` com o link real do repo.

6. Revisao final
   - Conferir se todos os itens do checklist aparecem no README.
   - Ler o README como avaliador: problema, pesquisa, decisao e plano precisam estar claros sem depender de explicacao oral.

## Backlog sugerido para Sprint 02

| Ordem | Entrega | Resultado esperado |
| --- | --- | --- |
| 1 | Setup tecnico | Repositorio com backend, frontend, banco e Docker |
| 2 | Schema e migracoes | Tabelas de usuarios, unidades, carregadores, sessoes e faturas |
| 3 | Simulador de sessoes | Dados realistas para demonstrar o fluxo completo |
| 4 | API de sessoes | Criar, listar, validar e auditar sessoes |
| 5 | Motor de rateio | Calculo mensal por usuario/unidade |
| 6 | Dashboard gestor | Visao de consumo, usuarios, faturas e anomalias |
| 7 | Portal usuario | Historico e demonstrativo individual |
| 8 | IA inicial | Previsao de consumo e deteccao de anomalias |
| 9 | Adapter GoodWe | Integracao com SEMS/API se acesso estiver disponivel |
| 10 | Pitch tecnico | Roteiro e demo de 3 minutos |

## Pontos que ainda dependem da equipe

- Nome da equipe e RMs.
- Link real do repositorio.
- Acesso real a uma conta GoodWe/SEMS+.
- Regras finais de taxa operacional e ociosidade, que devem ser validadas conforme contexto escolhido: condominio, predio corporativo ou campus.

