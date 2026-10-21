"""Gera experimentos.ipynb: os cinco experimentos do protocolo v0.5.

O notebook é gerado por este script para que texto e código fiquem revisáveis
no git. Para mudar uma célula, mude aqui e rode: python3 montar_notebook.py
"""
from pathlib import Path

import nbformat as nbf

CELULAS = []


def md(t):
    CELULAS.append(nbf.v4.new_markdown_cell(t.strip()))


def code(t):
    CELULAS.append(nbf.v4.new_code_cell(t.strip()))


# =============================================================================
md(r"""
# Dados aeroportuários auditáveis — cinco experimentos com a pista do SBSJ

**Pergunta.** É possível tornar dados aeroportuários geolocalizados auditáveis — cada valor atribuível, retido, re-derivável e com adulteração evidente —, e quais são os limites dessa garantia?

O notebook usa a biblioteca **`aeroledger`** (o artefato do TG) como uma biblioteca qualquer: cada passo é uma chamada a ela. Cada experimento responde a uma pergunta e termina comparando o que aconteceu com o que o protocolo previa **antes** de rodar.

| | Pergunta | Ótica |
|---|---|---|
| **E1** | Qual é o problema? | as publicações oficiais |
| **E2** | O número se refaz a partir das premissas? | derivação |
| **E3** | Como estava em *t*, quem afirmou e por quê? | as três perguntas do auditor |
| **E4** | Alguém consegue adulterar sem ser visto? | segurança (PANS-AIM 2.2) |
| **E5** | Dois produtos do mesmo ledger podem divergir? A prova é verificável por terceiros? | consistência e interoperabilidade (PANS-AIM 2.1.3.2) |

Fontes: AIP Brasil, AD 2.12 e AD 2.13 (eAIP 20-2026); ADC AIRAC 2604A1; AOC AIRAC 2213A1. Protocolo: `protocolo/v0.5/protocolo.yaml`, que reusa sem alteração as predições de derivação da v0.4.

> Uso em pesquisa. Nada aqui substitui a publicação oficial.
""")

code(r"""
import json
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

RAIZ = Path.cwd().resolve()
if RAIZ.name == "experimento":
    RAIZ = RAIZ.parent
sys.path.insert(0, str(RAIZ / "experimento"))
sys.path.insert(0, str(RAIZ / "protocolo" / "gabarito"))

import matplotlib.pyplot as plt
from IPython.display import Markdown, display

import aeroledger as al                      # o artefato
from aeroledger import adc, derivacoes
from aeroledger.referencial import Resolvedor

import passos                                # registro e apoio do experimento
import ataques                               # E4
import verificador_independente as vi        # E5: não importa aeroledger
import geodesia as gab                       # gabarito geodésico, outro código
from passos import F, seed as s

print("aeroledger", al.__version__, "| modo:", "ENSAIO (dados fictícios)" if passos.ENSAIO else "oficial (SBSJ)")
""")

# =============================================================================
md(r"""
## Passo 0 — Preparação

1. **O protocolo está congelado.** O notebook confere o hash do `protocolo/v0.5/protocolo.yaml` contra o registrado e para se não bater. (No modo ensaio essa conferência é pulada e nada é gravado.)
2. **A biblioteca passa nos seus testes**, sobre um aeródromo fictício.
3. **A execução tem um banco só dela**, que não é apagado depois: dá para auditar qualquer execução.
""")

code(r"""
reg = passos.Registro()
c = reg.congelamento
display(Markdown(f'''
- execução: `{reg.exec_id}` · commit `{reg.commit}`{"" if reg.commit_limpo else " (com alterações não commitadas)"}
- protocolo v{c["versao"]}, estado **{c["estado"]}**, sha256 `{c["sha256"][:16]}…`, registrado `{(c["registrado"] or "—")[:16]}`
'''))
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "--color=no", "-p", "no:cacheprovider",
                    str(RAIZ / "artefato" / "tests")], capture_output=True, text=True)
print("testes da biblioteca:", r.stdout.strip().splitlines()[-1])
assert r.returncode == 0, "a biblioteca não passa nos próprios testes"

conn, BANCO = passos.banco_da_execucao(reg.exec_id)
SAIDA = Path(tempfile.mkdtemp()) if reg.ensaio else RAIZ / "resultados" / reg.exec_id
SAIDA.mkdir(parents=True, exist_ok=True)
reg.nota("banco da execução", banco=BANCO)
print("banco desta execução:", BANCO)
""")

# =============================================================================
md(r"""
## E1 — Qual é o problema?

Primeiro, a pista registrada **como o AIXM faria**: cada número publicado vira um campo guardado. Um BASELINE com a AOC de 2022 e um DELTA com o ADC de 2026, ambos afirmados pelo DECEA. Fica num run à parte (`aixm`): é o sistema que o TG critica.

**Previsão (E1.1, E1.2).** O diff entre as edições tem 12 campos em 4 grandezas, e nenhum traz a causa.
""")

code(r"""
RUN_F = al.novo_run(conn, F.AIRAC_2213, "aixm")
e2213, _ = reg.escrever(conn, RUN_F, "SBSJ-RWY-AIXM", "runway_forma", "BASELINE", corpo=F.FORMA_AIRAC_2213,
                        asserted_by="DECEA", reason="AOC AIRAC AMDT 2213A1")
passos.avancar_ate(conn, RUN_F, F.AIRAC_2604)
antes, depois = al.ledger.achatar(F.FORMA_AIRAC_2213), al.ledger.achatar(F.FORMA_AIRAC_2604)
e2604, _ = reg.escrever(conn, RUN_F, "SBSJ-RWY-AIXM", "runway_forma", "DELTA",
                        alteracoes={p: v for p, v in depois.items() if antes[p] != v},
                        asserted_by="DECEA", reason="ADC AIRAC AMDT 2604A1")

D = al.diff(conn, RUN_F, e2213, e2604)
display(Markdown("| campo | AIRAC 2213 | AIRAC 2604 |\n|---|---|---|\n" +
                 "\n".join(f"| `{p}` | {a} | {b} |" for _, p, a, b in D)))
""")

code(r"""
grandezas = {p.split(".")[0] for _, p, _, _ in D}
reg.condicao("E1.1", len(D) == 12 and grandezas == {"pista", "swy", "faixa", "distancias"},
             f"{len(D)} campos em {sorted(grandezas)}")
env = al.envelope(conn, e2604)
reg.condicao("E1.2", env["caused_by"] is None, f"caused_by = {env['caused_by']}; reason = {env['reason']!r}")
""")

md(r"""
**Leitura.** Uma única mudança física (a pista) aparece como sete números editados separadamente, porque TORA, TODA, ASDA e LDA estão guardados em vez de calculados. E o registro diz quem publicou, não por que mudou.
""")

# =============================================================================
md(r"""
## E2 — O número se refaz a partir das premissas?

Agora o SBSJ no modelo proposto, num run próprio (`sbsj`). Entram só **premissas**: as coordenadas das duas cabeceiras (AD 2.12), as larguras e a SWY. Toda posição se apoia nas cabeceiras: a pista vai "de THR16 até THR34"; o número 2675 não é escrito em lugar nenhum.

| Papel | Dado | Fonte |
|---|---|---|
| premissa | coordenadas e elevações das cabeceiras | AD 2.12 |
| premissa | largura da pista, dimensões da SWY | AD 2.12 |
| norma | variação magnética; regra das distâncias declaradas | ADC; Anexo 14 / RBAC 154 |
| derivado | comprimento, azimutes, rumos, TORA/TODA/ASDA/LDA | calculado, nunca escrito |
""")

code(r"""
RUN = al.novo_run(conn, F.EAIP_20_2026, "sbsj")
REF1 = al.publicar_referencial(conn, passos.corpo_referencial())
CORPO1 = al.carregar_referencial(conn, REF1)
E = reg.escrever

E(conn, RUN, "SBSJ", "airport", "BASELINE", asserted_by="DECEA", reason="eAIP 20-2026 (AD 2); ADC AIRAC 2604A1",
  corpo={"adc": {"icao": "SBSJ"}, "referencial": {"ref_id": REF1},
         "norma": {"variacao_magnetica_graus": F.VARIACAO_LESTE,
                   "regra_distancias": "TORA = pista; TODA = TORA + CWY; ASDA = TORA + SWY; LDA = pista − deslocamento"}})
E(conn, RUN, "SBSJ-RWY", "runway", "BASELINE", asserted_by="DECEA", reason="eAIP 20-2026, AD 2.12",
  corpo={"adc": {"designacao": "16/34", "direcoes": {"inicio": "16", "fim": "34"}, "superficie": F.SUPERFICIE},
         "geometria": {"primitivos": {"pista": {"tipo": "retangulo", "inicio": s("THR16"), "fim": s("THR34"),
                                                "largura": F.LARGURA_RWY}}}})
for d, ref in (("16", "THR16"), ("34", "THR34")):
    E(conn, RUN, f"SBSJ-THR{d}", "runway_direction", "BASELINE", asserted_by="DECEA", reason="eAIP 20-2026, AD 2.12",
      corpo={"adc": {"designador": d, "pista": "SBSJ-RWY"},
             "geometria": {"primitivos": {"thr": {"tipo": "ponto", "seed": s(ref)}}}})
E(conn, RUN, "SBSJ-SWY", "protect_area", "BASELINE", asserted_by="DECEA", reason="eAIP 20-2026, AD 2.12",
  corpo={"adc": {"papel": "swy", "aplica_a": {"pista": "SBSJ-RWY", "direcao": "16"}},
         "geometria": {"primitivos": {"swy": {"tipo": "retangulo", "inicio": s("THR34"),
                                              "fim": s("THR34", -F.SWY["comprimento"]), "largura": F.SWY["largura"]}}}})
T_A = al.agora(conn, RUN)
print("premissas escritas; instante t_a =", T_A)
""")

md(r"""
A geometria abaixo **não está no banco**: é gerada na leitura a partir das seeds e do referencial (demonstração; o motor de geometria não é testado nesta versão).
""")

code(r"""
ADC_A = adc.projetar(conn, RUN)
fig, ax = plt.subplots(figsize=(8, 4))
for el in ADC_A["elementos"]:
    if el["forma"] is not None:
        x, y = el["forma"].exterior.xy
        ax.fill(x, y, alpha=0.5, label=el["feature_id"])
    for p in el["nos"]:
        ax.plot(p.x, p.y, "k^")
ax.set_aspect("equal"); ax.set_xlabel("leste (m)"); ax.set_ylabel("norte (m)"); ax.legend(loc="lower left")
ax.set_title("Pista e SWY geradas das premissas (plano local em THR16)")
fig.savefig(SAIDA / "e2_geometria.png", dpi=150, bbox_inches="tight"); plt.show()
""")

md(r"""
### Os derivados batem com o AIP? (H2.01 a H2.14)

Comprimento e azimutes saem da geodésica entre as cabeceiras (GRS80). O rumo magnético soma a variação. As distâncias declaradas saem da regra. As margens vêm da precisão com que o AIP publica cada número (protocolo v0.4). Por fim, H2.14 procura no banco algum derivado guardado: não pode haver nenhum.
""")

code(r"""
L1 = derivacoes.comprimento(CORPO1, "RWY_16_34")
AZ1 = derivacoes.azimutes(CORPO1, "RWY_16_34")
DD1 = al.distancias_declaradas(conn, RUN)
reg.numerico("H2.01", L1)
reg.numerico("H2.02", AZ1["THR16"], angular=True)
reg.numerico("H2.03", AZ1["THR34"], angular=True)
reg.numerico("H2.04", derivacoes.rumo_magnetico(AZ1["THR16"], F.VARIACAO_LESTE), angular=True)
reg.numerico("H2.05", derivacoes.rumo_magnetico(AZ1["THR34"], F.VARIACAO_LESTE), angular=True)
for vid, (d, k) in {"H2.06": ("16", "TORA"), "H2.07": ("16", "TODA"), "H2.08": ("16", "ASDA"), "H2.09": ("16", "LDA"),
                    "H2.10": ("34", "TORA"), "H2.11": ("34", "TODA"), "H2.12": ("34", "ASDA"), "H2.13": ("34", "LDA")}.items():
    reg.numerico(vid, DD1[d][k])
n = passos.contar(conn, r'''SELECT count(*) FROM event_field f JOIN event e USING (event_id)
    WHERE e.run_id = %s AND (regexp_replace(f.path, '^.*\.', '') IN ('tora','toda','asda','lda','azimute','azimuth','rumo','bearing')
          OR (e.feature_type = 'runway' AND regexp_replace(f.path, '^.*\.', '') IN ('comprimento','length')))''', RUN)
reg.igual("H2.14", n, 0, "linhas de derivado no banco")
""")

md(r"""
### A cabeceira 34 é remedida (H2.15 a H2.19)

Cenário fixado no protocolo: a THR34 é remedida (≈1 m de deslocamento). O levantamento entra como evento próprio, e a troca de referencial aponta para ele em `caused_by`. **Previsão:** nenhuma seed é reescrita; a pista e a SWY acompanham a cabeceira nova sozinhas; e as posições coincidem com o gabarito geodésico independente.
""")

code(r"""
al.avancar(conn, RUN, dias=30)
MARCO = passos.maior_event_id(conn, RUN)
LEV, _ = E(conn, RUN, "SBSJ-LEV-THR34", "survey", "BASELINE",
           asserted_by="Heyder (cenário simulado do protocolo)", reason="remedição da cabeceira 34",
           corpo={"levantamento": {"ponto": "THR34", "lat_publicada": F.THR34_REMEDIDA["lat"],
                                   "lon_publicada": F.THR34_REMEDIDA["lon"]}})
REF2 = al.publicar_referencial(conn, passos.corpo_referencial(F.THR34_REMEDIDA, "levantamento SBSJ-LEV-THR34"))
CORPO2 = al.carregar_referencial(conn, REF2)
TROCA, _ = E(conn, RUN, "SBSJ", "airport", "DELTA", alteracoes={"referencial.ref_id": REF2},
             asserted_by="DECEA", reason="troca de referencial: THR34 remedida", caused_by=LEV)
T_B = al.agora(conn, RUN)
DEPOIS = passos.depois_de(conn, RUN, MARCO)
display(Markdown("| evento | feature | tipo | campos escritos |\n|---|---|---|---|\n" +
                 "\n".join(f"| {e} | {f} | {et} | {', '.join(p)} |" for e, f, _, et, p in DEPOIS)))
""")

code(r"""
esperado = [("SBSJ-LEV-THR34", "BASELINE"), ("SBSJ", "DELTA", ["referencial.ref_id"])]
observado = [(f, et) if f != "SBSJ" else (f, et, list(p)) for _, f, _, et, p in DEPOIS]
reg.igual("H2.15", observado + [al.envelope(conn, TROCA)["caused_by"] == LEV], esperado + [True],
          "predição ajustada na v0.5: levantamento + DELTA no airport com caused_by")
com_seed = {"runway", "runway_direction", "protect_area", "taxiway", "apron"}
reg.igual("H2.16", sum(1 for _, _, t, _, _ in DEPOIS if t in com_seed), 0, "eventos em features com seed")
reg.igual("H2.17", sum(1 for *_, paths in DEPOIS for p in paths
                       if p.split(".")[-1] in ("comprimento", "length", "tora", "toda", "asda", "lda")), 0,
          "campos de comprimento ou distância escritos")

def latlon(corpo, nome):
    r = corpo["referentes"][nome]
    return (r["lat"], r["lon"])

pior = 0.0
for corpo in (CORPO1, CORPO2):
    res = Resolvedor(corpo)
    for v in reg.v04["H2"]["ato4"]["vertices_verificados"]:
        ref, outro = v["referente"], ("THR34" if v["referente"] == "THR16" else "THR16")
        lat, lon, _ = res.seed(s(ref, v["s"], v["o"]))
        glat, glon = gab.resolver(latlon(corpo, ref), latlon(corpo, outro), v["s"], v["o"])
        # pontos idênticos ao último bit: distância zero (a inversa de Vincenty não trata esse caso)
        d = 0.0 if (lat, lon) == (glat, glon) else gab.inversa(lat, lon, glat, glon)[0]
        pior = max(pior, d)
reg.limite("H2.18", pior, reg.idx["H2.18"]["tolerancia_m"], "maior distância biblioteca × gabarito, ref v1 e v2")

L2 = derivacoes.comprimento(CORPO2, "RWY_16_34")
AZ2 = derivacoes.azimutes(CORPO2, "RWY_16_34")
gL, gaz16, gaz34 = gab.inversa(*latlon(CORPO2, "THR16"), *latlon(CORPO2, "THR34"))
dL = abs(L2 - gL)
daz = max(abs(AZ2["THR16"] - gaz16), abs(AZ2["THR34"] - gaz34))
tol_az = 0.0005 / L2 * 180 / 3.141592653589793
reg.condicao("H2.19", dL <= 5e-4 and daz <= tol_az, f"ΔL = {dL:.1e} m; Δaz = {daz:.1e}° (limite {tol_az:.1e}°)")
DD2 = al.distancias_declaradas(conn, RUN)
print(f"comprimento: {L1:.3f} m → {L2:.3f} m, sem nenhum número digitado")
""")

# =============================================================================
md(r"""
## E3 — Como estava em *t*, quem afirmou e por quê?

As três perguntas do auditor, respondidas só lendo o banco:

1. **estado em *t***: em *t_a* (antes da remedição) vale o referencial antigo e o comprimento antigo; agora, os novos;
2. **ciclo de vida**: uma interdição temporária de 300 m a partir da THR 34 entra em *t₄* e sai em *t₅* (BASELINE e VOID, sem um tipo especial de "temporário");
3. **quem e por quê**: o envelope da troca de referencial dá autor, motivo e causa;
4. **o número está certo**: as distâncias re-derivadas em *t_a* são exatamente as que valiam em *t_a*.
""")

code(r"""
al.avancar(conn, RUN, dias=10)
T4 = al.agora(conn, RUN)
DONO = {"owner_ref": "SBSJ-RWY"}
B4, _ = E(conn, RUN, "SBSJ-RES-0001", "restriction", "BASELINE", asserted_by="operador SBSJ", reason="NOTAM (simulado)",
          corpo={"adc": {"texto": "RWY 16/34: 300 m a partir da THR 34 interditados para obra",
                         "trecho": {"de": s("THR34"), "ate": s("THR34", 300)}}}, **DONO)
al.avancar(conn, RUN, dias=3)
T5 = al.agora(conn, RUN)
V5, _ = E(conn, RUN, "SBSJ-RES-0001", "restriction", "VOID", asserted_by="operador SBSJ",
          reason="obra concluída", **DONO)
al.avancar(conn, RUN, dias=1)

lim = al.relogio.limite
ref_a, corpo_a = al.referencial_vigente(conn, RUN, lim(T_A))
ref_b, corpo_b = al.referencial_vigente(conn, RUN, lim(al.agora(conn, RUN)))
La, Lb = derivacoes.comprimento(corpo_a, "RWY_16_34"), derivacoes.comprimento(corpo_b, "RWY_16_34")
reg.condicao("E3.1", ref_a == REF1 and ref_b == REF2 and La == L1 and Lb == L2,
             f"t_a: ref {ref_a[:8]}…, {La:.3f} m · agora: ref {ref_b[:8]}…, {Lb:.3f} m")

def interditada(t):
    return any(f == "SBSJ-RES-0001" for f, _ in al.features(conn, RUN, t, tipos=["restriction"]))

dentro = [T4, T4 + timedelta(days=1.5), passos.um_segundo_antes(T5)]
fora = [passos.um_segundo_antes(T4), T5, al.agora(conn, RUN)]
reg.condicao("E3.2", all(map(interditada, dentro)) and not any(map(interditada, fora)),
             f"dentro: {[interditada(t) for t in dentro]} · fora: {[interditada(t) for t in fora]}")

seg = al.ciclos(conn, RUN, "SBSJ-RES-0001")
reg.condicao("E3.3", seg == [(B4, "BASELINE", 1), (V5, "VOID", 1)]
             and al.instante(B4) == T4 and al.instante(V5) == T5,
             f"{[(t, c) for _, t, c in seg]} em {al.instante(B4):%d/%m} e {al.instante(V5):%d/%m}")

env_t, env_l = al.envelope(conn, TROCA), al.envelope(conn, LEV)
reg.condicao("E3.4", env_t["asserted_by"] == "DECEA" and env_t["caused_by"] == LEV and bool(env_t["reason"])
             and bool(env_l["asserted_by"]),
             f"troca: {env_t['asserted_by']}, '{env_t['reason']}', causa = {env_l['feature_id']} ({env_l['asserted_by']})")

reg.condicao("E3.5", al.distancias_declaradas(conn, RUN, T_A) == DD1, "distâncias em t_a re-derivadas = as do E2")

TRILHA = al.diff(conn, RUN, T_A, al.agora(conn, RUN))
display(Markdown("**Trilha de auditoria entre t_a e agora**\n\n| feature | campo | antes | depois |\n|---|---|---|---|\n" +
                 "\n".join(f"| {f} | `{p}` | {str(a)[:20]} | {str(b)[:20]} |" for f, p, a, b in TRILHA)))
""")

# =============================================================================
md(r"""
## E4 — Alguém consegue adulterar sem ser visto?

O PANS-AIM (2.2.1) recomenda garantir a integridade com criptografia, como funções de hash. Aqui o atacante tem acesso direto ao banco e não passa pela biblioteca. Cada ataque roda numa **cópia** do banco; antes, a cabeça da cadeia é anotada fora do banco (a âncora).

**Previsões.** Alterar, apagar ou inserir no meio: `verificar_cadeia` acusa o evento previsto. Reescrever tudo de *k* até o fim recalculando os hashes: o banco sozinho não percebe (previsão negativa); só a âncora pega.
""")

code(r"""
ANCORA = al.cabeca(conn, RUN)
reg.nota("âncora antes dos ataques", cabeca=ANCORA)
K, K1, CAB = ataques.escolher_k(conn, RUN)
print("âncora:", ANCORA[1][:16], "… | k =", K)

PLANO = {"E4.1": ("H3.01", [K], True), "E4.2": ("H3.05", [K1], True),
         "E4.3": ("H3.06", [K1], True), "E4.4": ("H3.09", [], True)}
LINHAS = []
conn.close()                                   # o Postgres só copia um banco sem conexões abertas
for vid, (ataque, vc_previsto, ancora_prevista) in PLANO.items():
    copia = f"{BANCO}_ataque"
    c2 = passos.copia_do_banco(BANCO, copia)
    ataques.atacar(c2, RUN, ataque, K, CAB)
    vc, com_ancora = ataques.detectar(c2, RUN, ANCORA)
    c2.close(); passos.apagar_banco(copia)
    LINHAS.append((vid, ataques.ATAQUES[ataque], vc, com_ancora))
    reg.igual(vid, [vc, com_ancora], [vc_previsto, ancora_prevista], ataques.ATAQUES[ataque])
conn = passos.reconectar(BANCO)
assert al.verificar_cadeia(conn, RUN) == [] and tuple(al.cabeca(conn, RUN)) == tuple(ANCORA)   # original intacto
display(Markdown("| | ataque | verificar_cadeia | com âncora |\n|---|---|---|---|\n" +
                 "\n".join(f"| {v} | {a} | {vc or 'não percebe'} | {'detecta' if ca else 'não detecta'} |"
                           for v, a, vc, ca in LINHAS)))
""")

md(r"""
**Limites declarados.** O banco registra quem afirmou, mas não prova: `asserted_by` é texto, não assinatura (repúdio fica como trabalho futuro). E nenhum sistema torna uma medição verdadeira: se a fonte mede errado, o ledger só atribui o erro — como as edições que divergem no E1.
""")

# =============================================================================
md(r"""
## E5 — Dois produtos podem divergir? A prova é verificável por terceiros?

O PANS-AIM (2.1.3.2) exige consistência entre os produtos de informação aeronáutica. No E1, os produtos reais divergem. Aqui, dois produtos saem do mesmo ledger:

- **P1**, a tabela do AIP (comprimento, azimutes, distâncias declaradas);
- **P2**, o conteúdo do ADC (a lente ADC).

Os dois usam a mesma derivação, então a consistência é **por construção** — é isso que se quer mostrar, e o contraste é o E1. A parte que não é óbvia vem depois: um **verificador independente**, escrito sem importar a biblioteca, confere a cadeia e o comprimento só a partir do JSON exportado.
""")

code(r"""
def p1(t):
    _, corpo = al.referencial_vigente(conn, RUN, lim(t))
    return {"comprimento": derivacoes.comprimento(corpo, "RWY_16_34"), "distancias": al.distancias_declaradas(conn, RUN, t)}

def p2(t):
    return {"distancias": adc.projetar(conn, RUN, t)["distancias"]}

AGORA = al.agora(conn, RUN)
P1a, P2a, P1b, P2b = p1(T_A), p2(T_A), p1(AGORA), p2(AGORA)
reg.condicao("E5.1", P1a["distancias"] == P2a["distancias"] and P1b["distancias"] == P2b["distancias"],
             "P1 = P2 em t_a e agora")
reg.condicao("E5.2", P1a["distancias"] != P1b["distancias"] and P2a["distancias"] != P2b["distancias"]
             and P1b["distancias"] == P2b["distancias"],
             f"ASDA 16: {P1a['distancias']['16']['ASDA']:.3f} → {P1b['distancias']['16']['ASDA']:.3f} m nos dois")

EXPORT = passos.exportar(conn, RUN, SAIDA / "export_sbsj.json")
dados = json.loads(Path(EXPORT).read_text())
r = vi.verificar(dados)
cab = list(al.cabeca(conn, RUN))
reg.condicao("E5.3", r["integra"] and list(r["cabeca"]) == cab,
             f"íntegra = {r['integra']}; cabeça {r['cabeca'][1][:16] if r['cabeca'] else None}… = biblioteca {cab[1][:16]}…")
Lv = vi.comprimento(dados)
reg.limite("E5.4", abs(Lv - P1b["comprimento"]), reg.idx["E5.4"]["tolerancia_m"],
           f"verificador {Lv:.4f} m · biblioteca {P1b['comprimento']:.4f} m")

alvo = next(e for e in dados["eventos"] if e["feature_id"] == "SBSJ-RWY")
for c_ in alvo["campos"]:
    if c_["path"].endswith("pista.largura"):
        c_["next"] = c_["next"] + 1
r2 = vi.verificar(dados)
reg.condicao("E5.5", r2["primeiro_divergente"] == alvo["event_id"],
             f"largura da pista alterada no JSON → verificador acusa o evento {r2['primeiro_divergente']}")
""")

# =============================================================================
md(r"""
## Fechamento
""")

code(r"""
display(Markdown(reg.tabela()))
resumo = reg.resumo()
display(Markdown("\n".join(f"- **{e}**: {d['PASSOU']} passaram, {d['FALHOU']} falharam" for e, d in resumo.items())))
if not reg.ensaio:
    (SAIDA / "vereditos.json").write_text(json.dumps(reg.vereditos, ensure_ascii=False, indent=1, default=str))
    print("vereditos gravados em", SAIDA / "vereditos.json")
else:
    print("modo ensaio: nada foi gravado no registro de execuções")
""")


nb = nbf.v4.new_notebook()
nb["cells"] = CELULAS
nb["metadata"]["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
destino = Path(__file__).with_name("experimentos.ipynb")
nbf.write(nb, destino)
print("gerado", destino, "com", len(CELULAS), "células")
