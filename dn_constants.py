"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Dinic: Niveaugraph und blockierender Fluss"."""

# --- Regler (wie in der Edmonds-Karp-Demo) ----------------------------------------------------------------------------------------
P_MIN, P_MAX, DEFAULT_P = 2, 6, 3            # Werke
D_MIN, D_MAX, DEFAULT_D = 2, 6, 3            # Verteilzentren
S_MIN, S_MAX, DEFAULT_S = 3, 12, 8           # Filialen
DENSITY_MIN, DENSITY_MAX, DEFAULT_DENSITY = 20, 100, 60   # Anteil vorhandener Lanes in ganzen Prozent, Schritt 10
SPREAD_MIN, SPREAD_MAX, DEFAULT_SPREAD = 0, 100, 50       # Streuung der Lane-Breiten in ganzen Prozent, Schritt 25
LOAD_MIN, LOAD_MAX, DEFAULT_LOAD = 40, 160, 90            # Gesamtnachfrage in Prozent der Werkskapazität, Schritt 10
DEFAULT_SEED = 43
SEED_MAX = 2_000_000_000

NETS = {
    "random": "Zufälliges Distributionsnetz",
    "stair": "Treppe (Einheitsnetz, fünf Ketten)",
    "assignment": "Zuordnung als Fluss (Kette, 5 + 5)",
}
DEFAULT_NET = "random"
FIXED_NETS = ("stair", "assignment")

BLOCKING_LABELS = {"pointer": "Mit Zeigerliste (Dinic)", "nopointer": "Ohne Zeigerliste (Sackgassen werden wiederbesucht)"}
DEFAULT_BLOCKING = "pointer"

# --- feste Seed-Mengen (dieselben wie in der Edmonds-Karp-Demo; unabhängig vom Nutzer-Seed) -----------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
SCALE_SIZES = ((2, 2, 4), (3, 3, 8), (4, 4, 16), (6, 6, 32), (8, 8, 64), (12, 12, 128))   # (Werke, DCs, Filialen)
SCALE_SEEDS = DIST_SEEDS[:10]
STAIR_KS = (1, 2, 3, 4, 5, 6, 8, 10, 12)
UNIT_SIZES = (10, 20, 40, 80, 160, 320)   # Einheitsnetze: Fahrzeuge = Aufträge
UNIT_DEGREE = 3
UNIT_SEEDS = DIST_SEEDS[:20]

COLORS = {
    "flow": "#1f77b4", "path": "#2ca02c", "back": "#ff7f0e", "cut": "#d62728", "reach": "#2ca02c", "dead": "#9467bd",
    "unreach": "#8c8c8c", "faint": "rgba(150,150,150,0.45)", "node": "#111111", "optimal": "#d62728", "levels": "Viridis",
}

# --- Presets -----------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", blocking=DEFAULT_BLOCKING, p=DEFAULT_P, d=DEFAULT_D, s=DEFAULT_S, density=DEFAULT_DENSITY, spread=DEFAULT_SPREAD, load=DEFAULT_LOAD, seed=DEFAULT_SEED)
PRESETS = {
    "🚚 Zufallsnetz": {**_BASE},
    "🧭 Ohne Zeigerliste": {**_BASE, "blocking": "nopointer"},
    "🕳️ Sackgassen": {**_BASE, "seed": 3},
    "🔁 Drei Phasen": {**_BASE, "p": 6, "d": 6, "s": 12, "density": 40, "spread": 100, "load": 100, "seed": 3},
    "🌊 Alles in einer Phase": {**_BASE, "p": 6, "d": 6, "s": 12, "seed": 1},
    "🏭 Werke knapp": {**_BASE, "density": 90, "load": 120, "seed": 9},
    "🪜 Treppe": {**_BASE, "net": "stair"},
    "💑 Zuordnung als Fluss": {**_BASE, "net": "assignment"},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py belegt (Lehrnetze von Hand, Zufallsnetze über die Seeds der Presets)
PRESET_HELP = {
    "🚚 Zufallsnetz": "3 Werke, 3 Verteilzentren, 8 Filialen: das Netz schafft 71 von 77 Einheiten. Dinic braucht 2 Phasen (Niveau 5 und 7) mit 8 und 2 Wegen, zwei davon über Rückkanten; Edmonds-Karp sucht dieselben 10 Wege einzeln. Durchsuchte Kanten: 219 gegen 434.",
    "🧭 Ohne Zeigerliste": "Dasselbe Netz ohne Zeigerliste: dieselben 10 Wege, aber 389 statt 219 durchsuchte Kanten - die Tiefensuche besucht Sackgassen 48-mal statt 17-mal, weil sie bei jedem Weg wieder bei der ersten Kante beginnt.",
    "🕳️ Sackgassen": "Die gesamte Nachfrage (68) wird geliefert. Die Tiefensuche verlässt 42-mal eine Sackgasse (violette Kreuze), 9 + 2 Wege in 2 Phasen; durchsucht werden 374 Kanten, Edmonds-Karp braucht 651.",
    "🔁 Drei Phasen": "6 Werke, 6 Verteilzentren, 12 Filialen, dünnes Netz (40 %) mit breit gestreuten Lanes: 3 Phasen mit Niveau 5, 7 und 9 und 17, 3 und 1 Wegen; Flusswert 124 von 150. Jede Phase braucht längere Wege, die Rückkanten nutzen. 722 durchsuchte Kanten gegen 2120 bei Edmonds-Karp.",
    "🌊 Alles in einer Phase": "Dasselbe Netz mit 60 % Netzdichte: alle 26 Wege stehen schon im ersten Niveaugraph (Niveau 5), die Nachfrage (150) wird ganz gedeckt. 571 durchsuchte Kanten gegen 3624 bei Edmonds-Karp - das 6,3-Fache.",
    "🏭 Werke knapp": "Auslastung 120 %: das Netz schafft 98 von 114 Einheiten, der Schnitt besteht nur aus den drei Werken. 2 Phasen (10 + 3 Wege); Dinic durchsucht 283 Kanten, Edmonds-Karp 787.",
    "🪜 Treppe": "Fünf Ketten aus Einheitskanten (20 Fahrzeuge, 20 Aufträge): 6 Phasen mit Niveau 3, 5, 7, 9, 11 und 13. Die erste nimmt 15 Wege, jede weitere genau einen - Kette t hat nur einen Verbesserungsweg mit 2t + 3 Kanten. Der Vorsprung ist hier klein: 928 durchsuchte Kanten gegen 1345.",
    "💑 Zuordnung als Fluss": "Fünf Fahrzeuge und fünf Aufträge in einer Kette, jede Kante Kapazität 1: eine Phase (Niveau 3) mit 5 Wegen, das sind die 5 Paare. 69 durchsuchte Kanten gegen 100 bei Edmonds-Karp.",
}
