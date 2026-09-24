"""Dinic - Niveaugraph und blockierender Fluss - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Dinics Phasen aus Niveaugraph und blockierendem Fluss - und lässt stattdessen das Beispiel wachsen.
Zweites Stück der Netzwerkfluss-Linie der "Konzepte"-Reihe, Fortsetzung der Demo "Edmonds-Karp": sie behebt deren Schwäche (eine Breitensuche je Weg). Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import dn_constants as C
import dn_evaluation as ev
import dn_scenario as sc
from dn_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from dn_scenario import build
from dn_visualization import (
    build_flow,
    build_gain,
    build_levels,
    build_phase_bars,
    build_phase_hist,
    build_scaling,
    build_unit,
)

st.set_page_config(page_title="Dinic – Sebastian Hanisch", layout="wide")


def _pct(x, digits=0):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _int(x):
    return f"{int(round(x)):,}".replace(",", " ")


def _route(net, nodes):
    return " → ".join(net.names[v] for v in nodes)


def _stage_text(stage_caps):
    parts = [f"{sc.KIND_LABELS[k]} {v}" for k, v in stage_caps.items() if k in ev.STAGE_KINDS]
    return ", ".join(parts)


@st.cache_resource(show_spinner=False, max_entries=32)
def _analysis(params, current_arc):
    return ev.analyse(build(*params), current_arc)


st.title("🌐 Dinic – Niveaugraph und blockierender Fluss")
st.markdown(
    """
Edmonds-Karp sucht für **jeden** Weg eine neue Breitensuche - und wirft dabei fast alles wieder weg, was sie über das Netz gelernt hat. **Dinic** nutzt sie besser:
eine Breitensuche gibt jedem Knoten sein **Niveau** (seine Entfernung von der Quelle S), der **Niveaugraph** enthält nur Kanten von Niveau k nach k + 1, und darin füllt eine Tiefensuche **alle** kürzesten Wege auf,
bis kein Weg mehr übrig ist - der **blockierende Fluss**. Danach ist die Entfernung von S nach T echt größer geworden, eine neue **Phase** beginnt. Es gibt höchstens |V| − 1 Phasen, auf den Netzen dieser Demo sind es im Mittel weniger als zwei.
Diese Demo zeigt, wie viel Suchaufwand das spart, wie eine **Zeigerliste** Sackgassen nur einmal besuchen lässt, und wo der Vorsprung klein bleibt.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - zweites Stück der Netzwerkfluss-Linie der \"Konzepte\"-Reihe, Fortsetzung der Demo \"Edmonds-Karp\" - **ein** Verfahren an einem wachsenden Beispiel. "
    "Auf Einheitsnetzen ist Dinic der Algorithmus von **Hopcroft–Karp** aus der Matching-Linie. Die Schwächen dieses Stücks sind die Ansatzpunkte der nächsten: **Push-Relabel** (Fluss ohne Wege, gebaut) und **Successive Shortest Paths** (die Kosten entscheiden, gebaut)."
)

with st.expander("So funktioniert Dinic", expanded=True):
    st.markdown(
        """
1. **Niveaugraph:** eine Breitensuche im Restgraphen gibt jedem Knoten sein Niveau, die Zahl der Kanten des kürzesten Weges von S. Sie hält an, sobald T erreicht ist. Im Niveaugraph zählen nur Restkanten von Niveau $k$ nach $k+1$ - jeder S-T-Weg darin ist ein *kürzester* Weg und hat genau $L$ Kanten, wenn T das Niveau $L$ hat.
2. **Blockierender Fluss:** eine Tiefensuche von S nach T durch den Niveaugraph, aufgefüllt um den Engpass; dann sucht sie von S weiter, bis kein Weg mehr existiert. Danach ist jeder S-T-Weg im Niveaugraph an mindestens einer Kante gesperrt.
3. **Phasen:** nach dem blockierenden Fluss ist die Entfernung von S nach T mindestens um 1 gewachsen. Die nächste Phase baut den Niveaugraph neu auf - jetzt mit längeren Wegen, oft über **Rückkanten**. Entfernung und Niveau von T wachsen echt, also gibt es höchstens $|V|-1$ Phasen.
4. **Zeigerliste:** je Knoten merkt die Tiefensuche, ab welcher Kante es sich lohnt weiterzusuchen. Kanten davor sind voll oder führen in **Sackgassen** (Kreuze in der Abbildung) und werden in dieser Phase nie wieder angesehen. Ohne Zeigerliste beginnt jede Wegesuche je Knoten wieder bei der ersten Kante - gleiche Wege, mehr Aufwand.
5. **Beweis:** wie bei Edmonds-Karp: scheitert die Breitensuche, sind die von S erreichbaren Knoten der minimale Schnitt, seine Kapazität ist der Flusswert.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielnetz laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Netz", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Ein zufälliges Distributionsnetz, oder eines der festen Einheitsnetze: die Treppe braucht 6 Phasen, die Zuordnungskette eine (Dinic auf Einheitsnetzen ist Hopcroft–Karp).",
    )
    blocking = st.radio(
        "Blockierender Fluss", list(C.BLOCKING_LABELS), key="blocking_radio", format_func=lambda k: C.BLOCKING_LABELS[k],
        help="Mit oder ohne Zeigerliste: dieselben Wege, aber ohne Zeiger besucht die Tiefensuche Sackgassen immer wieder. Bei den Standardeinstellungen durchsucht Dinic über 100 Netze im Mittel 254 Kanten mit und 436 ohne Zeigerliste (Edmonds-Karp: 525).",
    )
    if net_key == "random":
        p = st.slider("Werke", *bounds("p_slider"), key="p_slider", help="Anzahl der Werke (oben im Netz).")
        st.session_state[KEPT["p_slider"]] = p
        d = st.slider("Verteilzentren", *bounds("d_slider"), key="d_slider", help="Anzahl der Verteilzentren; jedes hat einen Durchsatz von 30 bis 60 % der gesamten Werkskapazität.")
        st.session_state[KEPT["d_slider"]] = d
        s = st.slider("Filialen", *bounds("s_slider"), key="s_slider", help="Anzahl der Filialen (unten im Netz).")
        st.session_state[KEPT["s_slider"]] = s
        density = st.slider("Netzdichte [%]", *bounds("density_slider"), key="density_slider", step=10, help="Anteil der möglichen Lanes (Werk → Verteilzentrum, Verteilzentrum → Filiale), die es gibt. Bei 100 % genügt fast immer eine Phase (im Mittel 1,0), bei mittlerer Dichte sind es die meisten (Höhepunkt bei 60 %: 1,7).")
        st.session_state[KEPT["density_slider"]] = density
        spread = st.slider("Streuung der Lane-Breiten [%]", *bounds("spread_slider"), key="spread_slider", step=25, help="0 = alle Lanes einer Stufe gleich breit, 100 = Kapazitäten gleichverteilt von 1 bis zum Doppelten der Grundbreite.")
        st.session_state[KEPT["spread_slider"]] = spread
        load = st.slider("Auslastung [% der Werkskapazität]", *bounds("load_slider"), key="load_slider", step=10, help="Gesamtnachfrage der Filialen in Prozent der gesamten Werkskapazität. Über 100 % können die Werke die Nachfrage nie decken. Bei 40 % genügt fast immer eine Phase (1,05), bei 120 % sind es im Mittel 1,8.")
        st.session_state[KEPT["load_slider"]] = load
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neues Netz generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilungen über 100 feste Netze weiter unten ändern sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        p = int(st.session_state.get(KEPT["p_slider"], C.DEFAULT_P))
        d = int(st.session_state.get(KEPT["d_slider"], C.DEFAULT_D))
        s = int(st.session_state.get(KEPT["s_slider"], C.DEFAULT_S))
        density = int(st.session_state.get(KEPT["density_slider"], C.DEFAULT_DENSITY))
        spread = int(st.session_state.get(KEPT["spread_slider"], C.DEFAULT_SPREAD))
        load = int(st.session_state.get(KEPT["load_slider"], C.DEFAULT_LOAD))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Dieses Netz ist fest - es gibt nichts zu erzeugen. Zahl der Werke, Verteilzentren und Filialen, Netzdichte, Streuung, Auslastung und Seed gehören zum zufälligen Netz.")

sync_query_params({"net_select": net_key, "blocking_radio": blocking, "p_slider": int(p), "d_slider": int(d), "s_slider": int(s), "density_slider": int(density),
                   "spread_slider": int(spread), "load_slider": int(load), "seed_input": int(seed)})

# feste Netze ignorieren die Zufallsregler: sonst würden gleiche Netze unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(p), int(d), int(s), int(density), int(spread), int(load), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_P, C.DEFAULT_D, C.DEFAULT_S, C.DEFAULT_DENSITY, C.DEFAULT_SPREAD, C.DEFAULT_LOAD, C.DEFAULT_SEED)
use_pointer = blocking == "pointer"
with st.spinner("Rechne..."):
    a = _analysis(params, use_pointer)
net, res, ekres = a.net, a.result, a.edmonds_karp
level, code, dat = ev.verdict(a)
settings = (int(p), int(d), int(s), int(density), int(spread), int(load))
fr = ev.frames(res)
n_frames = len(fr)

# --- Phasen in Aktion -------------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Phasen in Aktion")
if st.session_state.get("dn_step_owner") != (params, use_pointer):
    st.session_state["dn_step"] = n_frames - 1
    st.session_state["dn_step_owner"] = (params, use_pointer)
step_col, play_col = st.columns([5, 2])
with step_col:
    if n_frames > 1:
        step = st.slider("Bild", 0, n_frames - 1, key="dn_step", help="Je Phase ein Bild mit dem Niveaugraph und je Weg des blockierenden Flusses ein weiteres; ganz rechts der fertige Fluss und der Beweis.")
    else:
        step = 0
        st.caption("Hier gibt es keine Phase: von S aus kommt nichts zu T. Rechts der Beweis dafür.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_frames <= 1)
view_slot = st.empty()


def _render(k):
    """Bild k: links der Niveaugraph der Phase (mit den bisherigen Wegen), rechts der Fluss; am Ende der Beweis."""
    with view_slot.container():
        ph_idx, stage = fr[k]
        c1, c2 = st.columns(2)
        if ph_idx >= len(res.phases):
            c1.markdown(f"**Ergebnis** - Flusswert {res.value}")
            c1.plotly_chart(build_flow(net, res.flow), width="stretch", key=f"result_map_{k}")
            c2.markdown(f"**Beweis:** ein Schnitt der Kapazität {res.cut_capacity}")
            c2.plotly_chart(build_flow(net, res.flow, cut=res.cut_arcs, reach=res.reach), width="stretch", key=f"proof_map_{k}")
            st.caption(f"Die letzte Breitensuche ({res.final_scanned} durchsuchte Kanten) erreicht T nicht mehr. Die grünen Knoten sind von S aus noch erreichbar; die {len(res.cut_arcs)} roten Kanten führen aus dieser Menge heraus und sind alle voll. "
                       f"Ihre Kapazitäten summieren sich auf {res.cut_capacity} - genau der Flusswert. Mehr kann kein Fluss.")
            return
        ph = res.phases[ph_idx]
        c1.markdown(f"**Phase {ph_idx + 1} von {len(res.phases)}** - " + ("Niveaugraph" if stage == 0 else f"Weg {stage} von {len(ph.paths)}"))
        flow = ph.flow_before if stage == 0 else ph.paths[stage - 1].flow_after
        value = ph.value_before if stage == 0 else ph.value_before + sum(x.bottleneck for x in ph.paths[:stage])
        c2.markdown(f"**Fluss** - Flusswert {value}")
        c1.plotly_chart(build_levels(net, ph, stage), width="stretch", key=f"level_map_{k}")
        c2.plotly_chart(build_flow(net, flow, path={e // 2 for e in ph.paths[stage - 1].arcs} if stage else None), width="stretch", key=f"flow_map_{k}")
        if stage == 0:
            cap = (f"Die Breitensuche hat {ph.bfs_scanned} Kanten durchsucht und endet, sobald T erreicht ist: T hat das Niveau {ph.level}, jeder kürzeste Weg dieser Phase hat {ph.level} Kanten. "
                   f"Die Farbe eines Knotens ist sein Niveau; dunkle Kanten sind Restkanten von Niveau k nach k + 1 (in dieser Phase {len(ph.level_arcs)}).")
        else:
            path = ph.paths[stage - 1]
            so_far = sum(x.scanned for x in ph.paths[:stage])
            back = " Der Weg nimmt gelegten Fluss über eine **Rückkante** zurück." if path.uses_back_arc else ""
            cap = (f"Weg {stage}: {_route(net, path.nodes)}, um {path.bottleneck} aufgefüllt.{back} Die Tiefensuche hat bis hier {so_far} Kanten durchsucht, davon {path.scanned} für diesen Weg (Sackgassen davor: {len(path.dead)}).")
            if stage == len(ph.paths):
                cap += (f" Damit ist der Fluss in dieser Phase blockierend: {ph.tail_scanned} Kanten danach noch vergeblich durchsucht, {len(ph.tail_dead)} weitere Sackgassen. "
                        f"Flusswert {ph.value_before} → {ph.value_after}.")
        st.caption(cap)


if auto_play:
    for k in range(n_frames):
        _render(k)
        time.sleep(min(0.8, 8.0 / max(n_frames, 1)))
    step = n_frames - 1
else:
    _render(step)

st.plotly_chart(build_phase_bars(res), width="stretch", key="phase_chart")
st.caption("Knotenfarbe = Niveau (Entfernung von S in Kanten); grau hohl: nicht im Niveaugraph. Dunkelblau: Restkanten des Niveaugraphen, orange gestrichelt: Rückkanten, hellgrün: frühere Wege der Phase, grün dick: der aktuelle Weg (beschriftet mit seinem Engpass), blass gepunktet: gesperrte (volle) Kanten. "
           "Violette Kreuze: Sackgassen der Tiefensuche. Rechts der Fluss (Breite ~ Fluss, dunkelblau = Kante voll). Unten die durchsuchten Kanten je Phase, getrennt nach Breiten- und Tiefensuche.")

st.markdown("---")

# --- Muss man für jeden Weg neu suchen? -----------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Muss man für jeden Weg neu suchen?")
st.caption("**Phasen** = Zahl der Niveaugraphen, die Dinic aufbaut; **Wege** = Zahl der aufgefüllten Verbesserungswege (Edmonds-Karp braucht für jeden eine eigene Breitensuche); **durchsuchte Kanten** = Aufwand aus Breiten- und Tiefensuche, maschinenunabhängig gezählt.")
m1, m2, m3, m4 = st.columns(4)
if net.logistic:
    m1.metric("Flusswert", f"{dat['value']} von {dat['demand']}", delta=f"{_f(dat['share'])} % der Nachfrage", delta_color="off", help="Größte Liefermenge des Netzes und die Gesamtnachfrage der Filialen.")
else:
    m1.metric("Flusswert", f"{dat['value']}", help="Größte Menge von S nach T.")
m2.metric("Phasen", f"{dat['phases']}", delta="Niveau " + ", ".join(str(x) for x in dat["levels"]) if dat["levels"] else "keine", delta_color="off", help="Niveau von T je Phase = Länge der Wege in dieser Phase; es wächst von Phase zu Phase.")
m3.metric("Wege", f"{dat['paths']}", delta=f"je Phase: {', '.join(str(x) for x in dat['paths_per_phase'])}" if dat["paths"] else "keiner nötig", delta_color="off",
          help=f"Aufgefüllte Verbesserungswege in den Phasen; {dat['back_paths']} davon über Rückkanten. Edmonds-Karp füllt auf demselben Netz {dat['ek_rounds']} Wege auf.")
m4.metric("Durchsuchte Kanten", f"{dat['scanned']}", delta=f"Edmonds-Karp: {dat['ek_scanned']}", delta_color="off",
          help=f"Breitensuchen {dat['bfs_scanned']} (einschließlich der letzten erfolglosen), Tiefensuchen {dat['dfs_scanned']}; Edmonds-Karp durchsucht auf demselben Netz {dat['ek_scanned']} Kanten.")

if code == "delivered":
    st.success(f"✅ Die gesamte Nachfrage ({dat['demand']}) wird geliefert, in {dat['phases']} Phase(n) mit {dat['paths']} Weg(en). Dinic durchsucht {dat['scanned']} Kanten, Edmonds-Karp {dat['ek_scanned']}.")
elif code == "disconnected":
    st.warning("⚠️ Es kommt gar nichts an: kein Weg führt von einem Werk über ein Verteilzentrum zu einer Filiale. Der Flusswert ist 0, es gibt keine Phase, der Schnitt ist leer. Mehr Netzdichte oder weniger Verteilzentren verbinden die Stufen.")
elif code == "bottleneck":
    covered = dat["stage_caps"].get(sc.K_DEMAND, 0)
    extra = f" (dazu {covered} Einheiten Nachfrage schon gedeckter Filialen)" if covered else ""
    st.warning(f"⚠️ Das Netz schafft höchstens **{dat['value']} von {dat['demand']}** Einheiten ({_f(dat['share'], 0)} %). Engpass: **{_stage_text(dat['stage_caps'])}**{extra}. "
               f"{dat['phases']} Phase(n) mit {dat['paths']} Wegen; Dinic durchsucht {dat['scanned']} Kanten, Edmonds-Karp {dat['ek_scanned']}.")
else:
    st.info(f"ℹ️ Flusswert {dat['value']} in {dat['phases']} Phase(n) mit {dat['paths']} Weg(en) (Niveau {', '.join(str(x) for x in dat['levels'])}); Dinic durchsucht {dat['scanned']} Kanten, Edmonds-Karp {dat['ek_scanned']}.")

if net_key in C.FIXED_NETS:
    st.info("Festes Netz: es gibt nur diese eine Ziehung. Für die Verteilungen über viele Netze ein zufälliges Distributionsnetz wählen.")
else:
    st.markdown(f"**Nicht nur dieses eine Netz:** {len(C.DIST_SEEDS)} feste Netze mit denselben Einstellungen (Werke {p}, Verteilzentren {d}, Filialen {s}, Netzdichte {density} %, Streuung {spread} %, Auslastung {load} %), getrennt vom Seed oben.")
    dist = ev.distribution(*settings)
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Phasen", _f(dist["phases_mean"], 1), delta=f"Median {_f(dist['phases_median'], 0)}, höchstens {dist['phases_max']}", delta_color="off", help="Mittel der Phasenzahl über die Netze. Edmonds-Karp braucht dieselben Wege einzeln.")
    p2.metric("Wege", _f(dist["paths_mean"], 1), delta=f"{_f(dist['paths_per_phase_mean'], 1)} je Phase", delta_color="off", help="Mittel der aufgefüllten Wege; auf allen 100 Netzen sind es so viele wie bei Edmonds-Karp (Dinic ändert nicht die Wege, sondern wie oft gesucht wird).")
    p3.metric("Durchsuchte Kanten", _f(dist["dinic_mean"], 0), delta=f"Edmonds-Karp {_f(dist['ek_mean'], 0)}", delta_color="off", help="Mittel über die Netze: Dinic mit Zeigerliste gegen Edmonds-Karp.")
    p4.metric("Dinic günstiger", _share(dist["share_le_ek"]), delta=f"Median {_f(dist['dinic_median'], 0)} gegen {_f(dist['ek_median'], 0)}", delta_color="off", help="Anteil der Netze, in denen Dinic höchstens so viele Kanten durchsucht wie Edmonds-Karp; im Delta die Mediane.")
    if dist["share_le_ek"] >= 0.5:
        st.success(f"✅ In {_share(dist['share_le_ek'])} der {dist['n_seeds']} Netze durchsucht Dinic höchstens so viele Kanten wie Edmonds-Karp - im Mittel {_f(dist['dinic_mean'], 0)} statt {_f(dist['ek_mean'], 0)}, bei {_f(dist['phases_mean'], 1)} statt {_f(dist['ek_rounds_mean'], 1)} Suchdurchgängen.")
    else:
        st.warning(f"⚠️ Nur in {_share(dist['share_le_ek'])} der {dist['n_seeds']} Netze durchsucht Dinic höchstens so viele Kanten wie Edmonds-Karp.")
    st.plotly_chart(build_phase_hist(dist["cols"]["phases"], dist["cols"]["ek_rounds"], current=dat["phases"] if net.logistic else None), width="stretch", key="phase_hist")
    st.markdown("**Aufwand der drei Verfahren** (Mittel und Median über die Netze; durchsuchte Kanten statt Sekunden):")
    st.table({"Verfahren": ["Dinic mit Zeigerliste", "Dinic ohne Zeigerliste", "Edmonds-Karp"],
              "Suchdurchgänge": [f"{_f(dist['phases_mean'])} Phasen", f"{_f(dist['phases_mean'])} Phasen", f"{_f(dist['ek_rounds_mean'])} Wege"],
              "durchsuchte Kanten (Mittel)": [_f(dist["dinic_mean"], 0), _f(dist["nopointer_mean"], 0), _f(dist["ek_mean"], 0)],
              "durchsuchte Kanten (Median)": [_f(dist["dinic_median"], 0), _f(dist["nopointer_median"], 0), _f(dist["ek_median"], 0)],
              "größter Wert": [dist["dinic_max"], dist["nopointer_max"], dist["ek_max"]]})
    st.caption(f"Das Netz hat im Mittel {_f(dist['edges_mean'], 0)} Kanten und {_f(dist['nodes_mean'], 0)} Knoten. Von den durchsuchten Kanten entfallen bei Dinic im Mittel {_f(dist['bfs_mean'], 0)} auf die Breitensuchen und {_f(dist['dfs_mean'], 0)} auf die Tiefensuchen.")

st.markdown("---")

# --- Vergleich ---------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – Verfahren im Vergleich"):
    st.markdown("**Was jedes Verfahren für das Netz oben findet**")
    other = _analysis(params, not use_pointer)
    modes = {True: a if use_pointer else other, False: other if use_pointer else a}
    rows = []
    for label, r in (("Dinic mit Zeigerliste", modes[True].result), ("Dinic ohne Zeigerliste", modes[False].result)):
        dead = sum(len(x.dead) for ph in r.phases for x in ph.paths) + sum(len(ph.tail_dead) for ph in r.phases)
        rows.append((label, r.value, f"{len(r.phases)} Phasen", r.n_paths, r.scanned_total, dead))
    rows.append(("Edmonds-Karp", ekres.value, f"{len(ekres.rounds)} Wege", len(ekres.rounds), ekres.scanned_total, "–"))
    st.table({"Verfahren": [r[0] for r in rows], "Flusswert": [r[1] for r in rows], "Suchdurchgänge": [r[2] for r in rows], "Wege": [r[3] for r in rows], "durchsuchte Kanten": [r[4] for r in rows], "Sackgassen-Besuche": [str(r[5]) for r in rows]})
    st.caption("Alle drei erreichen denselben Flusswert und finden denselben Schnitt. Dinic mit und ohne Zeigerliste füllen genau dieselben Wege auf; sie unterscheiden sich nur in den Sackgassen-Besuchen und damit im Aufwand.")
    st.markdown("**Protokoll der Phasen** (aktuelle Einstellung)")
    if res.phases:
        st.dataframe({"Phase": list(range(1, len(res.phases) + 1)), "Niveau von T": [ph.level for ph in res.phases], "Wege": [len(ph.paths) for ph in res.phases],
                      "davon über Rückkanten": [sum(1 for x in ph.paths if x.uses_back_arc) for ph in res.phases], "Breitensuche (Kanten)": [ph.bfs_scanned for ph in res.phases],
                      "Tiefensuche (Kanten)": [ph.dfs_scanned for ph in res.phases], "Flusswert danach": [ph.value_after for ph in res.phases]}, hide_index=True, width="stretch")
    else:
        st.caption("Keine Phase: von S aus ist T nicht erreichbar.")

st.markdown("---")

# --- Experimente -------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Wächst der Suchaufwand langsamer als bei Edmonds-Karp?")
st.caption("Edmonds-Karp durchsucht bei wachsendem Netz schneller als die Kantenzahl (Steigung 1,7 bis 1,9 in der Demo dazu). Dinic baut je Phase einen Niveaugraph und sucht darin mit Zeigerliste; wie wächst sein Aufwand?")
if st.button("Netze von 12 bis 166 Knoten durchrechnen (dauert einige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 6 Netzgrößen × 10 Netze × 3 Verfahren..."):
        sc_rows = ev.scaling()
    slopes = ev.slopes(sc_rows)
    c1, c2 = st.columns(2)
    c1.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
    c2.plotly_chart(build_gain(sc_rows), width="stretch", key="gain_chart")
    st.table({"Werke / DCs / Filialen": [f"{r['size'][0]} / {r['size'][1]} / {r['size'][2]}" for r in sc_rows], "Knoten": [_f(r["n"], 0) for r in sc_rows], "Kanten": [_f(r["m"], 0) for r in sc_rows],
              "Phasen": [_f(r["phases"]) for r in sc_rows], "Wege": [_f(r["paths"]) for r in sc_rows], "Dinic": [_int(r["dinic"]) for r in sc_rows], "ohne Zeigerliste": [_int(r["nopointer"]) for r in sc_rows],
              "Edmonds-Karp": [_int(r["ek"]) for r in sc_rows], "Edmonds-Karp ÷ Dinic": [_f(r["ek"] / r["dinic"], 1) for r in sc_rows], "ohne ÷ mit Zeigerliste": [_f(r["nopointer"] / r["dinic"], 1) for r in sc_rows]})
    st.caption(f"Mittel über 10 feste Netze je Größe (Netzdichte, Streuung und Auslastung auf den Standardwerten); durchsuchte Kanten, nicht Sekunden. Steigung im doppelt logarithmischen Diagramm: Dinic {_f(slopes['dinic'], 2)}, Dinic ohne Zeigerliste {_f(slopes['nopointer'], 2)}, Edmonds-Karp {_f(slopes['ek'], 2)}. "
               "Je größer das Netz, desto mehr spart die Zeigerliste, und desto größer ist der Abstand zu Edmonds-Karp - bei den kleinsten Netzen ist er gering. Auf diesen geschichteten Netzen genügt bei den großen Netzen schon **eine** Phase: alle Wege sind gleich lang.")

st.subheader("🔬 Was leistet die Zeigerliste?")
if net_key in C.FIXED_NETS:
    st.info("Für die Verteilung ein zufälliges Distributionsnetz wählen. Auf den festen Netzen zeigt der Vergleich im Expander oben die Sackgassen-Besuche mit und ohne Zeigerliste.")
else:
    dist = ev.distribution(*settings)
    factors = [b / a_ for a_, b in zip(dist["cols"]["dinic"], dist["cols"]["nopointer"])]
    q1, q2, q3 = st.columns(3)
    q1.metric("Aufwand ohne ÷ mit Zeigerliste (Mittel)", _f(dist["nopointer_mean"] / dist["dinic_mean"], 2), help="Mittel der durchsuchten Kanten ohne Zeigerliste geteilt durch das Mittel mit Zeigerliste.")
    q2.metric("Größter Faktor eines Netzes", _f(max(factors), 1), help="Das Netz mit dem größten Unterschied zwischen ohne und mit Zeigerliste.")
    q3.metric("Netze mit gleichem Aufwand", _share(sum(1 for f in factors if f == 1) / len(factors)), help="Anteil der Netze, in denen die Zeigerliste nichts einspart (keine Sackgasse besucht).")
    st.caption("Beide Varianten füllen auf jedem Netz genau dieselben Wege auf; die Zeigerliste spart nur Sackgassen-Besuche. Sie ändert nicht die Zahl der Phasen, aber den Aufwand je Phase: jede Kante wird pro Phase höchstens einmal als Sackgasse oder als gesperrte Kante angesehen.")

st.subheader("🔬 Einheitsnetze: Dinic ist Hopcroft–Karp")
st.caption("Auf Netzen mit lauter Kapazität 1 (Zuordnung von Fahrzeugen zu Aufträgen) sind die Phasen von Dinic genau die von Hopcroft–Karp; ihre Zahl ist höchstens etwa $2\\sqrt{n}$. Die **Treppe** aus der Hopcroft–Karp-Demo treibt sie am höchsten (etwa $\\sqrt{2n}$), Zufallsnetze bleiben weit darunter.")
if st.button("Einheitsnetze durchrechnen (dauert wenige Sekunden)", key="unit_start"):
    st.session_state["unit_on"] = True
if st.session_state.get("unit_on"):
    with st.spinner("Rechne Treppen und Zufallsnetze..."):
        stair_rows, unit_rows = ev.stair_table(), ev.unit_random()
    st.plotly_chart(build_unit(stair_rows, unit_rows), width="stretch", key="unit_chart")
    u1, u2 = st.columns(2)
    u1.table({"Ketten k": [r["k"] for r in stair_rows], "Fahrzeuge = Aufträge": [r["n"] for r in stair_rows], "Phasen": [r["phases"] for r in stair_rows], "Wege": [r["ek_rounds"] for r in stair_rows]})
    u2.table({"Fahrzeuge = Aufträge": [r["n"] for r in unit_rows], "Phasen (Mittel)": [_f(r["phases_mean"]) for r in unit_rows], "Phasen (höchstens)": [r["phases_max"] for r in unit_rows], "Schranke 2·√n": [_f(r["bound"]) for r in unit_rows]})
    st.caption("Links die Treppe: k + 1 Phasen bei k (k + 3) / 2 Fahrzeugen - Kette t braucht einen eigenen Verbesserungsweg mit 2t + 3 Kanten, jede Phase also einen längeren; Wege gibt es so viele wie Fahrzeuge. "
               "Rechts zufällige bipartite Netze (jedes Fahrzeug mit 3 Aufträgen verbunden, Mittel über 20 feste Netze je Größe): die Phasenzahl wächst nur langsam und bleibt unter der Schranke.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Nur die Menge zählt** | Dinic füllt dieselben Wege auf wie Edmonds-Karp und ist genauso kostenblind: welche Lanes der Fluss benutzt, entscheidet die Reihenfolge der Kanten, nicht der Preis. | **Successive Shortest Paths**: der billigste Weg im Restgraphen entscheidet |
| **Fluss wird über Wege gebaut** | Auch Dinic legt den Fluss Weg für Weg. Im schlechtesten Fall kostet das $O(V^2 E)$; auf den Netzen dieser Demo braucht es weit weniger als $|V|-1$ Phasen (höchstens 4 von 18 auf den Standardnetzen), aber die Schranke bleibt. | **Push-Relabel** (gebaut): Überschüsse lokal schieben, Höhen anheben |
| **Die Wege sind gleich lang** | Auf dem geschichteten Distributionsnetz genügt bei größeren Netzen meist **eine** Phase. Mehr als zwei Phasen gibt es dort selten (im Mittel 1,7, höchstens 4); erst Einheitsnetze wie die Treppe treiben die Phasenzahl hoch - und dort ist der Vorsprung gegen Edmonds-Karp klein. | Die Treppe zeigt die Grenze |
| **Ein Gut, teilbar** | Alle Waren sind gleich und beliebig teilbar. Mehrere Güter auf gemeinsamen Kanten machen den Fluss im Allgemeinen gebrochen. | **Mehrgüterfluss** (gebaut: multicommodity-demo) |
| **Ein Zeitpunkt** | Das Netz gilt für eine Periode; wer über mehrere Perioden mit Lagerhaltung plant, dehnt das Netz zeitlich aus. | Fall-Demo \"Distributionsnetzwerk-Optimierung\" |
"""
)
st.caption("Die Netzwerkfluss-Linie ist als Ganzes geplant: Edmonds-Karp, Dinic (dieses Stück), Push-Relabel (gebaut), Successive Shortest Paths (gebaut), Cycle-Canceling (gebaut), Cost Scaling (gebaut), Mehrgüterfluss (gebaut), Column Generation (gebaut), Garg-Könemann (gebaut), Fixkosten-Netzwerkdesign, Benders-Zerlegung und Slope Scaling - bisher sind die ersten neun gebaut.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Wie in der Edmonds-Karp-Demo: gerichteter Graph $G=(V,E)$ mit Quelle $s$, Senke $t$, ganzzahligen Kapazitäten $c_e$; ein Fluss $f$ mit $0\le f_e\le c_e$ und Flusserhaltung; Restgraph $G_f$ mit Vorwärtskante (Rest $c_e-f_e$) und Rückkante (Rest $f_e$).

**Niveau.** $\ell_f(v)$ sei die Zahl der Kanten eines kürzesten $s$-$v$-Weges in $G_f$. Der **Niveaugraph** $L_f$ enthält die Restkanten $(u,v)$ mit $\ell_f(v)=\ell_f(u)+1$. Jeder $s$-$t$-Weg in $L_f$ ist ein kürzester Weg in $G_f$ und hat $\ell_f(t)$ Kanten.

**Blockierender Fluss.** Ein Fluss $g$ in $L_f$ (aufgefüllt Weg für Weg) heißt *blockierend*, wenn jeder $s$-$t$-Weg in $L_f$ eine durch $g$ volle Kante enthält. Ihn findet die Tiefensuche mit Zeigerliste in $O(|V|\cdot|E|)$: jede Kante wird als Sackgasse oder gesperrte Kante höchstens einmal übersprungen (insgesamt $O(|E|)$), und jeder der höchstens $|E|$ Wege kostet $O(|V|)$.

**Lemma.** Nach jeder Phase gilt $\ell_{f'}(t)>\ell_f(t)$. *Beweisskizze:* Neue Kanten im Restgraphen sind Rückkanten voller Niveaukanten und führen von Niveau $k+1$ nach $k$; ein Weg, der nur Niveaukanten und Rückkanten nutzt, wird mit jeder Rückkante länger. Ein Weg gleicher Länge bestünde nur aus Niveaukanten, wäre also durch den blockierenden Fluss gesperrt.

**Laufzeit.** Wegen $\ell(t)\le |V|-1$ gibt es höchstens $|V|-1$ Phasen: **$O(|V|^2\cdot|E|)$** im Allgemeinen. Auf Einheitsnetzen (alle Kapazitäten 1) dauert eine Phase $O(|E|)$, und nach $\sqrt{|E|}$ Phasen bleibt höchstens $\sqrt{|E|}$ Restfluss: **$O(|E|\sqrt{|E|})$**; für bipartite Zuordnung ist das der Algorithmus von Hopcroft und Karp mit $O(|E|\sqrt{|V|})$.

**Zeigerliste.** Ohne Zeiger beginnt die Tiefensuche je Weg bei der ersten Kante; die Wege sind dieselben (gesperrte Kanten und Sackgassen bleiben es innerhalb der Phase), aber jede Sackgasse kann je Weg wieder besucht werden: $O(|V|\cdot|E|)$ je Weg statt insgesamt je Phase.

**Beweis.** Wie bei Edmonds-Karp: scheitert die Breitensuche, ist $Z$ die von $s$ erreichbare Menge und $|f|=c(Z,\bar Z)$ (Max-Flow = Min-Cut).

Implementiert in `dn_scenario.py` (Netze, eigener Zufallsgenerator, Einheitsnetze), `dn_algorithm.py` (Niveaugraph, blockierender Fluss, Zeigerliste, Beweis), `dn_edmonds_karp.py` (Kopie der Vorgänger-Demo als Vergleichsbasis), `dn_evaluation.py` (Kennzahlen, Verteilungen, Experimente).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
