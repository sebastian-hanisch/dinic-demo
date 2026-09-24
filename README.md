# Dinic – Niveaugraph und blockierender Fluss – Streamlit-Demo

*(noch nicht deployed)*

Zweites Stück der **Netzwerkfluss-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Fortsetzung der Demo [Edmonds-Karp](https://github.com/sebastian-hanisch/edmonds-karp-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **Dinics Phasen aus Niveaugraph und blockierendem Fluss** – an einem wachsenden Beispiel.
Edmonds-Karp sucht für jeden Weg eine neue Breitensuche. **Dinic** nutzt sie besser: eine Breitensuche gibt jedem Knoten sein **Niveau** (Entfernung von der Quelle), der **Niveaugraph** enthält nur Restkanten von Niveau k nach k + 1, und darin füllt eine Tiefensuche **alle** kürzesten Wege auf, bis keiner mehr übrig ist (**blockierender Fluss**).
Danach ist die Entfernung von S nach T echt gewachsen, eine neue **Phase** beginnt – höchstens |V| − 1 Phasen. Eine **Zeigerliste** lässt die Tiefensuche jede Sackgasse nur einmal besuchen. Vehikel wie in der Edmonds-Karp-Demo: ein Distributionsnetz (Werke → Verteilzentren → Filialen), dazu Einheitsnetze.

**Einordnung in die Reihe (die Kanten des Graphen):** dieses Stück behebt die Schwäche der Wurzel (eine Breitensuche je Weg; ihre durchsuchten Kanten wachsen schneller als das Netz, Steigung 1,7 bis 1,9). Auf Einheitsnetzen ist Dinic der Algorithmus von **Hopcroft–Karp** aus der Matching-Linie.
Seine eigenen Schwächen sind die Ansatzpunkte der nächsten: Fluss wird weiter über Wege gebaut (**Push-Relabel**, gebaut: [push-relabel-demo](https://github.com/sebastian-hanisch/push-relabel-demo)), und die Kosten entscheiden nicht (**Successive Shortest Paths**). Bisher gebaut: die Wurzel, dieses Stück und Push-Relabel.
```
edmonds-karp-demo (Wurzel: Restgraph, Rückkanten, Max-Flow = Min-Cut)                  [gebaut]
  ├─ dinic-demo (viele kürzeste Wege je Phase: Niveaugraph, blockierender Fluss)        [dieses Stück]
  ├─ push-relabel-demo (kein Weg: Überschüsse schieben, Höhen anheben)                 [gebaut]
  └─ ssp-demo (Kosten: der billigste Weg im Restgraphen, Potenziale)                    [geplant]
       ├─ cycle-canceling-demo → Netzwerksimplex (network-flow-demo)                    [geplant / gebaut als Fall-Demo]
       ├─ cost-scaling-demo (Push-Relabel + ε-Skalierung, das nutzt OR-Tools)           [geplant]
       └─ multicommodity-demo → Column Generation, Garg-Könemann,
          Fixkosten-Netzwerkdesign → Benders-Zerlegung, Slope Scaling                   [geplant]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` belegt: die Lehrnetze von Hand, die Beispielnetze über ihre Seeds, die Verteilungen über 100 feste Netze (Seeds 100000–100099, dieselben wie in der Edmonds-Karp-Demo). Standard: 3 Werke, 3 Verteilzentren, 8 Filialen, Netzdichte 60 %, Streuung 50 %, Auslastung 90 %, mit Zeigerliste. Die Zahlen von Edmonds-Karp werden hier neu gemessen (die Breitensuche ist aus der Vorgänger-Demo kopiert, ein Test bewacht die Kopie).

| Frage | Ergebnis |
|---|---|
| Wird der Fluss maximal? | ✅ Ja, auf jedem getesteten Netz, mit und ohne Zeigerliste; unabhängig gegen `networkx` (`maximum_flow` mit `dinitz`, `minimum_cut`) und `scipy` (`maximum_flow`, beide Verfahren) geprüft, dazu Brute-Force-Aufzählung aller Schnitte auf Kleinstnetzen; derselbe Schnitt wie bei Edmonds-Karp. Niveaus und Niveaugraph jeder Phase sind unabhängig per `networkx` auf dem Restgraphen nachgebaut, jede Phase ist blockierend. |
| Wie viele Phasen? | ✅ Im Mittel 1,7 (Median 2, höchstens 4 von |V| − 1 = 18): 40 von 100 Netzen brauchen eine Phase, 50 zwei, 9 drei, 1 vier. Das Niveau von T wächst in jedem Netz echt; die Phasenzahl liegt im Mittel bei 9,5 % der Schranke |V| − 1, höchstens bei 22 %. Edmonds-Karp sucht dieselben 11,1 Wege einzeln. |
| Ändert Dinic die Wege? | ⚠️ Nein: auf allen 100 Netzen sind es genauso viele Wege wie bei Edmonds-Karp, mit derselben Verteilung der Weglängen. Dinic spart nicht Wege, sondern Suchdurchgänge. (Beobachtung an diesen Netzen, kein Satz.) |
| Wie viel Aufwand spart das? | ✅ Im Mittel 254 statt 525 durchsuchte Kanten (Median 236,5 statt 526), in 100 von 100 Netzen höchstens so viele wie Edmonds-Karp; das Verhältnis liegt je Netz zwischen 1,24 und 3,5, im Mittel bei 2,1. Von den 254 entfallen 115 auf Breiten- und 139 auf Tiefensuchen. |
| Wächst der Vorsprung mit dem Netz? | ✅ Ja: Edmonds-Karp ÷ Dinic = 1,2 (12 Knoten), 2,0, 3,4, 9,0, 17,3 und 33,7 (166 Knoten). Steigung im doppelt logarithmischen Diagramm: Dinic 0,94, Dinic ohne Zeigerliste 1,45, Edmonds-Karp 1,74. Bei den drei größten Netzen genügt schon **eine** Phase (alle Wege sind gleich lang). |
| Was leistet die Zeigerliste? | ✅ Ohne sie sind es im Mittel 436 statt 254 durchsuchte Kanten (Faktor 1,7), im schlimmsten Netz das 2,5-Fache, in keinem Netz gleich viele; bei den größten Netzen der Demo (166 Knoten) das 10,6-Fache. Die Wege sind dieselben (Test), nur die Sackgassen-Besuche unterscheiden sich (Beispielnetz: 48 statt 17). |
| Wie hängt die Phasenzahl an den Reglern? | ⚠️ Nicht monoton: Netzdichte 100 % braucht im Mittel 1,04 Phasen, mittlere Dichte die meisten (Höhepunkt bei 60 %: 1,71), sehr dünne Netze wieder weniger. Auslastung 40 %: 1,05; 120 %: 1,77. |
| Und auf Einheitsnetzen? | ⚠️ Die **Treppe** (nachgebaut aus der Hopcroft–Karp-Demo) braucht k + 1 Phasen bei k (k + 3) / 2 Fahrzeugen, etwa √(2n): 13 Phasen bei n = 90 (Schranke 2√n ≈ 19). Dort ist der Vorsprung klein: bei den 20 Fahrzeugen des Presets 928 gegen 1345 durchsuchte Kanten. Zufällige bipartite Netze bleiben weit darunter: im Mittel 5,4 Phasen (höchstens 8) bei n = 320, Schranke 36. |
| Beispielnetz mit einer Phase | ✅ 6 Werke, 6 Verteilzentren, 12 Filialen: alle 26 Wege in der ersten Phase, 571 durchsuchte Kanten gegen 3624 (das 6,3-Fache). |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde gemessen; einige Vermutungen aus dem Plan stimmten nicht:

- **„Dinic kann bei kleinen Netzen verlieren“** (wie Hopcroft–Karp bei 20 × 20 gegen die Einzelwege). Nicht eingetreten: schon bei 12 Knoten durchsucht Dinic weniger (Faktor 1,2), und bei den 100 Standardnetzen nie mehr als Edmonds-Karp.
- **„Drei bis fünf Phasen auf dem Distributionsnetz.“** Tatsächlich im Mittel 1,7, bei größeren Netzen genau **eine**: das Distributionsnetz ist geschichtet, alle kürzesten Wege haben zunächst dieselbe Länge (5 Kanten), der erste blockierende Fluss ist fast schon der maximale. Mehrphasige Netze braucht es für die Anschauung – Beispielnetze mit 2 und 3 Phasen und die Treppe.
- **„Dünnere Netze brauchen mehr Phasen.“** Nur bis zur mittleren Dichte; bei sehr dünnen Netzen gibt es wenige Wege, bei 100 % genügt eine Phase.
- **„Dinic ändert, wie viele Wege gebraucht werden.“** Nein, auf allen 100 Netzen dieselbe Zahl wie bei Edmonds-Karp. Der Gewinn liegt in den Suchdurchgängen.
- **Einheitsnetz-Vergleich mit einer Referenz-Hopcroft–Karp im Test** (Plan): nicht umgesetzt. Zwei gültige Verfahren können bei verschiedener Wahl maximaler Wegmengen verschieden viele Phasen brauchen, ein exakter Vergleich wäre also nicht belastbar; stattdessen prüft der Test Flusswert gegen `scipy`-Matching, ungerade Niveaus und die Schranke 2√n + 1.
- **Abweichungen vom Plan:** Port 8671; kein PDF-Export; keine Kostenmessung (Dinic ist genauso kostenblind wie Edmonds-Karp, die Messung steht in der Edmonds-Karp-Demo).
- Bestätigt wurde: Dinic braucht weniger Suchaufwand als Edmonds-Karp, die Zeigerliste spart Aufwand, ohne Wege zu ändern, und das Niveau von T wächst in jedem Netz echt.

## Was die Demo zeigt

- **Phasen in Aktion:** Schritt-Slider und ▶️ über die Bilder: je Phase ein **Niveaugraph** (Knotenfarbe = Niveau, dunkle Kanten = Restkanten von Niveau k nach k + 1, orange gestrichelt = Rückkante, grau hohl = nicht im Niveaugraph), dann ein Bild je Weg des blockierenden Flusses (grün, mit seinem Engpass; **Sackgassen der Tiefensuche** als violette Kreuze, volle Kanten blass gepunktet), rechts jeweils der Fluss; am Ende der **Beweis** (Schnitt) wie bei Edmonds-Karp. Darunter die durchsuchten Kanten je Phase, getrennt nach Breiten- und Tiefensuche.
- **Muss man für jeden Weg neu suchen?** Flusswert, Phasen mit ihren Niveaus, Wege, durchsuchte Kanten gegen Edmonds-Karp; Verteilung über 100 feste Netze (Histogramm Phasen gegen Wege mit der Marke „Ihre Ziehung“, Tabelle Dinic mit und ohne Zeigerliste gegen Edmonds-Karp).
- **Experimente (🔬):** Skalierung von 12 bis 166 Knoten; was leistet die Zeigerliste; Einheitsnetze (Treppe und Zufallsnetze gegen 2√n).
- **Feste Netze** (Treppe, Zuordnung als Fluss) und zufällige Distributionsnetze; **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

## Modell und Verfahren

- **Netz und Restgraph:** wie in der Edmonds-Karp-Demo (Quelle S, Werke, Verteilzentren als Eingang und Ausgang gespalten, Filialen, Senke T; Restkanten als Paar 2i/2i+1); ganzzahlig, eigener Zufallsgenerator SplitMix64 statt `numpy.random`.
- **Niveaugraph:** Breitensuche im Restgraphen, hält an, sobald T erreicht ist (dann sind alle Niveaus < Niveau(T) vergeben); Niveaugraph = Restkanten von Niveau k nach k + 1.
- **Blockierender Fluss:** Tiefensuche von S durch den Niveaugraph, Weg auffüllen, von S aus weitersuchen; Zeigerliste je Knoten (Kanten davor sind voll oder Sackgassen); ohne Zeiger beginnt jede Wegesuche je Knoten bei der ersten Kante – gleiche Wege, mehr durchsuchte Kanten.
- **Lemma:** nach jeder Phase wächst die Entfernung von S nach T echt, also höchstens |V| − 1 Phasen: **O(|V|²·|E|)**. Auf Einheitsnetzen O(|E|·√|E|); bipartit ist das Hopcroft–Karp mit O(|E|·√|V|).
- **Beweis:** wie bei Edmonds-Karp; scheitert die Breitensuche, sind die von S erreichbaren Knoten der minimale Schnitt.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `dn_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `dn_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `dn_scenario.py` | Distributionsnetz, eigener Zufallsgenerator, Lehrnetze, Treppe und zufällige bipartite Einheitsnetze |
| `dn_algorithm.py` | Dinic: Niveaugraph, blockierender Fluss, Zeigerliste, Phasen, Beweis |
| `dn_edmonds_karp.py` | Kopie von `ek_algorithm.py` der Edmonds-Karp-Demo als Vergleichsbasis (ohne Import, durch einen Test bewacht) |
| `dn_evaluation.py` | Urteil, Bilderfolge, Verteilungen, Skalierung, Einheitsnetze |
| `dn_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Hover über unsichtbare Marker entlang der Kanten) |
| `tests/` | Algorithmus (Handfälle, `networkx`/`scipy`/Brute Force als Gegenprobe, Niveaugraph unabhängig nachgebaut, blockierender Fluss, Lemma, gleiche Wege ohne Zeigerliste), Szenario und Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
