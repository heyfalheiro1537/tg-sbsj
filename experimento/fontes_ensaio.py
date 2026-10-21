"""Aeródromo fictício para ENSAIAR o notebook antes do congelamento.

Mesma estrutura de fontes.py, com números inventados (perto de 10°S 50°W).
Serve só para conferir que as células rodam. Nada calculado com estes dados
vale como resultado: no modo ensaio o notebook não grava no registro de
execuções e marca cada verificação como [ENSAIO].
"""
from datetime import datetime, timezone

UTC = timezone.utc

AIRAC_2213 = datetime(2022, 12, 29, tzinfo=UTC)
AIRAC_2604 = datetime(2026, 4, 16, tzinfo=UTC)
EAIP_20_2026 = datetime(2026, 10, 1, tzinfo=UTC)

THR16 = {"lat": "100000.00S", "lon": "0500000.00W", "elev_m": 500.0, "gund_m": -2.0}
THR34 = {"lat": "100100.00S", "lon": "0495900.00W", "elev_m": 510.0, "gund_m": -2.0}
LARGURA_RWY = 45
SWY = {"comprimento": 200, "largura": 45, "aplica_a": "16", "alem_de": "THR34"}
FAIXA = {"comprimento": 2900, "largura": 280}
SUPERFICIE = "ASPH"
PCN = "60/F/A/X/T"
VARIACAO_LESTE = -20.0
ARP = {"lat": "100030S", "lon": "0495930W"}

FORMA_AIRAC_2213 = {
    "pista": {"comprimento": 2610, "largura": 45},
    "swy": {"comprimento": 220, "largura": 45},
    "faixa": {"comprimento": 2950, "largura": 300},
    "distancias": {"rwy16": {"tora": 2610, "toda": 2610, "asda": 2830, "lda": 2610},
                   "rwy34": {"tora": 2610, "toda": 2610, "asda": 2610, "lda": 2610}},
}
FORMA_AIRAC_2604 = {
    "pista": {"comprimento": 2609, "largura": 45},
    "swy": {"comprimento": 200, "largura": 45},
    "faixa": {"comprimento": 2900, "largura": 280},
    "distancias": {"rwy16": {"tora": 2609, "toda": 2609, "asda": 2809, "lda": 2609},
                   "rwy34": {"tora": 2609, "toda": 2609, "asda": 2609, "lda": 2609}},
}

THR34_REMEDIDA = {"lat": "100100.03S", "lon": "0495859.99W", "elev_m": 510.0, "gund_m": -2.0}


def gms(texto):
    h = texto[-1]
    corpo = texto[:-1]
    inteiro, _, frac = corpo.partition(".")
    gw = 2 if h in "NS" else 3
    g, m = int(inteiro[:gw]), int(inteiro[gw:gw + 2])
    s = float(inteiro[gw + 2:] + ("." + frac if frac else ""))
    v = g + m / 60 + s / 3600
    return -v if h in "SW" else v
