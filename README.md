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

## Testes

```bash
PYTHONPATH=src pytest -q
```

Os testes unitarios usam mocks e nao chamam a Meta.
