"""Orakel: Dinic gegen eine unabhängige Neuimplementierung (rekursive Tiefensuche auf Kantenlisten, Zeiger je Knoten) und networkx auf zufälligen allgemeinen
Digraphen (Zyklen, Gegenkanten, Parallelkanten, Kapazität 0): Flusswert, Schnitt, Phasenzahl, Niveau von T je Phase und die angezeigten Zähler
(durchsuchte Kanten der Breiten- und Tiefensuchen). Schnell (< 10 s)."""

import itertools
import random
from collections import deque

import networkx as nx

import dn_algorithm as dn
import dn_scenario as sc


def _net(rng):
    n = rng.randint(2, 10)
    p = rng.choice((0.15, 0.3, 0.5, 0.8))
    cmax = rng.choice((1, 3, 10, 100))
    arcs = [(u, v, rng.randint(0, cmax)) for u in range(n) for v in range(n) if u != v and v != 0 and u != 1 and rng.random() < p]
    if arcs and rng.random() < 0.3:
        arcs.append(arcs[0])
    rng.shuffle(arcs)
    return n, sc.Net(tuple(f"v{i}" for i in range(n)), tuple(f"v{i}" for i in range(n)), tuple((i, i) for i in range(n)),
                     tuple((u, v, c, 0, sc.K_OTHER) for u, v, c in arcs), 0, 1, False)


def _reference(net):
    """Dinic mit Zählung: (Wert, Niveaus von T je Phase, Breitensuche-Einträge, Tiefensuche-Einträge); die Niveaus jenseits von T zählen nicht."""
    n, s, t = net.n, net.s, net.t
    arcs, adj = [], [[] for _ in range(n)]
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        arcs += [[u, v, c], [v, u, 0]]
        adj[u].append(2 * i)
        adj[v].append(2 * i + 1)
    value, tops, bfs, dfs = 0, [], 0, 0
    while True:
        lvl, queue, hit = [-1] * n, deque([s]), False
        lvl[s] = 0
        while queue and not hit:
            u = queue.popleft()
            for e in adj[u]:
                bfs += 1
                if arcs[e][2] > 0 and lvl[arcs[e][1]] < 0:
                    lvl[arcs[e][1]] = lvl[u] + 1
                    if arcs[e][1] == t:
                        hit = True
                        break
                    queue.append(arcs[e][1])
        if not hit:
            return value, tops, bfs, dfs
        top = lvl[t]
        tops.append(top)
        lvl = [x if (0 <= x < top or i == t) else -1 for i, x in enumerate(lvl)]
        ptr = [0] * n

        def go(u, f):
            nonlocal dfs
            if u == t:
                return f
            while ptr[u] < len(adj[u]):
                e = adj[u][ptr[u]]
                dfs += 1
                if arcs[e][2] > 0 and lvl[arcs[e][1]] == lvl[u] + 1:
                    d = go(arcs[e][1], min(f, arcs[e][2]))
                    if d > 0:
                        arcs[e][2] -= d
                        arcs[e ^ 1][2] += d
                        return d
                ptr[u] += 1
            return 0

        while True:
            d = go(s, 1 << 60)
            if d == 0:
                break
            value += d


def test_dinic_matches_independent_reference_and_networkx_on_random_digraphs():
    rng = random.Random(2026)
    for _ in range(120):
        n, net = _net(rng)
        g = nx.DiGraph()
        g.add_nodes_from(range(n))
        for u, v, c, _, _ in net.arcs:
            if g.has_edge(u, v):
                g[u][v]["capacity"] += c
            else:
                g.add_edge(u, v, capacity=c)
        expected = nx.maximum_flow_value(g, 0, 1)
        res = dn.dinic(net)
        value, tops, bfs, dfs = _reference(net)
        assert res.value == value == expected == res.cut_capacity
        assert [ph.level for ph in res.phases] == tops
        assert (res.bfs_total, res.dfs_total) == (bfs, dfs)
        assert not dn.has_augmenting_path(net, res.flow)
        for v in range(2, n):
            assert sum(res.flow[i] for i, a in enumerate(net.arcs) if a[1] == v) == sum(res.flow[i] for i, a in enumerate(net.arcs) if a[0] == v)
        assert all(0 <= f <= a[2] for f, a in zip(res.flow, net.arcs))


def test_unique_cut_flag_against_cut_enumeration():
    rng = random.Random(7)
    for _ in range(60):
        n, net = _net(rng)
        n = min(n, 9)
        net = sc.Net(net.names, net.labels, net.pos, tuple(a for a in net.arcs if a[0] < n and a[1] < n), 0, 1, False) if net.n > n else net
        others = list(range(2, net.n))
        caps = []
        for mask in itertools.product((0, 1), repeat=len(others)):
            side = {0} | {v for v, b in zip(others, mask) if b}
            caps.append(sum(c for u, v, c, _, _ in net.arcs if u in side and v not in side))
        res = dn.dinic(net)
        assert res.cut_capacity == min(caps) and res.unique_cut == (caps.count(min(caps)) == 1)
