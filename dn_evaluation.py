"""Kennzahlen, Urteil, Bilderfolge und die Experimente der Demo (Verteilungen über feste Netze, Aufwand gegen Edmonds-Karp, Zeigerliste, Einheitsnetze).
Alles ganzzahlig gerechnet; Prozente entstehen erst bei der Ausgabe."""

from dataclasses import dataclass
from functools import lru_cache
from statistics import mean, median

import numpy as np

import dn_algorithm as dn
import dn_constants as C
import dn_edmonds_karp as ek
import dn_scenario as sc

K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT, K_DEMAND = sc.K_SUPPLY, sc.K_LANE_IN, sc.K_THROUGHPUT, sc.K_LANE_OUT, sc.K_DEMAND
STAGE_KINDS = (K_SUPPLY, K_LANE_IN, K_THROUGHPUT, K_LANE_OUT)


@dataclass(frozen=True)
class Analysis:
    net: sc.Net
    result: dn.Result
    edmonds_karp: ek.Result
    demand: int          # Gesamtnachfrage (nur beim Distributionsnetz, sonst 0)
    stage_caps: dict     # Art -> Kapazität der Schnitt-Kanten dieser Art (kleinster minimaler Schnitt)
    current_arc: bool


def _demand(net):
    return sum(c for _, _, c, _, kind in net.arcs if kind == K_DEMAND)


def _stage_caps(net, res):
    caps = {}
    for i in res.cut_arcs:
        kind = net.arcs[i][4]
        caps[kind] = caps.get(kind, 0) + net.arcs[i][2]
    return caps


def analyse(net, current_arc=True):
    res = dn.dinic(net, current_arc=current_arc)
    return Analysis(net, res, ek.max_flow(net, "bfs"), _demand(net) if net.logistic else 0, _stage_caps(net, res), current_arc)


def pct(numerator, denominator, digits=1):
    return round(100 * numerator / denominator, digits) if denominator else 0.0


def frames(res):
    """Bildfolge der Wiedergabe: je Phase Stufe 0 (Niveaugraph), dann ein Bild je Weg; am Ende der Beweis.
    Ein Bild ist (Phase, Stufe); das Endbild hat Phase = Zahl der Phasen und Stufe 0."""
    out = []
    for k, ph in enumerate(res.phases):
        out.append((k, 0))
        out.extend((k, t) for t in range(1, len(ph.paths) + 1))
    out.append((len(res.phases), 0))
    return out


def verdict(a):
    """(Stufe, Code, Daten): 'delivered' = alle Nachfrage gedeckt, 'bottleneck' = das Netz schafft weniger, 'disconnected' = gar nichts kommt an, 'teaching' = Lehrnetz."""
    res, net = a.result, a.net
    levels = [ph.level for ph in res.phases]
    paths = [p.length for ph in res.phases for p in ph.paths]
    data = {
        "value": res.value, "demand": a.demand, "share": pct(res.value, a.demand) if a.demand else None,
        "phases": len(res.phases), "levels": levels, "paths": res.n_paths, "paths_per_phase": [len(ph.paths) for ph in res.phases],
        "bfs_scanned": res.bfs_total, "dfs_scanned": res.dfs_total, "scanned": res.scanned_total, "ek_scanned": a.edmonds_karp.scanned_total, "ek_rounds": len(a.edmonds_karp.rounds),
        "cut_capacity": res.cut_capacity, "cut_arcs": len(res.cut_arcs), "unique_cut": res.unique_cut, "stage_caps": a.stage_caps,
        "back_paths": sum(1 for ph in res.phases for p in ph.paths if p.uses_back_arc), "path_max": max(paths, default=0),
        "dead": sum(len(p.dead) for ph in res.phases for p in ph.paths) + sum(len(ph.tail_dead) for ph in res.phases),
    }
    if not net.logistic:
        return "info", "teaching", data
    if res.value == 0:
        return "warning", "disconnected", data
    if res.value == a.demand:
        return "success", "delivered", data
    net_caps = {k: v for k, v in a.stage_caps.items() if k in STAGE_KINDS}
    data["dominant"] = max(net_caps, key=net_caps.get) if net_caps else None
    return "warning", "bottleneck", data


def _generate(p, d, s, density, spread, load, seed):
    return sc.generate(p, d, s, density, spread, load, seed)


@lru_cache(maxsize=256)
def _runs(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Je Netz Dinic mit und ohne Zeigerliste und Edmonds-Karp (ohne Flusszustände je Runde); von den Verteilungen gemeinsam genutzt."""
    out = []
    for seed in seeds:
        net = _generate(p, d, s, density, spread, load, seed)
        out.append((net, _demand(net), dn.dinic(net, keep_flows=False), dn.dinic(net, current_arc=False, keep_flows=False), ek.max_flow(net, "bfs", keep_flows=False)))
    return out


@lru_cache(maxsize=256)
def distribution(p, d, s, density, spread, load, seeds=C.DIST_SEEDS):
    """Über feste Netze: Phasen, Wege, durchsuchte Kanten (Dinic mit und ohne Zeigerliste, Edmonds-Karp), Gleichheit mit Edmonds-Karp, Schranke |V|-1."""
    keys = ("phases", "paths", "ek_rounds", "dinic", "nopointer", "ek", "bfs", "dfs")
    cols = {k: [] for k in keys}
    served, all_served, unique, ratio, growing, same_count, same_lengths, path_mean_ph = [], 0, [], [], [], [], [], []
    for net, demand, r, r2, e in _runs(p, d, s, density, spread, load, seeds):
        for k, v in zip(keys, (len(r.phases), r.n_paths, len(e.rounds), r.scanned_total, r2.scanned_total, e.scanned_total, r.bfs_total, r.dfs_total)):
            cols[k].append(v)
        levels = [ph.level for ph in r.phases]
        growing.append(all(a < b for a, b in zip(levels, levels[1:])))
        ratio.append(len(r.phases) / (net.n - 1))
        same_count.append(r.n_paths == len(e.rounds))
        same_lengths.append(sorted(p_.length for ph in r.phases for p_ in ph.paths) == sorted(x.length for x in e.rounds))
        served.append(pct(r.value, demand))
        all_served += r.value == demand
        unique.append(r.unique_cut)
        path_mean_ph.append(r.n_paths / len(r.phases) if r.phases else 0.0)
    n = len(seeds)
    out = {"n_seeds": n, "cols": cols, "share_growing": sum(growing) / n, "share_same_count": sum(same_count) / n, "share_same_lengths": sum(same_lengths) / n,
           "share_le_ek": sum(1 for a, b in zip(cols["dinic"], cols["ek"]) if a <= b) / n, "bound_ratio_mean": mean(ratio), "bound_ratio_max": max(ratio),
           "served_mean": mean(served), "share_all_served": all_served / n, "share_unique": sum(unique) / n, "paths_per_phase_mean": mean(path_mean_ph),
           "edges_mean": mean(net.m for net, *_ in _runs(p, d, s, density, spread, load, seeds)), "nodes_mean": mean(net.n for net, *_ in _runs(p, d, s, density, spread, load, seeds))}
    for k in keys:
        out[k + "_mean"], out[k + "_median"], out[k + "_max"] = mean(cols[k]), median(cols[k]), max(cols[k])
    return out


@lru_cache(maxsize=64)
def scaling(sizes=C.SCALE_SIZES, seeds=C.SCALE_SEEDS):
    """Phasen und durchsuchte Kanten gegen die Netzgröße: Dinic, Dinic ohne Zeigerliste, Edmonds-Karp."""
    rows = []
    for (p, d, s) in sizes:
        dist = distribution(p, d, s, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, tuple(seeds))
        rows.append({"size": (p, d, s), "n": dist["nodes_mean"], "m": dist["edges_mean"], "phases": dist["phases_mean"], "paths": dist["paths_mean"], "dinic": dist["dinic_mean"],
                     "nopointer": dist["nopointer_mean"], "ek": dist["ek_mean"], "ek_rounds": dist["ek_rounds_mean"], "bfs": dist["bfs_mean"], "dfs": dist["dfs_mean"]})
    return rows


def slopes(rows):
    """Steigung im doppelt logarithmischen Diagramm (durchsuchte Kanten gegen Kantenzahl)."""
    x = np.log([r["m"] for r in rows])
    return {k: float(np.polyfit(x, np.log([r[k] for r in rows]), 1)[0]) for k in ("dinic", "nopointer", "ek")}


# --- Einheitsnetze ------------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=16)
def stair_table(ks=C.STAIR_KS):
    rows = []
    for k in ks:
        net = sc.staircase(k)
        r = dn.dinic(net, keep_flows=False)
        rows.append({"k": k, "n": (net.n - 2) // 2, "phases": len(r.phases), "levels": [ph.level for ph in r.phases], "value": r.value, "ek_rounds": len(ek.max_flow(net, "bfs", keep_flows=False).rounds)})
    return rows


@lru_cache(maxsize=16)
def unit_random(sizes=C.UNIT_SIZES, degree=C.UNIT_DEGREE, seeds=C.UNIT_SEEDS):
    rows = []
    for n in sizes:
        phases = [len(dn.dinic(sc.random_bipartite(n, degree, seed), keep_flows=False).phases) for seed in seeds]
        rows.append({"n": n, "phases_mean": mean(phases), "phases_max": max(phases), "bound": 2 * n ** 0.5})
    return rows
