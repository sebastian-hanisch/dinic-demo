"""Plotly-Abbildungen: Niveaugraph mit blockierendem Fluss, Fluss mit Kapazitäten, Schnitt (Beweis), Phasen, Verteilungen, Aufwand, Zeigerliste, Einheitsnetze.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Kanten haben über unsichtbare Marker einen Hover-Text
(Plotly-Linien reagieren nur an ihren Stützpunkten)."""

from math import atan2, degrees, hypot

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dn_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _layout(fig, net, height):
    xs = [p[0] for p in net.pos]
    ys = [p[1] for p in net.pos]
    pad = 9
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _curve(p0, p1, bulge, steps=8):
    """Punkte von p0 nach p1; mit `bulge` > 0 als flacher Bogen nach rechts (so trennen sich Vorwärts- und Rückkante). Dazu der Pfeilwinkel bei 65 %."""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    length = hypot(dx, dy) or 1.0
    cx, cy = (x0 + x1) / 2 + bulge * length * dy / length, (y0 + y1) / 2 - bulge * length * dx / length
    ts = [k / steps for k in range(steps + 1)]
    xs = [(1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1 for t in ts]
    ys = [(1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1 for t in ts]
    t = 0.65
    tx = 2 * (1 - t) * (cx - x0) + 2 * t * (x1 - cx)
    ty = 2 * (1 - t) * (cy - y0) + 2 * t * (y1 - cy)
    ax = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1
    ay = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1
    return xs, ys, (ax, ay, degrees(atan2(tx, ty))), (xs[steps // 2], ys[steps // 2])


def _segments(curves):
    x, y = [], []
    for xs, ys, _, _ in curves:
        x += xs + [None]
        y += ys + [None]
    return x, y


def _lines(fig, curves, color, width, name, dash=None, showlegend=True):
    if not curves:
        return
    x, y = _segments(curves)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=width, dash=dash), hoverinfo="skip", name=name, showlegend=showlegend))


def _arrows(fig, curves, color, size=9):
    if not curves:
        return
    fig.add_trace(go.Scatter(x=[c[2][0] for c in curves], y=[c[2][1] for c in curves], mode="markers", hoverinfo="skip", showlegend=False,
                             marker=dict(symbol="arrow", size=size, color=color, angle=[c[2][2] for c in curves])))


def _hover_points(fig, net, entries):
    """Unsichtbare Marker entlang jeder Kante, damit der Hover-Text überall auf der Kante erscheint. entries: [(Kurve, Text)]"""
    x, y, text = [], [], []
    for curve, label in entries:
        xs, ys = curve[0], curve[1]
        for k in range(1, len(xs) - 1):
            x.append(xs[k]); y.append(ys[k]); text.append(label)
    if x:
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(size=9, opacity=0), hovertext=text, hoverinfo="text", showlegend=False))


def _labels(fig, points):
    """points: [(x, y, Text)] - als Annotationen mit heller Hinterlegung, damit sie Kanten, Pfeile und Knotenbeschriftungen nicht unlesbar machen."""
    for x, y, text in points:
        fig.add_annotation(x=x, y=y, text=text, showarrow=False, xanchor="left", font=dict(size=11, color="#111"), bgcolor="rgba(255,255,255,0.88)", borderpad=1)


def _arc_name(net, i):
    u, v = net.arcs[i][0], net.arcs[i][1]
    return f"{net.names[u]} → {net.names[v]}"


def _nodes(fig, net, reach=None):
    """Knoten: S und T als Quadrate, alle anderen als Kreise; mit `reach` grün (von S erreichbar) oder grau eingefärbt."""
    text_pos = {0: "top center", 1: "bottom center"}
    for kind, idx in (("Quelle/Senke", [net.s, net.t]), ("Knoten", [v for v in range(net.n) if v not in (net.s, net.t)])):
        colors = [C.COLORS["node"] if reach is None else (C.COLORS["reach"] if reach[v] else C.COLORS["unreach"]) for v in idx]
        pos = [text_pos.get(v, "top center" if net.pos[v][1] > 70 else ("bottom center" if net.pos[v][1] < 30 else "middle left")) for v in idx]
        if net.logistic and kind == "Knoten":
            pos = ["top center" if net.names[v].startswith("Werk") else "bottom center" if net.names[v].startswith("Filiale") else "middle left" for v in idx]
        fig.add_trace(go.Scatter(
            x=[net.pos[v][0] for v in idx], y=[net.pos[v][1] for v in idx], mode="markers+text", showlegend=False,
            text=[net.labels[v] for v in idx], textposition=pos, hovertext=[net.names[v] for v in idx], hoverinfo="text",
            marker=dict(symbol="square" if kind == "Quelle/Senke" else "circle", size=13 if kind == "Quelle/Senke" else 10, color=colors, line=dict(width=1.5, color="#333"))))


def _wscale(net):
    return max(c for _, _, c, _, _ in net.arcs)


def _width(amount, top, lo=1.0, hi=6.0):
    return lo + (hi - lo) * amount / top if top else lo


def build_flow(net, flow, path=None, cut=None, reach=None, height=460):
    """Fluss je Kante: Breite ~ Fluss, dunkelblau = voll ausgelastet, blass = ungenutzt. `path`: Kanten (Netzkanten-Indizes) der letzten Augmentierung
    (grün beschriftet mit Fluss/Kapazität); `cut`: Schnittkanten in Rot mit Kapazität; `reach`: von S erreichbare Knoten in Grün."""
    fig = go.Figure()
    top = _wscale(net)
    cut_set, path_set = set(cut or ()), set(path or ())
    groups = {"idle": [], "part": [], "full": []}
    hover, labels = [], []
    special = {"cut": [], "path": []}
    for i, (u, v, cap, cost, _) in enumerate(net.arcs):
        curve = _curve(net.pos[u], net.pos[v], 0.0)
        hover.append((curve, f"{_arc_name(net, i)}: Fluss {flow[i]} von {cap}, Kosten {cost} je Einheit"))
        if i in cut_set:
            special["cut"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{cap}"))
        elif i in path_set:
            special["path"].append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{flow[i]}/{cap}"))
        else:
            groups["idle" if flow[i] == 0 else "full" if flow[i] == cap else "part"].append((curve, flow[i]))
    _lines(fig, [c for c, _ in groups["idle"]], C.COLORS["faint"], 1.2, "ungenutzt")
    for group, color in (("part", "rgba(31,119,180,0.85)"), ("full", "#0b3d91")):
        by_width = {}
        for c, f in groups[group]:
            by_width.setdefault(round(_width(f, top)), []).append(c)      # ganze Breiten: wenige Spuren statt einer je Kante
        for w, curves in by_width.items():
            _lines(fig, curves, color, w, group, showlegend=False)
    if groups["part"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="rgba(31,119,180,0.85)", width=4), name="Fluss (nicht voll)"))
    if groups["full"]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="#0b3d91", width=4), name="Fluss (Kante voll)"))
    _lines(fig, special["path"], C.COLORS["path"], 5, "Kante des letzten Weges")
    _lines(fig, special["cut"], C.COLORS["cut"], 5, "Schnittkante (voll, Kapazität beschriftet)")
    if net.m <= 60:
        _arrows(fig, [c for c, _ in groups["idle"]] + [c for c, _ in groups["part"]] + [c for c, _ in groups["full"]], "rgba(60,60,60,0.7)", 8)
    _arrows(fig, special["path"] + special["cut"], "rgba(30,30,30,0.9)", 11)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    _nodes(fig, net, reach)
    return _layout(fig, net, height)


def _node_text_positions(net, idx):
    if net.logistic:
        return ["top center" if (v == 0 or net.names[v].startswith("Werk")) else "bottom center" if (v == 1 or net.names[v].startswith("Filiale")) else "middle left" for v in idx]
    return ["top center" if net.pos[v][1] > 60 else "bottom center" for v in idx]


def build_levels(net, phase, stage, height=460):
    """Niveaugraph einer Phase: Knotenfarbe = Niveau (Entfernung von S), dunkle Kanten = Restkanten von Niveau k nach Niveau k+1, orange gestrichelt = Rückkante.
    `stage` = Zahl der schon gefundenen Wege der Phase: frühere Wege hellgrün, der aktuelle Weg dick grün mit seinem Engpass beschriftet, volle Kanten blass gepunktet,
    Sackgassen der Tiefensuche als violettes Kreuz."""
    fig = go.Figure()
    paths = phase.paths[:stage]
    cur = paths[-1] if paths else None
    flow = cur.flow_after if cur else phase.flow_before
    earlier = {e for p in paths[:-1] for e in p.arcs}
    cur_arcs = set(cur.arcs) if cur else set()
    dead = {v for p in paths for v in p.dead}
    if stage == len(phase.paths):
        dead |= set(phase.tail_dead)

    def rest(e):
        i = e // 2
        return net.arcs[i][2] - flow[i] if e % 2 == 0 else flow[i]

    alive, alive_back, full, mid, current, hover, labels = [], [], [], [], [], [], []
    for e in phase.level_arcs:
        i, forward = e // 2, e % 2 == 0
        u, v = net.arcs[i][0], net.arcs[i][1]
        a, b = (u, v) if forward else (v, u)
        curve = _curve(net.pos[a], net.pos[b], 0.0 if forward else 0.08)
        hover.append((curve, f"{net.names[a]} → {net.names[b]} (Niveau {phase.levels[a]} → {phase.levels[b]}): Rest {rest(e)}" + ("" if forward else " (Rückkante)")))
        if e in cur_arcs:
            current.append(curve)
            labels.append((curve[0][3] + 1.5, curve[1][3], f"{cur.bottleneck}"))
        elif e in earlier:
            mid.append(curve)
        elif rest(e) == 0:
            full.append(curve)
        else:
            (alive if forward else alive_back).append(curve)
    _lines(fig, full, C.COLORS["faint"], 1.2, "Kante voll (in dieser Phase gesperrt)", dash="dot")
    _lines(fig, alive, "rgba(40,70,110,0.9)", 2.2, "Niveaugraph (Restkapazität)")
    _lines(fig, alive_back, C.COLORS["back"], 2.2, "Niveaugraph über eine Rückkante", dash="dash")
    _lines(fig, mid, "rgba(44,160,44,0.45)", 3.5, "früherer Weg der Phase")
    _lines(fig, current, C.COLORS["path"], 5.5, "aktueller Weg")
    if net.m <= 80:
        _arrows(fig, alive + full, "rgba(40,70,110,0.8)", 8)
        _arrows(fig, alive_back, C.COLORS["back"], 8)
    _arrows(fig, mid + current, C.COLORS["path"], 11)
    _hover_points(fig, net, hover)
    _labels(fig, labels)
    top = phase.level
    on = [v for v in range(net.n) if phase.levels[v] >= 0]
    off = [v for v in range(net.n) if phase.levels[v] < 0]
    if off:
        fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in off], y=[net.pos[v][1] for v in off], mode="markers", showlegend=True, name="nicht im Niveaugraph",
                                 hovertext=[f"{net.names[v]}: nicht im Niveaugraph" for v in off], hoverinfo="text",
                                 marker=dict(symbol="circle-open", size=9, color=C.COLORS["unreach"], line=dict(width=1.5))))
    fig.add_trace(go.Scatter(
        x=[net.pos[v][0] for v in on], y=[net.pos[v][1] for v in on], mode="markers+text", showlegend=False,
        text=[net.labels[v] for v in on], textposition=_node_text_positions(net, on), hovertext=[f"{net.names[v]}: Niveau {phase.levels[v]}" for v in on], hoverinfo="text",
        marker=dict(symbol=["square" if v in (net.s, net.t) else "circle" for v in on], size=[13 if v in (net.s, net.t) else 10 for v in on], color=[phase.levels[v] for v in on],
                    colorscale=C.COLORS["levels"], cmin=0, cmax=top, showscale=True, line=dict(width=1.5, color="#333"),
                    colorbar=dict(title=dict(text="Niveau", side="top"), orientation="h", thickness=9, len=0.6, x=0.5, xanchor="center", y=-0.02, yanchor="top",
                                  tickmode="linear", tick0=0, dtick=1 if top <= 6 else 2))))
    if dead:
        d = sorted(dead)
        fig.add_trace(go.Scatter(x=[net.pos[v][0] for v in d], y=[net.pos[v][1] for v in d], mode="markers", name="Sackgasse der Tiefensuche", hovertext=[f"{net.names[v]}: Sackgasse" for v in d],
                                 hoverinfo="text", marker=dict(symbol="x", size=13, color=C.COLORS["dead"], line=dict(width=2))))
    fig = _layout(fig, net, height)
    fig.update_layout(margin=dict(l=10, r=10, t=10, b=90), legend=dict(orientation="h", y=-0.3))         # Platz für die waagerechte Farbskala unter dem Netz
    return fig


def build_phase_bars(res, height=300):
    """Durchsuchte Kanten je Phase (Breitensuche und Tiefensuche gestapelt), dazu die Zahl der Wege je Phase; ganz rechts die letzte, gescheiterte Breitensuche."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    labels = [f"Phase {k + 1}<br>Niveau {ph.level}" for k, ph in enumerate(res.phases)] + ["Beweis"]
    fig.add_trace(go.Bar(x=labels, y=[ph.bfs_scanned for ph in res.phases] + [res.final_scanned], name="Breitensuche", marker_color="#1f77b4", opacity=0.75), secondary_y=False)
    fig.add_trace(go.Bar(x=labels, y=[ph.dfs_scanned for ph in res.phases] + [0], name="Tiefensuche", marker_color="#ff7f0e", opacity=0.75), secondary_y=False)
    fig.add_trace(go.Scatter(x=labels, y=[len(ph.paths) for ph in res.phases] + [0], mode="lines+markers", name="Wege", line=dict(color=C.COLORS["path"])), secondary_y=True)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title="durchsuchte Kanten", secondary_y=False, rangemode="tozero")
    fig.update_yaxes(title="Wege", secondary_y=True, rangemode="tozero", showgrid=False)
    return _base(fig, height)


def build_phase_hist(phases, rounds, current=None, height=300):
    """Phasen von Dinic und Wege von Edmonds-Karp über die Netze, übereinandergelegt."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=phases, xbins=dict(start=-0.5, size=1), name="Phasen (Dinic)", marker_color="#2ca02c", opacity=0.7))
    fig.add_trace(go.Histogram(x=rounds, xbins=dict(start=-0.5, size=1), name="Wege (Edmonds-Karp)", marker_color="#1f77b4", opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Phasen bzw. Wege bis zum Ende", dtick=1)
    fig.update_yaxes(title="Netze")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.35), height=height + 50, margin=dict(l=10, r=10, t=30 if current is not None else 10, b=10))
    return fig


def build_scaling(rows, height=340):
    """Durchsuchte Kanten gegen die Kantenzahl (doppelt logarithmisch): Dinic, Dinic ohne Zeigerliste, Edmonds-Karp; dazu die Kantenzahl selbst."""
    fig = go.Figure()
    m = [r["m"] for r in rows]
    for key, label, color, dash in (("dinic", "Dinic", "#2ca02c", "solid"), ("nopointer", "Dinic ohne Zeigerliste", "#9467bd", "dot"), ("ek", "Edmonds-Karp", "#1f77b4", "solid")):
        fig.add_trace(go.Scatter(x=m, y=[r[key] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash=dash)))
    fig.add_trace(go.Scatter(x=m, y=m, mode="lines", name="Kanten des Netzes", line=dict(color="#555", dash="dashdot")))
    fig.update_xaxes(title="Kanten des Netzes", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    return _base(fig, height)


def build_gain(rows, height=320):
    """Verhältnis der durchsuchten Kanten: Edmonds-Karp durch Dinic, und Dinic ohne Zeigerliste durch Dinic, je Netzgröße."""
    fig = go.Figure()
    n = [r["n"] for r in rows]
    fig.add_trace(go.Scatter(x=n, y=[r["ek"] / r["dinic"] for r in rows], mode="lines+markers", name="Edmonds-Karp ÷ Dinic", line=dict(color="#1f77b4")))
    fig.add_trace(go.Scatter(x=n, y=[r["nopointer"] / r["dinic"] for r in rows], mode="lines+markers", name="ohne Zeigerliste ÷ mit", line=dict(color="#9467bd")))
    fig.add_hline(y=1, line=dict(color="#555", dash="dot"))
    fig.update_xaxes(title="Knoten des Netzes", type="log")
    fig.update_yaxes(title="Faktor der durchsuchten Kanten", type="log")
    return _base(fig, height)


def build_unit(stair_rows, random_rows, height=340):
    """Phasen auf Einheitsnetzen gegen die Zahl der Fahrzeuge: Treppe (schlimmster Fall), Zufall, und die Hopcroft-Karp-Schranke 2·√n."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[r["n"] for r in stair_rows], y=[r["phases"] for r in stair_rows], mode="lines+markers", name="Treppe", line=dict(color=C.COLORS["cut"])))
    fig.add_trace(go.Scatter(x=[r["n"] for r in random_rows], y=[r["phases_mean"] for r in random_rows], mode="lines+markers", name="Zufall (Mittel)", line=dict(color="#2ca02c")))
    ns = sorted({r["n"] for r in stair_rows} | {r["n"] for r in random_rows})
    fig.add_trace(go.Scatter(x=ns, y=[2 * n ** 0.5 for n in ns], mode="lines", name="Schranke 2·√n", line=dict(color="#555", dash="dash")))
    fig.update_xaxes(title="Fahrzeuge = Aufträge", type="log")
    fig.update_yaxes(title="Phasen", type="log")
    return _base(fig, height)
