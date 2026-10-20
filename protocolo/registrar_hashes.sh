#!/bin/sh
# Registra os hashes do protocolo e dos artefatos que ele cita.
# Rodar antes de qualquer execução; depois commit + tag.
set -e
cd "$(dirname "$0")"
sha256sum protocolo.yaml derivar_tolerancias.py gabarito/geodesia.py gabarito/test_geodesia.py \
  adc/adc_geo.py adc/calibrar_adc.py adc/extrair_contornos.py adc/calibracao.json adc/contornos_brutos.geojson \
  > PROTOCOLO.sha256
cat PROTOCOLO.sha256
