"""Dados do SBSJ usados no experimento, cada um com a fonte e o papel.

Papéis (protocolo e plano): premissa entra no ledger e nunca valida a si
mesma; oráculo só é comparado; entrada entra sem validação (vem do desenho).
"""
from datetime import datetime, timezone

UTC = timezone.utc

# ---------------------------------------------------------------- instantes da história
AIRAC_2213 = datetime(2022, 12, 29, tzinfo=UTC)     # AOC (F2)
AIRAC_2604 = datetime(2026, 4, 16, tzinfo=UTC)      # ADC (F1)
EAIP_20_2026 = datetime(2026, 10, 1, tzinfo=UTC)    # AD 2.12 / AD 2.13 (F3, F4)

# ---------------------------------------------------------------- premissas (F3, AD 2.12)
THR16 = {"lat": "231310.79S", "lon": "0455219.08W", "elev_m": 619.3, "gund_m": -2.6}
THR34 = {"lat": "231412.21S", "lon": "0455112.46W", "elev_m": 647.0, "gund_m": -3.0}
LARGURA_RWY = 45                       # F3 col. 3
SWY = {"comprimento": 283, "largura": 45, "aplica_a": "16", "alem_de": "THR34"}   # F3 col. 8
FAIXA = {"comprimento": 3118, "largura": 280}                                      # F3 col. 10
SUPERFICIE = "ASPH"
PCN = "71/F/A/X/T"

# ---------------------------------------------------------------- premissas (F1, ADC)
VARIACAO_LESTE = -22.0                 # VAR 22°W 2026 (oeste negativo)
ARP = {"lat": "231344S", "lon": "0455216W"}   # ADC cabeçalho (AD 2.2), resolução 1"

# ---------------------------------------------------------------- prólogo: modo forma (F2 e F1)
FORMA_AIRAC_2213 = {
    "pista": {"comprimento": 2676, "largura": 45},
    "swy": {"comprimento": 325, "largura": 45},
    "faixa": {"comprimento": 3121, "largura": 300},
    "distancias": {"rwy16": {"tora": 2676, "toda": 2676, "asda": 3001, "lda": 2676},
                   "rwy34": {"tora": 2676, "toda": 2676, "asda": 2676, "lda": 2676}},
}
FORMA_AIRAC_2604 = {
    "pista": {"comprimento": 2675, "largura": 45},
    "swy": {"comprimento": 283, "largura": 45},
    "faixa": {"comprimento": 3118, "largura": 280},
    "distancias": {"rwy16": {"tora": 2675, "toda": 2675, "asda": 2958, "lda": 2675},
                   "rwy34": {"tora": 2675, "toda": 2675, "asda": 2675, "lda": 2675}},
}

# ---------------------------------------------------------------- ato 4 (cenário fixado no protocolo)
THR34_REMEDIDA = {"lat": "231412.24S", "lon": "0455112.45W", "elev_m": 647.0, "gund_m": -3.0}

# ---------------------------------------------------------------- rótulos das manchas do ADC
# Informativos: a unidade de teste de H1 é o contorno como desenhado; o rótulo
# só dá o tipo da feature e o nome na carta (protocolo v0.4, H1.unidade_de_teste).
ROTULOS = {
    "891": ("taxiway", "TWY A"), "893": ("taxiway", "TWY B"), "894": ("taxiway", "TWY C"),
    "897": ("taxiway", "TWY D"), "890": ("taxiway", "TWY E"), "898": ("taxiway", "TWY E"),
    "971": ("taxiway", "TWY E"), "889": ("taxiway", "ligação"), "786": ("taxiway", "ligação"),
    "885": ("apron", "APN 1"), "888": ("apron", "APN 2"), "876": ("apron", "APN 3"),
    "887": ("apron", "APN 4"), "872": ("apron", "APN 4"), "886": ("apron", "APN 5"),
    "836": ("apron", "APN 6"), "837": ("apron", "APN 7"), "860": ("apron", "APN 8"),
}
ROTULO_PADRAO = ("pavement", "pavimento sem designação (área de teste de motores e acessos)")


def gms(texto):
    """'231310.79S' → graus decimais."""
    h = texto[-1]
    corpo = texto[:-1]
    inteiro, _, frac = corpo.partition(".")
    gw = 2 if h in "NS" else 3
    g, m = int(inteiro[:gw]), int(inteiro[gw:gw + 2])
    s = float(inteiro[gw + 2:] + ("." + frac if frac else ""))
    v = g + m / 60 + s / 3600
    return -v if h in "SW" else v
