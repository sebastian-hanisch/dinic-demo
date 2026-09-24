"""Szenario (Aufbau, Reproduzierbarkeit, Stufen, Einheitsnetze), Auswertung (Urteil, Bilderfolge, Verteilungen, Experimente)."""

import pytest

import dn_algorithm as dn
import dn_constants as C
import dn_edmonds_karp as ek
import dn_evaluation as ev
import dn_scenario as sc

DEFAULT = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def _net(seed=C.DEFAULT_SEED, *settings):
    return sc.generate(*(settings or DEFAULT), seed)


def test_generation_is_reproducible_and_seed_dependent():
    assert _net(5) == _net(5) and _net(5) != _net(6)


def test_structure_of_a_distribution_net():
    p, d, s = 3, 3, 8
    net = _net()
    assert net.n == 2 + p + 2 * d + s and net.s == 0 and net.t == 1 and net.logistic
    kinds = [a[4] for a in net.arcs]
    assert kinds.count(sc.K_SUPPLY) == p and kinds.count(sc.K_THROUGHPUT) == d and kinds.count(sc.K_DEMAND) == s
    assert all(a[2] >= 1 for a in net.arcs)
    for u, v, _, _, kind in net.arcs:                                       # Stufen laufen von oben nach unten
        assert net.pos[u][1] > net.pos[v][1]
        if kind == sc.K_THROUGHPUT:
            assert net.pos[u][0] == net.pos[v][0] and net.names[u].endswith("(Eingang)") and net.names[v].endswith("(Ausgang)")


@pytest.mark.parametrize("seed", range(30))
def test_every_plant_and_store_has_a_lane_even_on_the_thinnest_net(seed):
    net = _net(seed, 3, 3, 8, C.DENSITY_MIN, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)
    plants = {a[1] for a in net.arcs if a[4] == sc.K_SUPPLY}
    stores = {a[0] for a in net.arcs if a[4] == sc.K_DEMAND}
    assert plants <= {a[0] for a in net.arcs if a[4] == sc.K_LANE_IN}
    assert stores <= {a[1] for a in net.arcs if a[4] == sc.K_LANE_OUT}


def test_a_thinner_net_only_removes_lanes_and_keeps_all_other_values():
    for seed in range(20):
        thin, full = _net(seed, 3, 3, 8, 40, 50, 90), _net(seed, 3, 3, 8, 100, 50, 90)
        assert set(thin.arcs) <= set(full.arcs) and len(thin.arcs) < len(full.arcs)


def test_teaching_nets_and_build_ignore_the_random_settings():
    assert not sc.assignment(4).logistic and sc.build("assignment", 6, 6, 12, 100, 100, 160, 1) == sc.assignment(4)
    assert sc.build("random", *DEFAULT, 9) == _net(9)
    assert sc.build("stair", 6, 6, 12, 100, 100, 160, 1) == sc.staircase(5)
    assert sc.assignment(4).n == 12 and sc.assignment(4).m == 5 + 9 + 5


def test_staircase_sizes():
    for k in (1, 2, 5, 8):
        net = sc.staircase(k)
        n = k * (k + 3) // 2
        assert net.n == 2 + 2 * n and net.m == n + sum(2 * i + 1 for i in range(1, k + 1)) + n
        assert all(a[2] == 1 for a in net.arcs)


def test_verdict_codes():
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 100, 50, 40)))
    assert (lvl, code) == ("success", "delivered") and d["value"] == d["demand"]
    lvl, code, d = ev.verdict(ev.analyse(_net(1, 3, 3, 8, 60, 50, 160)))
    assert (lvl, code) == ("warning", "bottleneck") and d["value"] < d["demand"] and d["dominant"] in ev.STAGE_KINDS
    assert ev.verdict(ev.analyse(sc.assignment(4)))[:2] == ("info", "teaching")
    lvl, code, d = ev.verdict(ev.analyse(sc.generate(2, 6, 3, 20, 50, 90, 8)))
    assert (lvl, code) == ("warning", "disconnected") and d["value"] == 0 and d["phases"] == 0


def test_frames_cover_every_phase_and_path_and_end_with_the_proof():
    res = dn.dinic(_net())
    fr = ev.frames(res)
    assert fr[0] == (0, 0) and fr[-1] == (len(res.phases), 0)
    assert len(fr) == sum(1 + len(ph.paths) for ph in res.phases) + 1
    assert ev.frames(dn.dinic(sc.generate(2, 6, 3, 20, 50, 90, 8))) == [(0, 0)]                 # kein Fluss: nur das Endbild


def test_stage_capacities_add_up_to_the_cut():
    for seed in range(30):
        a = ev.analyse(_net(seed))
        assert sum(a.stage_caps.values()) == a.result.cut_capacity == a.result.value


def test_distribution_is_consistent_with_single_runs():
    dist = ev.distribution(*DEFAULT, seeds=tuple(range(5)))
    runs = [dn.dinic(sc.generate(*DEFAULT, seed)) for seed in range(5)]
    assert dist["cols"]["phases"] == [len(r.phases) for r in runs] and dist["cols"]["dinic"] == [r.scanned_total for r in runs]
    assert dist["cols"]["ek"] == [ek.max_flow(sc.generate(*DEFAULT, seed), "bfs").scanned_total for seed in range(5)]
    assert dist["n_seeds"] == 5 and 0 <= dist["share_all_served"] <= 1 and dist["bound_ratio_max"] <= 1


def test_scaling_rows_and_slopes():
    rows = ev.scaling()
    assert [r["size"] for r in rows] == list(C.SCALE_SIZES)
    assert all(r["dinic"] < r["nopointer"] and r["phases"] >= 1 for r in rows)
    assert all(0.5 < s < 2.5 for s in ev.slopes(rows).values())


def test_stair_and_unit_tables():
    rows = ev.stair_table()
    assert [r["k"] for r in rows] == list(C.STAIR_KS) and all(r["phases"] == r["k"] + 1 and r["value"] == r["n"] == r["ek_rounds"] for r in rows)
    unit = ev.unit_random()
    assert [r["n"] for r in unit] == list(C.UNIT_SIZES) and all(r["phases_max"] <= r["bound"] + 1 for r in unit)
