#!/bin/sh
# Roda o notebook dos experimentos do começo ao fim, sem interface.
#
#   scripts/rodar_experimentos.sh           execução oficial (exige protocolo v0.5 congelado)
#   scripts/rodar_experimentos.sh --ensaio  ensaio com aeródromo fictício (nada é gravado)
#
# Precisa de um PostgreSQL acessível (scripts/pg_local.sh ou docker compose) e
# das dependências de requirements.txt.
set -e
RAIZ=$(cd "$(dirname "$0")/.." && pwd)
cd "$RAIZ/experimento"

if [ "$1" = "--ensaio" ]; then
  export AEROLEDGER_ENSAIO=1
  ALVO=$(mktemp -d)/experimentos_ensaio.ipynb
  cp experimentos.ipynb "$ALVO"
else
  ALVO="$RAIZ/experimento/experimentos.ipynb"
fi

python3 - "$ALVO" <<'EOF'
import sys
import nbformat
from nbclient import NotebookClient

caminho = sys.argv[1]
nb = nbformat.read(caminho, as_version=4)
NotebookClient(nb, timeout=1800, kernel_name="python3",
               resources={"metadata": {"path": "."}}).execute()
nbformat.write(nb, caminho)
for cell in nb.cells[::-1]:
    if cell.cell_type == "code":
        for o in cell.get("outputs", []):
            md = o.get("data", {}).get("text/markdown")
            if md:
                print(md)
        break
print("notebook executado:", caminho)
EOF
