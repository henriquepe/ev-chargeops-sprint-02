# Guia de estudo — entender antes de apresentar

Este material é um roteiro de leitura crítica. A implementação foi desenvolvida com apoio de IA; conseguir executar os passos não substitui compreender as decisões.

## A história que o código conta

Uma recarga termina. O sistema recebe seu identificador, usuário, unidade, carregador, medidores e horários. Primeiro, verifica se já recebeu esse evento. Depois, valida se a unidade corresponde ao usuário, se o medidor é coerente e se a energia cabe no tempo ativo e na potência nominal. A IA compara o comportamento ao histórico. Só uma sessão elegível entra no rateio. No fechamento, a fatura congela valores e regras; o histórico explica como se chegou à cobrança.

## Percurso pelo código

| Leia nesta ordem | O que localizar | O que explicar sem consultar |
|---|---|---|
| `backend/app/schemas.py` | `SessionInput`, `coherent_time` | Por que horários precisam de timezone? Por que `Decimal` na energia? |
| `backend/app/models.py` | Sessão, tarifa, fatura e auditoria | Por que separar sessão operacional de fatura fechada? |
| `backend/app/sessions.py` | `ingest` | Como o hash impede reuso conflitante de ID? Qual a diferença entre rejeitar contrato e reter uma sessão? |
| `backend/app/intelligence.py` | `train_anomaly`, `score_session` | O que a mediana/MAD aprende? Onde o resultado altera a cobrança? |
| `backend/app/billing.py` | `session_cost`, `preview`, `close_month` | Quando ocorre arredondamento? Por que fechar é diferente de calcular a prévia? |
| `backend/app/sessions.py` | `review` | Por que a IA pode ser revisada e um medidor regressivo não pode ser aprovado? |
| `backend/app/intelligence.py` | `forecast` | Qual é o alvo da regressão? Qual é o corte temporal? O que é MAE? |
| `backend/app/auth.py` e `main.py` | `current_user`, `manager`, filtros de unidade | Por que esconder um botão não protege os dados de um morador? |
| `frontend/src/main.jsx` | Componentes e função `mutate` | Como uma ação na tela chega à API e atualiza os dados? |
| `scripts/evidence.py` | Asserções reais HTTP | Qual resultado prova cada afirmação do README? |

## Conceitos essenciais

**Idempotência:** enviar duas vezes o mesmo evento produz uma sessão. O identificador é único e o hash do conteúdo detecta uma repetição diferente. Créditos também possuem identificador. Depois do fechamento, uma repetição idêntica de uma sessão existente continua sendo apenas uma leitura do registro já salvo, sem nova cobrança.

**Transação e concorrência:** em PostgreSQL, a linha da tarifa mensal serve de trava para escritas no período. Uma revisão recarrega a sessão sob trava antes de decidir; um segundo operador vê que ela já foi revisada e recebe 409. A gravação operacional e a auditoria pertencem à mesma transação. O teste HTTP dispara dois revisores e exige exatamente um sucesso.

**Dinheiro:** floats não representam todos os centavos exatamente. O motor usa `Decimal`, arredonda cada componente com `ROUND_HALF_UP` e devolve inteiros em centavos. A tela formata R$ 15,26 a partir de 1526; não recalcula a cobrança.

**Anomalia não é fraude:** um comportamento fora do padrão exige análise; pode ter explicação legítima. A sessão de 650 minutos entrega só 12 kWh, o que chama atenção pela duração e baixa potência média. A revisão humana pode liberá-la com motivo. Já uma sessão sem responsável não tem a quem atribuir a despesa.

**Modelo estatístico treinado:** medianas e escalas vêm de observações anteriores, não de uma resposta pronta de um chatbot. O limiar e os pisos são parâmetros projetados. A saída controla o estado `pending`, usado diretamente pelo rateio. A regressão é um segundo componente de aprendizado, implementado com scikit-learn.

**Ridge:** ajusta uma relação entre atributos e consumo, penalizando coeficientes grandes para reduzir instabilidade. Os atributos são tendência temporal e dia da semana; a variável alvo é kWh por dia. Não é previsão de potência nem de ocupação instantânea.

**MAE:** média do valor absoluto dos erros. Se a MAE é 2,70 kWh/dia, as previsões desviaram em média 2,70 kWh dos valores observados no conjunto de validação. Isso não é "97% de precisão", e não autoriza prometer o mesmo resultado em produção.

**Validação temporal:** os últimos 14 dias não participam do ajuste usado para a comparação. O baseline é calculado apenas no trecho anterior. Depois da escolha, o modelo final usa os dias conhecidos até o corte. Ainda seria necessário um teste externo ou várias janelas temporais para estimar generalização; escolher pelo mesmo holdout não equivale a avaliação final independente.

**Demonstrativo imutável:** uma prévia acompanha dados e regras atuais. Uma fatura fechada usa o snapshot salvo. Não recalcular faturas antigas com uma tarifa nova evita divergência entre relatório e cobrança. O MVP não possui reabertura nem ajuste pós-fechamento.

## Exercícios para ensaiar

1. Refaça à mão o total de R$ 15,26 de uma sessão normal. Depois, troque a tarifa do mês aberto e explique a diferença.
2. Gere uma interrupção: identifique energia, duração e motivo de encerramento. Confira que não há estimativa de energia que o carro deixou de receber.
3. Gere uma sessão sem identificação. Tente fechar o mês. Explique por que excluir com motivo mantém a trilha, enquanto apagar esconderia a falha.
4. Abra uma anomalia, leia as referências históricas e explique cada termo do score. Revise-a e confira o evento de auditoria.
5. Ative uma quota fixa em um mês vazio e observe o apartamento sem consumo. Desative-a novamente antes de fechar. Diferencie consumo variável de custo de infraestrutura.
6. Faça login no morador 102 digitando `morador102@demo.local`. Confira que os dados são dele, mesmo sem existir um botão de atalho para esse usuário.
7. Consulte `/docs` e explique por que a API deve verificar o token e a unidade em toda requisição.
8. Rode os testes e identifique qual deles falharia se o backend removesse o bloqueio das sessões retidas.

## Respostas que a apresentação precisa ser capaz de dar

**Foi conectado ao carregador da FIAP?** Não. O fallback simulado já estava previsto. Sem acesso real, um contrato de entrada e um simulador permitem provar o núcleo. A integração SEMS/Modbus permanece pendente e não foi inventada.

**Por que não usar um LLM?** O problema prioritário é detectar desvios numéricos e prever consumo. Modelos menores, reproduzíveis e explicáveis atendem à prioridade. Chatbot era uma extensão, não o núcleo.

**Por que não Isolation Forest?** Era uma possibilidade na Sprint 01, assim como z-score robusto. Para pouca massa e necessidade de justificar uma retenção ao morador, mediana/MAD simplificam a explicação. Modelos multivariados podem ser comparados quando houver dados reais suficientes.

**O que falta para produção?** Dados e conexão reais, calibração e monitoramento dos modelos, autenticação operacional, segregação por condomínio, revisão de regras de cobrança, políticas de privacidade/retencão, observabilidade e testes de volume, interoperabilidade e segurança elétrica conduzida por profissionais habilitados. O MVP não executa essas responsabilidades físicas.

**O código é compreendido?** A resposta deve ser sua, após estudar e executar os exercícios. Não diga que escreveu manualmente cada linha: explique o apoio de IA e demonstre o entendimento das escolhas.
