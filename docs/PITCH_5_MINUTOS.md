# Pitch de cinco minutos — roteiro de preparação

Atualizado em **09/10/2026** após reler o [enunciado da Sprint 02](https://on.fiap.com.br/mod/assign/view.php?id=662437&returnto=conteudocurso). A orientação atual é gravar o pitch individual de **cinco minutos durante a prova presencial obrigatória agendada**. A apresentação presencial habilita a validação das notas. O roteiro de três minutos usado em setembro foi substituído.

Adapte a linguagem à sua voz. Ensaie com cronômetro, incluindo os cliques, e apresente somente aquilo que você consegue explicar. O texto abaixo é um apoio; não é comprovação automática de domínio do código.

## 0:00–0:40 — problema e proposta

“Sou Henrique Pires, RM 568600, e este é o EV ChargeOps, desenvolvido para o desafio GoodWe e FIAP. Em uma garagem compartilhada, disponibilizar o carregador não resolve toda a operação. Precisamos saber quem carregou, quanto consumiu e como dividir o custo sem cobrar energia de quem não usou. Também precisamos identificar registros inconsistentes antes de transformá-los em uma despesa. Nossa proposta conecta sessão, consumo individual, rateio e inteligência operacional, mantendo uma explicação verificável para gestor e morador.”

**Na tela:** dashboard de setembro de 2026. Aponte consumo, rateio e sessões retidas. Explique que os dados são sintéticos.

## 0:40–1:30 — sessão e cálculo verificável

“O protótipo recebe cada sessão com usuário, unidade, veículo, carregador, horários e medidores. A energia é a diferença entre o medidor final e o inicial. Ao simular esta recarga, o registro passa pela API e fica no banco. Um identificador único evita duplicidade quando um evento é reenviado. No nosso exemplo, 14,2 kWh a 95 centavos custam 13 reais e 49 centavos. Somamos 1 real e 50 centavos de operação e 27 centavos de perdas, chegando a 15 reais e 26 centavos. A ociosidade ficou dentro da franquia e não gerou taxa. Cada componente usa cálculo decimal e arredondamento em centavos.”

**Na tela:** Simular recarga normal → detalhe. Em Rateio e faturas → Ver cálculo, localize a sessão gerada. Reserve alguns segundos para os cliques.

## 1:30–2:35 — IA integrada à decisão

“O detector aprende medianas e dispersões de sessões históricas válidas, usando energia, duração, potência média e ociosidade. Esta sessão durou 650 minutos e entregou apenas 12 kWh. O comportamento foge do histórico, então ela fica retida e seu valor não entra no rateio. A tela informa as variáveis que causaram o alerta e a versão do modelo. O gestor pode aprovar uma anomalia estatística com justificativa, e a decisão fica auditada. Uma falha de medição ou de identificação não pode ser liberada: precisa ser excluída e corrigida por um novo registro. A integração é concreta, porque remover a análise mudaria quais sessões podem ser cobradas.”

**Na tela:** abrir uma anomalia pendente, mostrar score e explicação; preencher uma justificativa e aprovar. Compare a mudança no rateio. Prepare a sessão antes do ensaio para não gastar tempo procurando.

## 2:35–3:20 — previsão e avaliação

“Também projetamos o consumo do mês com regressão Ridge, usando tendência e dia da semana. Os últimos quatorze dias são separados para validação, e comparamos o erro com uma referência baseada na média semanal. Selecionamos a alternativa com menor MAE e depois a ajustamos com o histórico disponível para prever o restante do mês. MAE é o erro absoluto médio em kWh por dia. Essa avaliação evita colocar dados futuros no treino. Como a base é sintética, os números demonstram que o método funciona no protótipo, mas não comprovam precisão em uma operação real.”

**Na tela:** Inteligência. Aponte as datas de treino e validação, os dois erros e o modelo selecionado. Leia os valores atuais: novas sessões e revisões alteram a série.

## 3:20–4:10 — arquitetura, persistência e evidências

“A arquitetura mantém FastAPI, React, PostgreSQL, SQLAlchemy e scikit-learn, como planejado na primeira fase. O fechamento mensal grava um demonstrativo imutável; ele não é recalculado com tarifas futuras. Eventos repetidos não duplicam consumo, e o morador só acessa a própria unidade, com autorização verificada pela API. Testamos os cálculos, a identidade dos usuários, entradas inválidas, revisão, previsão e fechamento. O fluxo HTTP também foi exercitado com PostgreSQL real, incluindo dois revisores concorrentes: somente uma decisão pode prevalecer. As capturas e saídas dos testes estão no repositório.”

**Na tela:** demonstrativo fechado, auditoria ou relatório de evidências. Se mostrar outubro, identifique que a competência futura foi criada apenas para o teste sintético. Não sugira que houve uma recarga real nessa data.

## 4:10–4:45 — limites e participação pessoal

“Usamos o simulador previsto na primeira fase porque não tivemos acesso ao carregador e à conta do laboratório. Não há integração GoodWe homologada, controle de carga elétrica nem pagamentos reais. O próximo passo é obter dados do HCA G2, validar o contrato de entrada e calibrar os modelos. O desenvolvimento teve apoio de IA. Para demonstrar minha compreensão, consigo acompanhar uma sessão desde a validação até o rateio e explicar por que as decisões de cálculo, revisão e acesso foram adotadas.”

**Antes de usar a última frase:** confirme que você consegue demonstrar esse percurso no código. Se ainda não conseguir, faça os exercícios do guia; não apresente uma afirmação sem sustentação.

## 4:45–5:00 — encerramento

“O resultado é um ciclo demonstrável: sessão registrada, consumo atribuído, anomalias revisadas e rateio explicável. O repositório reúne código, instruções, decisões e evidências para reproduzir a solução.”

## Preparar a demonstração

- Siga o README para iniciar a aplicação. Se quiser repetir os cenários, use uma instância nova preservando a existente.
- Selecione setembro de 2026, que é o período do histórico de demonstração. A data de corte da previsão é fixa e está identificada na tela.
- Deixe uma anomalia pendente em um mês aberto. Se a original já foi revisada, gere outra pelo simulador.
- Separe as telas na ordem do roteiro e ensaie o total, incluindo navegação. Ajuste o texto à sua velocidade sem exceder a duração informada.
- Tenha as capturas reais como apoio se a demonstração ao vivo não couber. Diga quando estiver mostrando uma execução registrada.
- Saiba refazer R$ 13,49 + R$ 1,50 + R$ 0,27 = R$ 15,26 e explicar idempotência, MAD, MAE, separação temporal e autorização por unidade.
- O TXT com o repositório é a entrega digital da Sprint 02. O pitch individual na etapa presencial é uma obrigação distinta; um roteiro escrito não substitui sua apresentação.
