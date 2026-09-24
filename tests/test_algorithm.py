"""Kern: Dinic gegen Handfälle und unabhängige Gegenproben (networkx, scipy, Brute Force), Niveaugraph unabhängig nachgebaut, Invarianten je Phase und je Weg,
Zeigerliste (gleiche Wege, mehr Aufwand ohne), Einheitsnetze und Treppe."""

import itertools
import random

import networkx as nx
import numpy as np
import pytest
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching, maximum_flow

import dn_algorithm as dn
import dn_edmonds_karp as ek
import dn_scenario as sc
from dn_scenario import SplitMix64


def _nets(count, sizes=((2, 2, 3), (3, 3, 6), (3, 3, 8), (4, 3, 5), (2, 4, 9), (6, 6, 12))):
    """Zufällige Distributionsnetze unterschiedlicher Größe, Dichte, Streuung und Auslastung."""
    rng = random.Random(11)
    for i in range(count):
        p, d, s = sizes[i % len(sizes)]
        yield sc.generate(p, d, s, rng.choice((20, 40, 60, 80, 100)), rng.choice((0, 25, 50, 75, 100)), rng.choice((40, 90, 120, 160)), 2000 + i)


def _digraph(net):
    g = nx.DiGraph()
    for u, v, c, _, _ in net.arcs:
        g.add_edge(u, v, capacity=c)
    return g


def _residual_arcs(net, flow):
    """(Kopf, Ende, Restkante) je Restkante mit Restkapazität, unabhängig von der Implementierung aufgebaut."""
    out = []
    for i, (u, v, c, _, _) in enumerate(net.arcs):
        if c - flow[i] > 0:
            out.append((u, v, 2 * i))
        if flow[i] > 0:
            out.append((v, u, 2 * i + 1))
    return out


def _source_flow(net, flow):
    return sum(flow[i] for i, arc in enumerate(net.arcs) if arc[0] == net.s)


# --- kopierte Bausteine (Wache gegen einen fehlerhaften Kopiervorgang) -------------------------------------------------------------------------

def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_edmonds_karp_copy_reproduces_the_numbers_of_the_predecessor_demo():
    """Die Breitensuche stammt aus der Edmonds-Karp-Demo; deren Zahlen bei den Standardeinstellungen müssen wiederkommen."""
    rounds, scans = [], []
    for seed in range(100000, 100100):
        res = ek.max_flow(sc.generate(3, 3, 8, 60, 50, 90, seed), "bfs", keep_flows=False)
        rounds.append(len(res.rounds))
        scans.append(res.scanned_total)
    assert abs(sum(rounds) / 100 - 11.1) <= 0.06 and sum(scans) == 52475 and sorted(scans)[49:51] == [525, 527] and max(rounds) == 16     # Mittel 524,75, Median 526
    assert len(ek.max_flow(sc.assignment(4), "bfs").rounds) == 5 and ek.max_flow(sc.assignment(4), "bfs").scanned_total == 100


# --- Handfälle ---------------------------------------------------------------------------------------------------------------------------------

def test_assignment_chain_by_hand():
    net = sc.assignment(4)
    res = dn.dinic(net)
    assert res.value == 5 and [ph.level for ph in res.phases] == [3] and [len(ph.paths) for ph in res.phases] == [5]
    assert res.scanned_total == 69 and res.cut_capacity == 5


def test_staircase_by_hand():
    for k in range(1, 7):
        net = sc.staircase(k)
        res = dn.dinic(net)
        n = k * (k + 3) // 2
        assert res.value == n and (net.n - 2) // 2 == n
        assert [ph.level for ph in res.phases] == [2 * t + 1 for t in range(1, k + 2)]                # Niveau 3, 5, ..., 2k + 3
        assert [len(ph.paths) for ph in res.phases] == [n - k] + [1] * k                                # erste Phase: alle billigen Kanten, danach ein Weg je Kette


def test_cut_of_a_tiny_net_and_uniqueness():
    net = sc.assignment(1)                                    # F1-A1 und F2-A1, F2-A2: Fahrzeuge 2, Aufträge 2
    res = dn.dinic(net)
    assert res.value == 2 and res.cut_capacity == 2


# --- Gegenproben -------------------------------------------------------------------------------------------------------------------------------

def test_value_and_cut_agree_with_networkx_and_scipy_on_random_nets():
    for net in _nets(90):
        g = _digraph(net)
        expected, _ = nx.minimum_cut(g, net.s, net.t)
        assert nx.maximum_flow_value(g, net.s, net.t, flow_func=nx.algorithms.flow.dinitz) == expected
        mat = np.zeros((net.n, net.n), dtype=np.int32)
        for u, v, c, _, _ in net.arcs:
            mat[u, v] = c
        for method in ("dinic", "edmonds_karp"):
            assert maximum_flow(csr_matrix(mat), net.s, net.t, method=method).flow_value == expected
        for current_arc in (True, False):
            res = dn.dinic(net, current_arc=current_arc)
            assert res.value == expected == res.cut_capacity
            assert not dn.has_augmenting_path(net, res.flow)
            assert not res.reach[net.t]


def test_the_cut_is_a_minimum_cut_by_brute_force_and_uniqueness_is_right():
    for net in _nets(40, sizes=((2, 2, 3), (2, 2, 4))):
        others = [v for v in range(net.n) if v not in (net.s, net.t)]
        best, count = None, 0
        for mask in itertools.product((0, 1), repeat=len(others)):
            side = {net.s} | {v for v, b in zip(others, mask) if b}
            cap = sum(c for u, v, c, _, _ in net.arcs if u in side and v not in side)
            if best is None or cap < best:
                best, count = cap, 1
            elif cap == best:
                count += 1
        res = dn.dinic(net)
        assert res.cut_capacity == best and res.value == best and res.unique_cut == (count == 1)


def test_same_cut_as_edmonds_karp():
    for net in _nets(40):
        a, b = dn.dinic(net), ek.max_flow(net, "bfs")
        assert a.value == b.value and a.reach == b.reach and a.cut_arcs == b.cut_arcs and a.unique_cut == b.unique_cut


def test_level_graph_is_the_bfs_level_graph_of_the_residual_graph():
    """Niveaus und Niveaugraph jeder Phase unabhängig per networkx auf dem Restgraphen VOR der Phase nachbauen."""
    for net in _nets(45):
        res = dn.dinic(net)
        for ph in res.phases:
            arcs = _residual_arcs(net, ph.flow_before)
            g = nx.DiGraph([(u, v) for u, v, _ in arcs])
            g.add_nodes_from(range(net.n))
            dist = nx.single_source_shortest_path_length(g, net.s)
            top = dist[net.t]
            assert top == ph.level
            for v in range(net.n):
                expected = dist[v] if (v in dist and (dist[v] < top or v == net.t)) else -1
                assert ph.levels[v] == expected
            expected_arcs = sorted((u, v) for u, v, _ in arcs if u in dist and v in dist and dist[u] + 1 == dist[v] and dist[u] < top and (dist[v] < top or v == net.t))
            assert sorted((net.arcs[e // 2][0], net.arcs[e // 2][1]) if e % 2 == 0 else (net.arcs[e // 2][1], net.arcs[e // 2][0]) for e in ph.level_arcs) == expected_arcs


def test_phase_and_path_invariants():
    for net in _nets(45):
        res = dn.dinic(net)
        levels = [ph.level for ph in res.phases]
        assert all(a < b for a, b in zip(levels, levels[1:])) and len(levels) <= net.n - 1          # Lemma: Niveau von T wächst echt, höchstens |V|-1 Phasen
        prev_value = 0
        for ph in res.phases:
            assert ph.value_before == prev_value and ph.paths and ph.value_after == ph.value_before + sum(p.bottleneck for p in ph.paths)
            assert _source_flow(net, ph.flow_before) == ph.value_before
            level_arc_set = set(ph.level_arcs)
            for p in ph.paths:
                assert p.nodes[0] == net.s and p.nodes[-1] == net.t and p.length == ph.level == len(p.arcs) == len(p.nodes) - 1
                assert set(p.arcs) <= level_arc_set and p.bottleneck >= 1
                for i, e in enumerate(p.arcs):                                                        # jede Kante steigt um genau ein Niveau
                    assert ph.levels[p.nodes[i + 1]] == ph.levels[p.nodes[i]] + 1
                for i, (u, v, c, _, _) in enumerate(net.arcs):
                    assert 0 <= p.flow_after[i] <= c
                for v in range(net.n):
                    if v not in (net.s, net.t):
                        assert sum(p.flow_after[i] for i, a in enumerate(net.arcs) if a[1] == v) == sum(p.flow_after[i] for i, a in enumerate(net.arcs) if a[0] == v)
            prev_value = ph.value_after
        assert prev_value == res.value


def test_each_phase_is_a_blocking_flow():
    """Nach der Phase gibt es im Niveaugraph (mit dem Fluss NACH der Phase) keinen S-T-Weg mehr."""
    for net in _nets(45):
        res = dn.dinic(net)
        for ph in res.phases:
            flow = ph.paths[-1].flow_after
            alive = []
            for e in ph.level_arcs:
                i = e // 2
                rest = net.arcs[i][2] - flow[i] if e % 2 == 0 else flow[i]
                if rest > 0:
                    alive.append((net.arcs[i][0], net.arcs[i][1]) if e % 2 == 0 else (net.arcs[i][1], net.arcs[i][0]))
            g = nx.DiGraph(alive)
            g.add_nodes_from([net.s, net.t])
            assert not nx.has_path(g, net.s, net.t)


def test_bottleneck_is_the_smallest_rest_on_the_path():
    for net in _nets(20):
        res = dn.dinic(net)
        for ph in res.phases:
            flow = ph.flow_before
            for p in ph.paths:
                before = {}
                for e in p.arcs:
                    i = e // 2
                    before[e] = net.arcs[i][2] - flow[i] if e % 2 == 0 else flow[i]
                assert p.bottleneck == min(before.values())
                flow = p.flow_after


# --- Zeigerliste -------------------------------------------------------------------------------------------------------------------------------

def test_without_pointers_the_same_paths_are_found_with_at_least_as_many_scans():
    more = 0
    for net in _nets(60):
        a, b = dn.dinic(net), dn.dinic(net, current_arc=False)
        assert [p.nodes for ph in a.phases for p in ph.paths] == [p.nodes for ph in b.phases for p in ph.paths]
        assert [p.bottleneck for ph in a.phases for p in ph.paths] == [p.bottleneck for ph in b.phases for p in ph.paths]
        assert a.scanned_total <= b.scanned_total and a.bfs_total == b.bfs_total
        more += a.scanned_total < b.scanned_total
    assert more > 30                                                            # Negativkontrolle: ohne Zeiger wird es wirklich teurer


def test_dead_ends_are_visited_more_often_without_pointers():
    net = sc.generate(3, 3, 8, 60, 50, 90, 43)
    count = lambda r: sum(len(p.dead) for ph in r.phases for p in ph.paths) + sum(len(ph.tail_dead) for ph in r.phases)
    assert count(dn.dinic(net, current_arc=False)) > count(dn.dinic(net))


def test_keep_flows_false_changes_nothing_else():
    for net in _nets(15):
        a, b = dn.dinic(net), dn.dinic(net, keep_flows=False)
        assert a.value == b.value and a.scanned_total == b.scanned_total and a.flow == b.flow and [ph.level for ph in a.phases] == [ph.level for ph in b.phases]


# --- Einheitsnetze -----------------------------------------------------------------------------------------------------------------------------

def test_unit_nets_reach_the_maximum_matching_within_the_hopcroft_karp_phase_bound():
    for n, degree in ((10, 2), (20, 3), (40, 3), (80, 3)):
        for seed in range(100000, 100010):
            net = sc.random_bipartite(n, degree, seed)
            biadj = np.zeros((n, n), dtype=int)
            for u, v, _, _, _ in net.arcs:
                if 2 <= u < 2 + n and 2 + n <= v < 2 + 2 * n:
                    biadj[u - 2, v - 2 - n] = 1
            size = int((maximum_bipartite_matching(csr_matrix(biadj), perm_type="column") >= 0).sum())
            res = dn.dinic(net)
            assert res.value == size and len(res.phases) <= 2 * n ** 0.5 + 1
            assert all(ph.level % 2 == 1 for ph in res.phases)                        # Weglängen in Einheitsnetzen sind ungerade: 3, 5, 7, ...


def test_random_bipartite_is_reproducible_and_has_the_requested_degree():
    a, b = sc.random_bipartite(20, 3, 5), sc.random_bipartite(20, 3, 5)
    assert a == b and a != sc.random_bipartite(20, 3, 6)
    out_degree = {}
    for u, v, _, _, _ in a.arcs:
        if 2 <= u < 22:
            out_degree[u] = out_degree.get(u, 0) + 1
    assert set(out_degree.values()) == {3}
