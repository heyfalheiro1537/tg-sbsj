"""Figuras do notebook. Toda figura sai do ledger (via lente ADC) ou do oráculo; nenhuma é desenhada à mão."""
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon

CORES = {"runway": "#222222", "protect_area": "#d9c79a", "taxiway": "#9aa5b1", "apron": "#b9c2cc",
         "pavement": "#cfd5db", "restriction": "#c0392b", "runway_direction": "#2c7be5",
         "aerodrome_point": "#2c7be5", "navaid": "#2c7be5"}
ORDEM = ["protect_area", "pavement", "apron", "taxiway", "runway", "restriction"]


def _partes(g):
    if g is None:
        return []
    return list(g.geoms) if hasattr(g, "geoms") else [g]


def _poligono(ax, g, cor, alfa=1.0, borda=None, lw=0.4, hachura=None, z=1):
    for p in _partes(g):
        if p.geom_type != "Polygon":
            continue
        ax.add_patch(MplPolygon(list(p.exterior.coords), closed=True, facecolor=cor, alpha=alfa,
                                edgecolor=borda or cor, lw=lw, hatch=hachura, zorder=z))
        for furo in p.interiors:
            ax.add_patch(MplPolygon(list(furo.coords), closed=True, facecolor="white", edgecolor=borda or cor,
                                    lw=lw, zorder=z + 0.1))


def adc(conteudo, titulo, edicao, ax=None, mostrar_tabela=True):
    """Desenha o conteúdo do ADC projetado do ledger, em coordenadas do plano local."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 10))
    els = sorted(conteudo["elementos"], key=lambda e: ORDEM.index(e["tipo"]) if e["tipo"] in ORDEM else 99)
    for e in els:
        tp = e["tipo"]
        if tp == "protect_area" and e["adc"].get("papel") == "faixa":
            _poligono(ax, e["forma"], "#f3ecd7", 0.9, "#a08a4f", 0.6, z=0)
        elif tp == "protect_area":
            _poligono(ax, e["forma"], "#e8e8e8", 1, "#444444", 0.6, hachura="////", z=2)
        elif tp == "restriction":
            _poligono(ax, e["forma"], CORES[tp], 0.55, CORES[tp], 1.0, hachura="xx", z=5)
        else:
            _poligono(ax, e["forma"], CORES.get(tp, "#cccccc"), 1, z=3 if tp == "runway" else 1)
        for n in e["nos"]:
            ax.plot(n.x, n.y, marker="o", ms=5, mfc="white", mec=CORES.get(tp, "#2c7be5"), mew=1.4, zorder=6)
            rot = e["adc"].get("designador") or e["adc"].get("designacao") or ""
            ax.annotate(rot, (n.x, n.y), xytext=(4, 4), textcoords="offset points", fontsize=7, zorder=6)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_xlabel("leste (m) — plano local com origem em THR16")
    ax.set_ylabel("norte (m)")
    ax.set_title(titulo, fontsize=11)
    ax.grid(True, lw=0.3, alpha=0.4)
    if mostrar_tabela and "pendente" not in conteudo["distancias"]:
        linhas = ["RWY   TORA     TODA     ASDA     LDA"]
        for d, v in sorted(conteudo["distancias"].items()):
            linhas.append(f"{d:<5} {v['TORA']:7.1f}  {v['TODA']:7.1f}  {v['ASDA']:7.1f}  {v['LDA']:7.1f}")
        ax.text(0.02, 0.02, "\n".join(linhas), transform=ax.transAxes, family="monospace", fontsize=7.5,
                va="bottom", bbox=dict(facecolor="white", edgecolor="#999999", alpha=0.95))
    ax.text(0.99, 0.005, f"Gerado do ledger para pesquisa; não substitui a publicação oficial. Fonte: {edicao}.",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6.5, color="#555555")
    return ax


def h1(unidades, envoltorias, ax=None, titulo="H1 — contornos do ADC (preto) e envoltórias geradas (azul)"):
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 10))
    for u in unidades:
        env = envoltorias.get(u["id"])
        _poligono(ax, env, "#2c7be5", 0.25, "#2c7be5", 0.6, z=1)
        for p in _partes(u["poligono"]):
            xs, ys = p.exterior.xy
            ax.plot(xs, ys, color="black", lw=0.5, zorder=2)
    ax.set_aspect("equal")
    ax.autoscale_view()
    ax.set_title(titulo, fontsize=11)
    ax.set_xlabel("leste (m)")
    ax.set_ylabel("norte (m)")
    ax.grid(True, lw=0.3, alpha=0.4)
    return ax
