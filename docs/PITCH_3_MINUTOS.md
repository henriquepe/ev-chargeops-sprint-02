# Pitch de três minutos — roteiro de preparação

A atividade informa que o pitch individual deverá ser gravado/apresentado na etapa presencial da prova obrigatória. Este roteiro não substitui essa etapa. Adapte a linguagem à sua voz e apresente somente o que você entendeu e consegue demonstrar.

## 0:00–0:25 — problema

“Sou Henrique Pires, RM 568600, e este é o EV ChargeOps. Em uma garagem compartilhada, disponibilizar o carregador não resolve toda a operação. É preciso saber quem carregou, quanto consumiu e como dividir o custo sem cobrar de quem não usou. Também precisamos identificar sessões suspeitas antes de transformá-las em uma despesa.”

**Na tela:** dashboard de setembro, com sessões, consumo e retenções.

## 0:25–1:00 — solução funcionando

“O protótipo registra cada sessão com unidade, veículo, horários e medidores. A energia vem da diferença entre o medidor final e o inicial. O cálculo separa energia, operação, ociosidade e perdas. Aqui eu gero uma sessão, e ela passa pela API e pelo banco. No demonstrativo, consigo explicar cada parcela. O morador consulta somente os dados da sua unidade.”

**Na tela:** gerar sessão normal; abrir detalhe. Depois, mostrar um demonstrativo por unidade.

## 1:00–1:45 — IA que altera o fluxo

“A inteligência não é apenas um gráfico. Treinamos um detector com mediana e dispersão robusta do histórico. Esta sessão dura 650 minutos, muito acima do padrão, então é retida e não entra na cobrança até uma revisão justificada. Falhas de identificação ou medição exigem exclusão e correção. Também usamos regressão para prever consumo diário e consolidar o restante do mês. A previsão é comparada com uma referência semanal usando os últimos quatorze dias, sem colocar dados futuros no treino.”

**Na tela:** abrir `demo-anomaly` ou uma nova simulação de anomalia; mostrar o motivo. Abrir Inteligência e apontar MAE e baseline. Não decorar métricas se a base foi alterada: leia o valor atual da tela.

## 1:45–2:20 — arquitetura e prova

“A arquitetura mantém a proposta da primeira fase: FastAPI, React, PostgreSQL, SQLAlchemy e scikit-learn. As faturas são snapshots imutáveis. Eventos repetidos não duplicam cobrança, decisões ficam na auditoria e moradores são isolados pela API. Além dos testes automatizados, executamos o fluxo HTTP completo com PostgreSQL, inclusive uma disputa entre dois revisores sobre a mesma sessão.”

**Na tela:** rateio, auditoria ou relatório de evidências. Mostrar um caso concreto é mais convincente que listar ferramentas rapidamente.

## 2:20–2:50 — limites e evolução

“Os dados são sintéticos e isso está identificado em todas as telas. Como não tivemos acesso à conta do laboratório, usamos o simulador previsto na primeira fase. O próximo passo é validar o contrato com dados reais do HCA G2, calibrar os modelos e medir seu comportamento em operação. O sistema não controla carga elétrica nem realiza pagamentos.”

## 2:50–3:00 — encerramento

“O resultado é um ciclo demonstrável: recarga registrada, consumo atribuído, anomalias revisadas e rateio explicável. O repositório contém código, instruções, testes e evidências para reproduzir esse fluxo.”

## Preparação prática

- Rode a demonstração antes da prova e ensaie com cronômetro. O texto deve ser falado com pausas, ajustando-o à sua velocidade.
- Prepare setembro aberto ou use uma nova instância Compose conforme o README. Faturas já fechadas não podem ser reabertas no MVP.
- Deixe uma anomalia pendente para a demonstração. Gerar uma nova é possível no mês aberto.
- Saiba refazer o exemplo R$ 13,49 + R$ 1,50 + R$ 0,27 = R$ 15,26.
- Se a demonstração ao vivo não couber no tempo, use as capturas reais do repositório e explique que representam uma execução registrada.
- Não alegue homologação GoodWe, precisão real, pagamento integrado ou implementação de chatbot.
