# Roadmap de desenvolvimento

Este documento registra o estado do projeto e os passos para evoluir o MVP para
um serviço confiavel de publicacao automatizada no Instagram via Instagram
Graph API.

> **Estado geral:** MVP parcial. O fluxo basico e os prototipos de midia,
> retentativas, cota e fila existem, mas ainda nao estao prontos para uso em
> producao. Os testes unitarios nao substituem uma validacao com a API real.

## Concluido

- [x] Repositorio Git inicializado, branch `main` criada e branch de trabalho
  `feature/passos-inicias-projeto` enviada ao GitHub.
- [x] Ambiente virtual e dependencias Python iniciais configurados.
- [x] `.gitignore` protege `.env`, ambientes virtuais, caches e artefatos locais.
- [x] `.env.example` e carregamento validado de `IG_USER_ID`,
  `IG_ACCESS_TOKEN` e `GRAPH_API_VERSION`.
- [x] Cliente da Graph API para criar contêiner de imagem, consultar estado
  (`IN_PROGRESS`, `FINISHED`, `ERROR`, `EXPIRED`) e publicar.
- [x] CLI para iniciar publicacoes de imagem, carrossel e Reel.
- [x] Tratamento inicial de erros da API, timeout e retentativas com backoff.
- [x] Estruturas SQLite iniciais para registrar publicacoes e jobs.
- [x] Testes automatizados sem chamadas reais a Meta; ultima execucao local:
  **20 testes passaram**.

## Implementado parcialmente — precisa de evolucao

- **Carrosseis:** existe fluxo para itens de imagem, mas falta validar regras
  atuais da plataforma e suportar/testar todos os tipos de item pretendidos.
- **Reels:** existe fluxo de contêiner e publicacao, mas nao ha validacao
  tecnica do video nem teste de integracao real.
- **Retentativas:** backoff inicial existe, mas repetir um `POST` cujo resultado
  ficou incerto pode duplicar uma publicacao.
- **Cota:** o ledger contabiliza registros locais, mas nao bloqueia o fluxo de
  publicacao, nao reserva cota atomicamente e nao conhece publicacoes feitas
  fora do servico.
- **Fila:** permite enfileirar e alterar estados, mas ainda nao e um scheduler
  completo nem executa jobs.

## Ainda falta

- [ ] Tornar a publicacao segura contra duplicidade em falhas de rede e
  resultados incertos.
- [ ] Implementar worker que encontre jobs vencidos e processe-os no horario
  devido, criando contêineres Just-In-Time.
- [ ] Impedir que jobs futuros sejam reivindicados; adicionar recuperacao de
  jobs abandonados, `retry_at`, leases e transicoes de estado validadas.
- [ ] Evitar que um job existente seja sobrescrito/resetado ao enfileirar o
  mesmo identificador.
- [ ] Aplicar a cota antes de publicar, com reserva concorrente e uma politica
  conservadora para publicacoes externas e limites variaveis da Meta.
- [ ] Validar disponibilidade e formato das URLs e requisitos de imagens e
  videos antes de criar contêineres.
- [ ] Completar onboarding/documentacao da Meta: conta profissional vinculada,
  permissoes, configuracao do app e ciclo de vida/renovacao do token.
- [ ] Confirmar a versao da Graph API e os limites/requisitos de midia na
  documentacao oficial vigente antes de cada release.
- [ ] Executar teste controlado de ponta a ponta com uma conta autorizada e
  uma unica midia; testes atuais sao mockados.
- [ ] Adicionar CI, logs estruturados sem segredos, alertas, estrategia de
  backup e procedimento operacional de falhas.

## Proximos passos

### 1. Corrigir idempotencia e retentativas — prioridade imediata

- Separar retentativas de operacoes que podem ser repetidas com seguranca das
  operacoes de publicacao.
- Em timeout/erro de rede durante `media_publish`, marcar o resultado como
  incerto e reconciliar o estado antes de tentar novamente.
- Nao repetir publicacao automaticamente sem uma estrategia de idempotencia.
- Testar: API retorna erro permanente, rate limit, falha de rede antes do envio
  e perda de resposta depois do envio.

**Pronto quando:** uma falha ambigua nao leva a uma segunda publicacao
automatica e erros permanentes nao sao repetidos.

### 2. Completar fila e worker — antes de habilitar agendamentos

- Adicionar consulta atomica dos jobs vencidos.
- Fazer `claim` respeitar `scheduled_for` e permitir recuperacao de workers
  interrompidos por meio de lease/timeout.
- Persistir tentativas e proximo horario de retry.
- Integrar worker ao cliente para criar o contêiner perto do horario marcado,
  aguardar processamento e publicar.
- Tornar transicoes de estado explicitas e impedir que um job concluido seja
  reaberto ou sobrescrito.

**Pronto quando:** jobs futuros nao rodam cedo, jobs concluidos nao repetem e
jobs abandonados podem ser recuperados sem duplicar publicacoes.

### 3. Integrar protecao de cota

- Consultar a cota local antes de reivindicar/publicar.
- Reservar capacidade atomicamente entre workers e confirmar somente apos
  resposta de publicacao bem-sucedida.
- Tratar limite da API como autoridade final; cooldowns devem ser persistidos,
  nao apenas esperados em memoria.
- Documentar que o contador local nao representa publicacoes externas, a menos
  que elas sejam sincronizadas.

**Pronto quando:** a aplicacao bloqueia preventivamente ao atingir seu limite
configurado e respeita cooldowns retornados pela API.

### 4. Validar midia e requisitos da plataforma

- Validar URL publica HTTPS, acessibilidade e tipo de conteudo.
- Validar dimensoes/proporcao/tamanho da imagem.
- Validar formato, duracao, dimensoes e codec de video.
- Validar quantidade e composicao dos itens de carrossel conforme a API vigente.

**Pronto quando:** entradas invalidas falham localmente com erro claro, antes
de consumir chamadas/criar contêineres.

### 5. Testar integracao Meta de forma controlada

- Configurar app Meta, conta profissional elegivel e permissao de publicacao.
- Usar credenciais somente em `.env` local ou secret manager; nunca em commits,
  logs ou tickets.
- Fazer uma publicacao manual controlada e verificar status do contêiner,
  resposta final e post na conta.
- Registrar os requisitos e o procedimento de revogacao/renovacao do token.

**Pronto quando:** existe evidência de uma publicacao real bem-sucedida e os
erros observados estao cobertos por testes sem credenciais.

### 6. Preparar operacao

- Configurar pipeline CI para instalar o projeto e executar testes.
- Adicionar logs estruturados, metricas e alertas sem tokens ou dados sensiveis.
- Definir deploy, execucao do worker, backup/restauracao SQLite e retencao de
  dados.
- Documentar runbook para rate limit, token expirado, contêiner expirado e
  publicacao com resultado incerto.

**Pronto quando:** o servico pode ser implantado, monitorado e recuperado sem
depender de execucao manual no computador de desenvolvimento.

## Como validar o estado atual

Execute os testes unitarios a partir da raiz do repositorio:

```bash
PYTHONPATH=src venv/bin/python -m pytest -q
```

Uma execucao bem-sucedida confirma os testes locais atuais; nao confirma
permissoes, compatibilidade ou publicacao na Graph API real.
