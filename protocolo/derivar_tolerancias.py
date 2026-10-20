"""Deriva as tolerâncias de H2 da precisão de publicação dos oráculos.

Regra do protocolo: tolerância nunca é escolhida. Ela é a soma, em pior caso
(aritmética de intervalos), de meia unidade da última casa publicada de cada
grandeza que entra no cálculo, propagada até a grandeza comparada, mais meia
unidade da última casa do valor publicado com que se compara.

Este script usa só valores PUBLICADOS (oráculo e premissas). Não calcula
nenhuma grandeza derivada do SBSJ: rodá-lo não antecipa o resultado do ato 1.
Uso: python3 derivar_tolerancias.py  (imprime o bloco que vai no protocolo)
"""
import sys
from math import cos, radians, sin, degrees

sys.path.insert(0, "gabarito")
from geodesia import aip, raios, direta, inversa  # noqa: E402

# Premissas publicadas (AD 2.12), resolução 0,01"
THR16 = (aip("231310.79S"), aip("0455219.08W"))
THR34 = (aip("231412.21S"), aip("0455112.46W"))
RES_COORD_S = 0.01            # segundos de arco
# Oráculos publicados
AZ_V_16 = 134.93              # AD 2.12, resolução 0,01°
AZ_V_34 = 314.92
L_PUB = 2675                  # AD 2.12 / ADC, resolução 1 m
RES_DIST = 1.0                # TORA/TODA/ASDA/LDA e SWY, resolução 1 m
RES_RUMO_MAG = 1.0            # ADC, BRG MAG em graus inteiros
RES_VAR = 1.0                 # ADC, VAR 22°W em graus inteiros
RES_AZ = 0.01


def meia(r):
    return r / 2


def caixa_m(lat):
    """Meia-largura em metros da caixa de arredondamento de uma coordenada."""
    M, N = raios(lat)
    rad = radians(meia(RES_COORD_S) / 3600)
    return M * rad, N * cos(radians(lat)) * rad   # (norte, leste)


def propagacao():
    a = radians(AZ_V_16)
    ao_longo = (sin(a), cos(a))             # (leste, norte)
    lateral = (cos(a), -sin(a))
    long_tot = lat_tot = 0.0
    for lat in (THR16[0], THR34[0]):
        dn, de = caixa_m(lat)
        long_tot += abs(de * ao_longo[0]) + abs(dn * ao_longo[1])
        lat_tot += abs(de * lateral[0]) + abs(dn * lateral[1])
    return long_tot, lat_tot


def cenario_ato4():
    """Remedição simulada da cabeceira 34 (premissa do cenário, não tolerância).

    THR 34 desloca 1,00 m para fora da pista no prolongamento do eixo e 0,50 m
    para sudoeste, a partir das coordenadas publicadas e com o rumo publicado
    (oráculo), e é republicada arredondada a 0,01", como o AIP publicaria.
    """
    para_fora = AZ_V_34 - 180                      # 314,92° − 180° = 134,92°
    lat, lon, _ = direta(*THR34, para_fora, 1.00)
    lat, lon, _ = direta(lat, lon, (para_fora + 90) % 360, 0.50)

    def fmt(v, hem, gw):
        v = abs(v)
        g = int(v); m = int((v - g) * 60); s = round(((v - g) * 60 - m) * 60, 2)
        if s >= 60:
            s -= 60; m += 1
        return f"{g:0{gw}d}{m:02d}{s:05.2f}{hem}"

    lat_t, lon_t = fmt(lat, "S", 2), fmt(lon, "W", 3)
    real, _, _ = inversa(*THR34, aip(lat_t), aip(lon_t))
    return lat_t, lon_t, real


if __name__ == "__main__":
    dl, dt = propagacao()
    dalfa = degrees(dt / L_PUB)
    tol_L = meia(RES_DIST) + dl
    print(f"propagacao_comprimento_m: {dl:.4f}")
    print(f"propagacao_azimute_graus: {dalfa:.5f}")
    print(f"tol_comprimento_m: {tol_L:.3f}")
    print(f"tol_azimute_verdadeiro_graus: {meia(RES_AZ) + dalfa:.4f}")
    print(f"tol_rumo_magnetico_graus: {meia(RES_RUMO_MAG) + meia(RES_VAR) + dalfa:.3f}")
    print(f"tol_tora_toda_lda_asda34_m: {tol_L:.3f}")
    print(f"tol_asda16_m: {tol_L + meia(RES_DIST):.3f}")
    lat_t, lon_t, real = cenario_ato4()
    print(f"ato4_thr34_remedida: {lat_t} {lon_t}  (deslocamento real após arredondamento: {real:.3f} m)")
