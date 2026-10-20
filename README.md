# TG — SBSJ

Trabalho de graduação sobre metamodelagem paramétrica e dados auditáveis do lado ar de aeroportos, com o SBSJ (São José dos Campos) como cenário.

**Comece pelo [GUIA.md](GUIA.md):** o que foi feito, as decisões, como rodar e o que vem a seguir.

## Estrutura

- `protocolo/` — protocolo de falseamento (H1–H4), **congelado** antes de qualquer execução. Não editar: uma correção vira nova versão.
- `artefato/` — o artefato do TG: esquema do banco, ledger, referencial, motor, derivações e testes.
- `docker-compose.yml`, `Dockerfile.jupyter` — PostGIS + Jupyter.
- `scripts/pg_local.sh` — PostgreSQL local, sem Docker.

## Rodar os testes

```sh
pip install -r requirements.txt
scripts/pg_local.sh
cd artefato && python3 -m pytest -q tests
```

## Conferir o protocolo

```sh
cd protocolo && sha256sum -c PROTOCOLO.sha256
```

## Ressalva

Dados do AIP Brasil (DECEA) usados para pesquisa. Nada aqui substitui a publicação oficial.
