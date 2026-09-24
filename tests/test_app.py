"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, beide Zeigerlisten-Varianten, Randgrößen, Schritt-Zustand, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import dn_constants as C
from dn_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

# Anfang der Meldung zum gezeigten Netz und (bei Zufallsnetzen) Teil der Meldung zur Verteilung (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "🚚 Zufallsnetz": "Das Netz schafft höchstens **71 von 77** Einheiten (92 %). Engpass: **Werkskapazität 50, Lane Werk → DC 21**",
    "🧭 Ohne Zeigerliste": "Das Netz schafft höchstens **71 von 77** Einheiten (92 %)",
    "🕳️ Sackgassen": "Die gesamte Nachfrage (68) wird geliefert, in 2 Phase(n) mit 11 Weg(en)",
    "🔁 Drei Phasen": "Das Netz schafft höchstens **124 von 150** Einheiten (83 %)",
    "🌊 Alles in einer Phase": "Die gesamte Nachfrage (150) wird geliefert, in 1 Phase(n) mit 26 Weg(en)",
    "🏭 Werke knapp": "Das Netz schafft höchstens **98 von 114** Einheiten (86 %). Engpass: **Werkskapazität 98**",
    "🪜 Treppe": "Flusswert 20 in 6 Phase(n) mit 20 Weg(en) (Niveau 3, 5, 7, 9, 11, 13)",
    "💑 Zuordnung als Fluss": "Flusswert 5 in 1 Phase(n) mit 5 Weg(en) (Niveau 3)",
}


def _run(setup=None, timeout=600):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def _step(at):
    found = [s for s in at.slider if s.key == "dn_step"]
    return found[0] if found else None


def _metric(at, label):
    return [m.value for m in at.metric if m.label == label]


def test_default_renders_without_exception():
    at = _run()
    assert any("Phasen in Aktion" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🚚 Zufallsnetz"]) and not at.error
    assert _metric(at, "Flusswert")[0] == "71 von 77" and _metric(at, "Phasen")[0] == "2" and _metric(at, "Wege")[0] == "10"


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    assert _has(at, EXPECTED[name]), _texts(at)
    if C.PRESETS[name]["net"] in C.FIXED_NETS:
        assert any(t.startswith("Festes Netz") for t in _texts(at))
    else:
        assert any("Netze durchsucht Dinic" in t for t in _texts(at))


@pytest.mark.parametrize("blocking", list(C.BLOCKING_LABELS))
def test_both_blocking_variants_reach_the_same_flow_on_the_default_net(blocking):
    at = _run(lambda a: a.session_state.__setitem__("blocking_radio", blocking))
    assert not at.error and _metric(at, "Flusswert")[0] == "71 von 77" and _metric(at, "Wege")[0] == "10"
    assert _metric(at, "Durchsuchte Kanten")[0] == ("219" if blocking == "pointer" else "389")


def test_extreme_sizes_render():
    for p, d, s, dens, spread, load in ((C.P_MIN, C.D_MIN, C.S_MIN, C.DENSITY_MIN, C.SPREAD_MIN, C.LOAD_MIN), (C.P_MAX, C.D_MAX, C.S_MAX, C.DENSITY_MAX, C.SPREAD_MAX, C.LOAD_MAX),
                                        (C.P_MIN, C.D_MAX, C.S_MAX, C.DENSITY_MIN, C.SPREAD_MAX, C.LOAD_MAX), (C.P_MAX, C.D_MIN, C.S_MIN, C.DENSITY_MAX, C.SPREAD_MIN, C.LOAD_MIN)):
        def setup(at, vals=(p, d, s, dens, spread, load)):
            for key, value in zip(("p_slider", "d_slider", "s_slider", "density_slider", "spread_slider", "load_slider"), vals):
                at.session_state[key] = value
        at = _run(setup)
        step = _step(at)
        assert step is None or step.value == step.max


def test_a_net_where_nothing_arrives_renders_and_says_so():
    """Zwei Werke, sechs Verteilzentren, drei Filialen, dünnes Netz: kein Weg von S nach T."""
    def setup(at):
        for key, value in (("p_slider", 2), ("d_slider", 6), ("s_slider", 3), ("density_slider", 20), ("spread_slider", 50), ("load_slider", 90), ("seed_input", 8)):
            at.session_state[key] = value
    at = _run(setup)
    assert _step(at) is None and any(b.label == "▶️ Abspielen" and b.disabled for b in at.button)
    assert _has(at, "Es kommt gar nichts an") and any("Die letzte Breitensuche" in c.value for c in at.caption)


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(lambda a: a.session_state.__setitem__("net_select", net)))
    random_labels, fixed = labels_for("random"), labels_for("stair")
    assert {"Netz", "Blockierender Fluss", "Werke", "Verteilzentren", "Filialen", "Netzdichte [%]", "Streuung der Lane-Breiten [%]", "Auslastung [% der Werkskapazität]", "Zufalls-Seed"} <= random_labels
    assert fixed == {"Netz", "Blockierender Fluss"}                                          # keine toten Regler bei festen Netzen


def test_hidden_slider_values_come_back_when_the_random_net_is_shown_again():
    at = _run(lambda a: a.session_state.__setitem__("density_slider", 80))
    at.session_state["net_select"] = "stair"
    at.run()
    at.session_state["net_select"] = "random"
    at.run()
    assert not at.exception and at.slider(key="density_slider").value == 80


def test_step_slider_returns_to_the_last_frame_when_the_net_changes():
    at = _run()
    assert _step(at).max == 12 and _step(at).value == 12                                     # 2 Phasen: (1 + 8) + (1 + 2) Bilder + Endbild
    _step(at).set_value(4)
    at.run()
    assert _step(at).value == 4
    at.session_state["net_select"] = "assignment"
    at.run()
    assert not at.exception and _step(at).value == 6 == _step(at).max                       # 1 Phase: 1 + 5 Bilder + Endbild


def test_step_zero_shows_the_level_graph_and_a_middle_step_shows_a_path():
    at = _run()
    _step(at).set_value(0)
    at.run()
    assert not at.exception and any(c.value.startswith("Die Breitensuche hat") and "T hat das Niveau 5" in c.value for c in at.caption)
    _step(at).set_value(2)
    at.run()
    assert not at.exception and any(c.value.startswith("Weg 2:") for c in at.caption)


def test_a_back_arc_path_is_announced():
    at = _run()
    _step(at).set_value(11)                                                                  # zweiter Weg der zweiten Phase
    at.run()
    assert not at.exception and any("**Rückkante**" in c.value for c in at.caption)


def test_play_runs_through_all_frames_without_duplicate_chart_keys():
    """Beim Abspielen entstehen in einem Lauf mehrere Diagramme mit demselben Namen - die Schlüssel tragen deshalb den Schritt (Regression: StreamlitDuplicateElementKey bei mehr als einem Bild)."""
    at = _run(lambda a: a.session_state.__setitem__("net_select", "assignment"))
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_permalink_parameters_are_clamped_and_snapped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "9999"
    at.query_params["spread"] = "abc"
    at.query_params["p"] = "-5"
    at.run()
    assert not at.exception
    assert at.slider(key="density_slider").value == C.DENSITY_MAX and at.slider(key="spread_slider").value == C.DEFAULT_SPREAD and at.slider(key="p_slider").value == C.P_MIN
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["density"] = "63"
    at.query_params["spread"] = "60"
    at.query_params["load"] = "94"
    at.run()
    assert at.slider(key="density_slider").value == 60 and at.slider(key="spread_slider").value == 50 and at.slider(key="load_slider").value == 90   # auf die Regler-Schritte gerundet


def test_unknown_values_in_the_permalink_fall_back_to_the_defaults():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.query_params["blocking"] = "sprung"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET and at.radio(key="blocking_radio").value == C.DEFAULT_BLOCKING


def test_randomize_moves_the_seed_but_not_the_distribution():
    at = _run()
    pick = lambda a: ([m.value for m in a.metric if m.label == "Phasen"][1], _metric(a, "Dinic günstiger"), [m.value for m in a.metric if m.label == "Wege"][1])
    before = pick(at)
    seed_before = at.number_input(key="seed_input").value
    [b for b in at.sidebar.button if "Neues Netz" in b.label][0].click()
    at.run()
    assert not at.exception and at.number_input(key="seed_input").value != seed_before and pick(at) == before


def test_experiments_run_on_demand():
    at = _run()
    assert not any("Mittel über 10 feste Netze je Größe" in c.value for c in at.caption)
    assert not any("Rechts zufällige bipartite Netze" in c.value for c in at.caption)
    for key in ("scaling_start", "unit_start"):
        at.button(key=key).click()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    text = " ".join(c.value for c in at.caption)
    assert "Mittel über 10 feste Netze je Größe" in text and "Rechts zufällige bipartite Netze" in text


def test_pointer_experiment_on_a_fixed_net_shows_a_hint_instead_of_dead_controls():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "stair"))
    assert sum("zufälliges Distributionsnetz wählen" in t for t in _texts(at)) >= 2


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    assert len(calls) == 9 and all(re.search(r'key=f?"[a-z_]+(_\{\w+\})?"', c) for c in calls), calls
    assert len({re.search(r'key=f?"([a-z_]+?)(?:_\{\w+\})?"', c).group(1) for c in calls}) == 9            # jeder Schlüssel nur einmal
    viz = (ROOT / "dn_visualization.py").read_text(encoding="utf-8")
    bodies = [b for b in viz.split(chr(10) + "def ") if b.startswith("build_")]
    assert "fixedrange=True" in viz and len(bodies) == 7 and all("_base(" in b or "_layout(" in b for b in bodies)


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_footer_is_verbatim():
    src = APP.read_text(encoding="utf-8")
    assert "https://sebastianhanisch.net/kontakt.html" in src and "Interesse an einer maßgeschneiderten Lösung für" in src and "Operations Research und Machine Learning" in src


def test_runtime_needs_only_numpy_pandas_plotly_streamlit():
    """Konvention der Konzepte-Wurzeln und -Stücke: Referenzbibliotheken (scipy, networkx) nur als Testorakel."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "scipy" not in req and "networkx" not in req
    for path in ROOT.glob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+(scipy|networkx)\b", path.read_text(encoding="utf-8"), re.M), path.name
