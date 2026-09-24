"""Presets: vollständig, in den Grenzen, und jedes Beispielnetz zeigt, was sein Hilfetext behauptet."""

import pytest

import dn_algorithm as dn
import dn_constants as C
import dn_evaluation as ev
import dn_presets as P
import dn_scenario as sc

KEYS = set(P.PRESET_KEYS)


def _net(p):
    return sc.build(p["net"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["blocking"] in C.BLOCKING_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["density"] - C.DENSITY_MIN) % 10 == 0 and p["spread"] % 25 == 0 and (p["load"] - C.LOAD_MIN) % 10 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_random_net_preset():
    p = C.PRESETS["🚚 Zufallsnetz"]
    assert (p["net"], p["blocking"], p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"], p["seed"]) == (
        C.DEFAULT_NET, C.DEFAULT_BLOCKING, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)


def test_the_pointer_preset_shares_the_default_net():
    base, off = C.PRESETS["🚚 Zufallsnetz"], C.PRESETS["🧭 Ohne Zeigerliste"]
    assert all(off[k] == base[k] for k in base if k != "blocking") and (base["blocking"], off["blocking"]) == ("pointer", "nopointer")


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"🪜 Treppe", "💑 Zuordnung als Fluss"}


def test_default_net_is_a_typical_draw():
    """Das Beispielnetz hat die mediane Phasenzahl der 100 festen Netze, eine Wegezahl im Bereich des Medians (±2) und durchsucht ähnlich viele Kanten wie der Median (±25 %)."""
    p = C.PRESETS["🚚 Zufallsnetz"]
    dist = ev.distribution(p["p"], p["d"], p["s"], p["density"], p["spread"], p["load"])
    res = dn.dinic(_net(p))
    assert len(res.phases) == dist["phases_median"] and abs(res.n_paths - dist["paths_median"]) <= 2
    assert abs(res.scanned_total - dist["dinic_median"]) <= 0.25 * dist["dinic_median"]
    assert res.n_paths == len(ev.analyse(_net(p)).edmonds_karp.rounds)


def test_the_presets_show_both_good_and_bad_news():
    """Positive UND negative Aussagen: auf jedem Preset durchsucht Dinic weniger als Edmonds-Karp (gut), und mindestens ein Preset zeigt, dass der Vorsprung klein bleibt (die Treppe: unter dem Faktor 1,5)."""
    factors = {}
    for name, p in C.PRESETS.items():
        a = ev.analyse(_net(p), p["blocking"] == "pointer")
        factors[name] = a.edmonds_karp.scanned_total / a.result.scanned_total
    assert factors["🧭 Ohne Zeigerliste"] > 1.0 and min(v for n, v in factors.items() if n != "🧭 Ohne Zeigerliste") > 1.0
    assert factors["🪜 Treppe"] < 1.5 and max(factors.values()) > 5
