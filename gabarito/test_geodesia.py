"""Valida o gabarito contra um caso publicado, nunca contra o SBSJ.

Caso de teste clássico de Vincenty no GRS80 (Geoscience Australia):
Flinders Peak → Buninyong.
s = 54 972,271 m; azimute direto 306°52'05,37"; azimute reverso 127°10'25,07".
"""
from geodesia import dms, inversa, direta, aip

FP = (dms(37, 57, 3.72030, "S"), dms(144, 25, 29.52440, "E"))
BU = (dms(37, 39, 10.15610, "S"), dms(143, 55, 35.38390, "E"))
S_PUB = 54972.271
AZ12_PUB = dms(306, 52, 5.37, "N")
AZ21_PUB = dms(127, 10, 25.07, "N")


def test_inversa():
    s, az12, az21 = inversa(*FP, *BU)
    assert abs(s - S_PUB) < 0.0005          # publicado em mm
    assert abs(az12 - AZ12_PUB) < 0.005 / 3600
    assert abs(az21 - AZ21_PUB) < 0.005 / 3600


def test_direta_volta_ao_ponto():
    lat, lon, _ = direta(*FP, AZ12_PUB, S_PUB)
    assert abs(lat - BU[0]) < 0.0001 / 3600
    assert abs(lon - BU[1]) < 0.0001 / 3600


def test_leitura_formato_aip():
    assert abs(aip("231310.79S") - dms(23, 13, 10.79, "S")) < 1e-12
    assert abs(aip("0455219.08W") - dms(45, 52, 19.08, "W")) < 1e-12


if __name__ == "__main__":
    test_inversa(); test_direta_volta_ao_ponto(); test_leitura_formato_aip()
    print("gabarito: 3/3 testes passaram")
