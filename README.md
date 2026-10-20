# TG — SBSJ

Trabalho de graduação sobre metamodelagem paramétrica e dados auditáveis do lado ar de aeroportos, com o SBSJ (São José dos Campos) como cenário.

## Estrutura

- `protocolo/` — protocolo de falseamento (H1–H4), registrado antes de qualquer execução.
  - `protocolo.yaml` — predições, oráculos e tolerâncias de cada verificação.
  - `PROTOCOLO.sha256` — hashes do protocolo e dos artefatos que ele cita.
  - `derivar_tolerancias.py` — tolerâncias de H2 a partir da precisão de publicação.
  - `gabarito/` — gabarito geodésico independente (Vincenty), validado em caso publicado.
  - `adc/` — calibração do ADC pela gratícula e extração dos contornos (oráculo de H1).

## Congelamento

A tag `protocolo-v0.4` marca o protocolo congelado. Depois dela o protocolo não muda: uma correção vira nova versão, com motivo, registrada antes de executar a parte que ela afeta.

Para conferir a integridade:

```sh
cd protocolo && sha256sum -c PROTOCOLO.sha256
```

## Ressalva

Dados do AIP Brasil (DECEA) usados para pesquisa. Nada aqui substitui a publicação oficial.
