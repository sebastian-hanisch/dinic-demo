"""Jede Zahl in den Hilfetexten, in der App und im README ist hier belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über die 100 festen Netze (DIST_SEEDS).
Alles ist ganzzahlig gerechnet (eigener Zufallsgenerator), die Zahlen sind auf Windows und Linux dieselben."""

import pytest

import dn_algorithm as dn
import dn_constants as C
import dn_evaluation as ev
import dn_scenario as sc

S = (C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD)


def near(value, expected, tol):
    assert abs(value - expected) <= tol, (value, expected)


def _preset(name):
    p = C.PRESETS[name]
    net = sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])
    return net, ev.analyse(net, p["blocking"] == "pointer")


def _dead(res):
    return sum(len(x.dead) for ph in res.phases for x in ph.paths) + sum(len(ph.tail_dead) for ph in res.phases)


def _shape(res):
    return [ph.level for ph in res.phases], [len(ph.paths) for ph in res.phases]


def _back(res):
    return sum(1 for ph in res.phases for x in ph.paths if x.uses_back_arc)


# --- Presets (PRESET_HELP) ------------------------------------------------------------------------------------------------------------------------

def test_default_net_preset():
    net, a = _preset("🚚 Zufallsnetz")
    r = a.result
    assert (r.value, a.demand) == (71, 77) and _shape(r) == ([5, 7], [8, 2]) and _back(r) == 2       # "71 von 77", "2 Phasen (Niveau 5 und 7) mit 8 und 2 Wegen, zwei über Rückkanten"
    assert len(a.edmonds_karp.rounds) == 10 and r.scanned_total == 219 and a.edmonds_karp.scanned_total == 434   # "dieselben 10 Wege", "219 gegen 434"
    assert _dead(r) == 17


def test_no_pointer_preset():
    net, a = _preset("🧭 Ohne Zeigerliste")
    _, base = _preset("🚚 Zufallsnetz")
    assert a.result.scanned_total == 389 and _dead(a.result) == 48 and _dead(base.result) == 17         # "389 statt 219", "48-mal statt 17-mal"
    assert [x.nodes for ph in a.result.phases for x in ph.paths] == [x.nodes for ph in base.result.phases for x in ph.paths] and a.result.n_paths == 10


def test_dead_end_preset():
    net, a = _preset("🕳️ Sackgassen")
    r = a.result
    assert (r.value, a.demand) == (68, 68) and _dead(r) == 42 and _shape(r) == ([5, 7], [9, 2])          # "(68)", "42-mal", "9 + 2 Wege in 2 Phasen"
    assert r.scanned_total == 374 and a.edmonds_karp.scanned_total == 651


def test_three_phases_preset():
    net, a = _preset("🔁 Drei Phasen")
    r = a.result
    assert _shape(r) == ([5, 7, 9], [17, 3, 1]) and (r.value, a.demand) == (124, 150)                    # "Niveau 5, 7 und 9 und 17, 3 und 1 Wegen", "124 von 150"
    assert r.scanned_total == 722 and a.edmonds_karp.scanned_total == 2120


def test_single_phase_preset():
    net, a = _preset("🌊 Alles in einer Phase")
    r = a.result
    assert _shape(r) == ([5], [26]) and (r.value, a.demand) == (150, 150)                                # "alle 26 Wege ... (Niveau 5)", "(150)"
    assert r.scanned_total == 571 and a.edmonds_karp.scanned_total == 3624 and round(3624 / 571, 1) == 6.3


def test_scarce_plants_preset():
    net, a = _preset("🏭 Werke knapp")
    r = a.result
    assert (r.value, a.demand) == (98, 114) and a.stage_caps == {sc.K_SUPPLY: 98}                        # "98 von 114", "nur aus den drei Werken"
    assert _shape(r) == ([5, 7], [10, 3]) and r.scanned_total == 283 and a.edmonds_karp.scanned_total == 787


def test_staircase_preset():
    net, a = _preset("🪜 Treppe")
    r = a.result
    assert (net.n - 2) // 2 == 20 and _shape(r) == ([3, 5, 7, 9, 11, 13], [15, 1, 1, 1, 1, 1])           # "20 Fahrzeuge ... 6 Phasen ... Die erste nimmt 15 Wege, jede weitere genau einen"
    assert r.scanned_total == 928 and a.edmonds_karp.scanned_total == 1345                               # "928 durchsuchte Kanten gegen 1345"


def test_assignment_preset():
    net, a = _preset("💑 Zuordnung als Fluss")
    r = a.result
    assert _shape(r) == ([3], [5]) and r.scanned_total == 69 and a.edmonds_karp.scanned_total == 100    # "eine Phase (Niveau 3) mit 5 Wegen", "69 ... gegen 100"


# --- Verteilungen bei den Standardeinstellungen (100 feste Netze) ---------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dist():
    return ev.distribution(*S)


def test_phases_and_paths(dist):
    near(dist["phases_mean"], 1.71, 0.005)                          # Intro: "im Mittel weniger als zwei"; Kennzahl Phasen 1,7
    assert dist["phases_mean"] < 2 and dist["phases_median"] == 2 and dist["phases_max"] == 4   # "Median 2, höchstens 4"; Grenzen: "im Mittel 1,7, höchstens 4"
    assert dist["nodes_mean"] == 19 and dist["phases_max"] == 4    # "höchstens 4 von 18"
    near(dist["paths_mean"], 11.11, 0.005)
    assert dist["share_same_count"] == 1.0 and dist["share_same_lengths"] == 1.0    # "auf allen 100 Netzen so viele Wege wie bei Edmonds-Karp"
    assert dist["share_growing"] == 1.0                              # Niveau von T wächst in jedem Netz echt
    hist = {k: dist["cols"]["phases"].count(k) for k in set(dist["cols"]["phases"])}
    assert hist == {1: 40, 2: 50, 3: 9, 4: 1}


def test_scans_against_edmonds_karp(dist):
    near(dist["dinic_mean"], 253.67, 0.01)                         # Sidebar: "254 Kanten mit ... (Edmonds-Karp: 525)"
    near(dist["nopointer_mean"], 435.52, 0.01)                     # "436 ohne Zeigerliste"
    near(dist["ek_mean"], 524.75, 0.01)
    assert (dist["dinic_median"], dist["nopointer_median"], dist["ek_median"]) == (236.5, 428.0, 526.0)
    assert dist["share_le_ek"] == 1.0                              # "Dinic günstiger": 100 %
    near(dist["ek_mean"] / dist["dinic_mean"], 2.07, 0.01)         # README: gut das Doppelte
    ratios = [e / d for d, e in zip(dist["cols"]["dinic"], dist["cols"]["ek"])]
    assert 1.2 < min(ratios) < 1.3 and max(ratios) > 3.4


def test_bound_on_phases(dist):
    near(dist["bound_ratio_mean"], 0.095, 0.001)                   # README: Phasen im Mittel 9,5 % (höchstens 22 %) von |V| - 1
    near(dist["bound_ratio_max"], 0.222, 0.001)


def test_pointer_factor(dist):
    factors = [b / a for a, b in zip(dist["cols"]["dinic"], dist["cols"]["nopointer"])]
    near(dist["nopointer_mean"] / dist["dinic_mean"], 1.72, 0.005)  # Kennzahl "Aufwand ohne ÷ mit Zeigerliste (Mittel)"
    near(max(factors), 2.5, 0.05)                                     # "größter Faktor eines Netzes"
    assert sum(1 for f in factors if f == 1) == 0                     # "Netze mit gleichem Aufwand": 0 %


def test_bfs_and_dfs_parts_of_the_scans(dist):
    near(dist["bfs_mean"], 115, 0.1) and near(dist["dfs_mean"], 138.7, 0.1)
    assert dist["bfs_mean"] + dist["dfs_mean"] == pytest.approx(dist["dinic_mean"])


# --- Phasen gegen die Regler --------------------------------------------------------------------------------------------------------------------

def test_phases_against_density_and_load():
    near(ev.distribution(3, 3, 8, 100, 50, 90)["phases_mean"], 1.04, 0.005)     # Sidebar Netzdichte: "bei 100 % ... 1,0"
    near(ev.distribution(3, 3, 8, 60, 50, 90)["phases_mean"], 1.71, 0.005)      # "Höhepunkt bei 60 %: 1,7"
    means = {d: ev.distribution(3, 3, 8, d, 50, 90)["phases_mean"] for d in range(20, 101, 10)}
    assert max(means, key=means.get) == 60                                       # 60 % ist der Höhepunkt
    near(ev.distribution(3, 3, 8, 60, 50, 40)["phases_mean"], 1.05, 0.005)     # Sidebar Auslastung: "bei 40 % ... 1,05"
    near(ev.distribution(3, 3, 8, 60, 50, 120)["phases_mean"], 1.77, 0.005)    # "bei 120 % ... 1,8"


# --- Skalierung ---------------------------------------------------------------------------------------------------------------------------------

def test_scaling():
    rows = ev.scaling()
    slopes = ev.slopes(rows)
    near(slopes["dinic"], 0.94, 0.03)                               # README: Dinic 0,94, ohne Zeigerliste 1,45, Edmonds-Karp 1,74
    near(slopes["nopointer"], 1.45, 0.03)
    near(slopes["ek"], 1.74, 0.03)
    assert [round(r["ek"] / r["dinic"], 1) for r in rows] == [1.2, 2.0, 3.4, 9.0, 17.3, 33.7]      # Tabelle "Edmonds-Karp ÷ Dinic"
    assert [round(r["nopointer"] / r["dinic"], 1) for r in rows] == [1.4, 1.7, 2.2, 4.2, 6.7, 10.6]  # "ohne ÷ mit Zeigerliste"
    assert all(r["phases"] == 1.0 for r in rows[3:]) and rows[1]["phases"] > 1.5    # "bei den großen Netzen schon eine Phase"
    near(rows[-1]["n"], 166, 0.5), near(rows[0]["n"], 12, 0.5)      # Knopf "Netze von 12 bis 166 Knoten"


# --- Einheitsnetze -------------------------------------------------------------------------------------------------------------------------------

def test_unit_nets():
    stair = {r["k"]: r for r in ev.stair_table()}
    assert all(r["phases"] == r["k"] + 1 for r in stair.values())                   # "k + 1 Phasen bei k (k + 3) / 2 Fahrzeugen"
    assert all(abs(r["phases"] - (2 * r["n"]) ** 0.5) <= 1.5 for r in stair.values())   # "etwa sqrt(2n)"
    assert stair[12]["n"] == 90 and stair[12]["phases"] == 13 and 0.65 < 13 / (2 * 90 ** 0.5) < 0.7
    assert all(r["ek_rounds"] == r["n"] for r in stair.values())                     # "Wege gibt es so viele wie Fahrzeuge"
    unit = {r["n"]: r for r in ev.unit_random()}
    assert unit[320]["phases_mean"] == 5.4 and unit[320]["phases_max"] == 8 and round(unit[320]["bound"]) == 36   # README: "5,4 bei n = 320 (Schranke 36)"
    assert all(r["phases_mean"] < r["bound"] / 2 for r in unit.values())            # "weit darunter"
