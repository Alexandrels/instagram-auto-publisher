# Instagram Auto Publisher

Publicacao automatizada no feed do Instagram via Instagram Graph API.

## Configuracao

1. Copie `.env.example` para `.env`.
2. Preencha `IG_USER_ID`, `IG_ACCESS_TOKEN` e `GRAPH_API_VERSION`.
3. Ative o ambiente virtual:

```bash
source venv/bin/activate
pip install -e '.[test]'
```

## Publicar uma imagem

Use somente uma URL HTTPS publica e diretamente acessivel:

```bash
PYTHONPATH=src python scripts/publish.py \
  --image-url "https://example.com/test-image.jpg" \
  --caption "Teste automatizado"
```

No Windows, use `venv\\Scripts\\activate` e ajuste o executavel conforme o ambiente.

O fluxo cria um contêiner, aguarda o estado `FINISHED` e publica a mídia.
Estados `ERROR` e `EXPIRED`, timeout e erros da Graph API interrompem o fluxo.

## Midias avancadas

O cliente tambem possui metodos para:

- `create_carousel_item()` e `publish_carousel()` para carrosseis.
- `create_reel()` e `publish_reel()` para Reels.
- `PublishLedger` para registrar publicacoes confirmadas em uma janela de 24 horas.
- `PublishQueue` para enfileirar, reivindicar e concluir jobs com persistencia SQLite.

O contador deve registrar apenas o `media_id` retornado pela publicacao confirmada.
O limite operacional recomendado para inicio e uso conservador e de 25 publicacoes por 24 horas.

Contêineres sao criados apenas no processamento imediato do job, porque expiram aproximadamente
apos 24 horas. Nao reutilize contêineres antigos nem publique o mesmo job sem uma chave externa
idempotente.

## Testes

```bash
PYTHONPATH=src pytest -q
```

Os testes unitarios usam mocks e nao chamam a Meta.
