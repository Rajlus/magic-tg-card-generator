# MTG Deck YAML Format - Spezifikation

## Übersicht
Diese Dokumentation beschreibt das korrekte Format für MTG Deck YAML-Dateien, die mit dem Card Generator verwendet werden können.

## Dateistruktur

### Grundstruktur
```yaml
card_count: 100  # Anzahl der Karten im Deck
cards:           # Liste aller Karten
  - [Karte 1]
  - [Karte 2]
  # ...
```

## Kartenformat

### Pflichtfelder

Jede Karte MUSS folgende Felder enthalten:

```yaml
- id: 1                                    # Eindeutige ID (Nummer)
  name: Percy Jackson, Sohn des Poseidon   # Kartenname
  type: Legendäre Kreatur - Halbgott      # Kartentyp (WICHTIG: Bindestrich, NICHT Em-Dash!)
  cost: '{2}{U}{G}'                        # Manakosten (in Anführungszeichen!)
  rarity: mythic                           # Seltenheit: common/uncommon/rare/mythic
  set: CMD                                 # Set-Code (3 Buchstaben)
  status: completed                        # Status der Karte
```

### Optionale Felder

```yaml
  text: |-                                 # Kartentext (mit Zeilenumbrüchen)
    Erste Fähigkeit.

    Zweite Fähigkeit.

  power: 3                                 # Stärke (nur bei Kreaturen)
  toughness: 4                            # Widerstandskraft (nur bei Kreaturen)

  flavor: "Flavortext hier"               # Flavor-Text (optional)

  art: "Beschreibung des Artworks"        # Artwork-Beschreibung für KI-Generation

  image_path: output/images/card.jpg      # Pfad zum generierten Bild
  card_path: saved_decks/.../card.png     # Pfad zur gerenderten Karte

  generated_at: '2025-08-25 21:47:28'     # Zeitstempel der Generierung
```

## Wichtige Formatierungsregeln

### 1. Manakosten - IMMER in Anführungszeichen!

❌ **FALSCH:**
```yaml
cost: {2}{R}{R}  # Führt zu YAML-Fehler!
```

✅ **RICHTIG:**
```yaml
cost: '{2}{R}{R}'
```

### 2. Kartentypen - NUR normale Bindestriche verwenden!

❌ **FALSCH:**
```yaml
type: Legendäre Kreatur — Drache  # Em-Dash verursacht Rendering-Fehler!
```

✅ **RICHTIG:**
```yaml
type: Legendäre Kreatur - Drache  # Normaler Bindestrich (Minus-Zeichen)
```

### 3. Kreaturentypen auf Deutsch

Verwende deutsche Begriffe für Kreaturentypen:

```yaml
# Beispiele korrekter deutscher Typen:
type: Kreatur - Konstrukt        # NICHT "Automaton"
type: Kreatur - Drache
type: Legendäre Kreatur - Halbgott
type: Artefaktkreatur - Golem
```

### 4. Kartentext mit Zeilenumbrüchen

Für korrekte Formatierung des Kartentexts verwende das `|-` Format (literal block scalar):

```yaml
text: |-
  Fliegend, Wachsamkeit.

  Wenn diese Kreatur ins Spiel kommt, ziehe eine Karte.

  {2}{U}, {T}: Tappe eine Kreatur deiner Wahl.
```

**Regeln für Zeilenumbrüche:**

1. **Schlüsselwortfähigkeiten** (erste Zeile):
   - `Fliegend, Erstschlag, Wachsamkeit.`
   - Mehrere Keywords mit Komma trennen, Punkt am Ende
   - Doppelter Zeilenumbruch nach dem Punkt

2. **Ausgelöste Fähigkeiten** (neue Zeile):
   - Beginnen mit: `Wenn`, `Immer wenn`, `Zu Beginn`, `Am Ende`, `Solange`
   - Jede ausgelöste Fähigkeit auf eigener Zeile

3. **Aktivierte Fähigkeiten** (neue Zeile):
   - Format: `{Kosten}: Effekt`
   - Beispiele: `{T}:`, `{2}{R}:`, `{U}{G}, {T}:`
   - Jede aktivierte Fähigkeit auf eigener Zeile

4. **Statische Fähigkeiten** (neue Zeile):
   - `Andere Kreaturen, die du kontrollierst, erhalten +1/+1.`
   - `Artefaktkreaturen kosten {1} weniger.`

### 5. Spezielle Zeichen

**Verwende diese Symbole:**
- `{T}` - Tap-Symbol
- `{U}` - Blaues Mana
- `{R}` - Rotes Mana
- `{G}` - Grünes Mana
- `{W}` - Weißes Mana
- `{B}` - Schwarzes Mana
- `{C}` - Farbloses Mana
- `{X}` - X-Kosten
- `{1}`, `{2}`, etc. - Generische Manakosten

## Vollständiges Beispiel

```yaml
card_count: 3
cards:
- id: 1
  name: Percy Jackson, Sohn des Poseidon
  type: Legendäre Kreatur - Halbgott
  cost: '{2}{U}{G}'
  power: 3
  toughness: 4
  rarity: mythic
  set: CMD
  status: completed
  text: |-
    Wenn Percy Jackson ins Spiel kommt, erzeuge einen 2/2 blauen
    Hippokamp-Kreaturenspielstein.

    Immer wenn du einen Zauberspruch wirkst, der Percy Jackson als
    Ziel hat, ziehe eine Karte.

    {U}{G}, {T}: Eine Kreatur deiner Wahl kann in diesem Zug nicht
    geblockt werden.
  flavor: Das Meer lässt sich nicht gerne einschränken.
  art: "Ein Teenager mit schwarzem Haar und meergrünen Augen, trägt
        ein oranges Camp Half-Blood T-Shirt"
  generated_at: '2025-08-25 21:47:28'
  image_path: output/images/Percy_Jackson.jpg
  card_path: saved_decks/deck/rendered_cards/Percy_Jackson.png

- id: 2
  name: Thalia Grace
  type: Legendäre Kreatur - Halbgott
  cost: '{2}{U}'
  power: 3
  toughness: 2
  rarity: rare
  set: CMD
  status: completed
  text: |-
    Fliegend, Erstschlag.

    Andere Kreaturen, die du kontrollierst, haben Fluchsicher.
  flavor: Tochter des Zeus, Kiefernwächterin.

- id: 3
  name: Festus
  type: Legendäre Artefaktkreatur - Drache
  cost: '{5}'
  power: 5
  toughness: 5
  rarity: rare
  set: CMD
  status: completed
  text: |-
    Fliegend.

    Wenn Festus ins Spiel kommt, bringe eine Artefaktkarte deiner
    Wahl aus deinem Friedhof auf deine Hand zurück.
```

## Häufige Fehler und deren Behebung

### Problem 1: YAML-Ladefehler
**Fehler:** `expected <block end>, but found '{'`
**Lösung:** Manakosten in Anführungszeichen setzen

### Problem 2: Schwarze/korrupte Kartenrenderung
**Fehler:** Karten werden mit schwarzen Bereichen gerendert
**Lösung:** Em-Dash (—) durch normalen Bindestrich (-) ersetzen

### Problem 3: Fehlende Zeilenumbrüche im Text
**Fehler:** Alle Fähigkeiten in einer Zeile
**Lösung:** `|-` Format verwenden und Fähigkeiten mit Doppel-Newline trennen

### Problem 4: Unbekannte Kreaturentypen
**Fehler:** "Automaton" wird nicht erkannt
**Lösung:** Deutsche Übersetzung verwenden (z.B. "Konstrukt")

## Validierung

Verwende folgendes Script zum Validieren deiner Deck-Datei:

```python
import yaml
import re

def validate_deck(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        deck = yaml.safe_load(f)

    errors = []

    for card in deck['cards']:
        # Check for em-dash
        if '—' in card.get('type', ''):
            errors.append(f"Card {card['id']}: Em-dash in type")

        # Check for unquoted mana costs
        cost = card.get('cost', '')
        if '{' in cost and not (cost.startswith("'") or cost.startswith('"')):
            errors.append(f"Card {card['id']}: Unquoted mana cost")

    return errors
```

## Tipps für die Deck-Erstellung

1. **Konsistenz:** Verwende einheitliche Formulierungen für ähnliche Effekte
2. **Deutsche Terminologie:** Nutze offizielle deutsche MTG-Begriffe
3. **Testen:** Rendere einzelne Karten zum Testen bevor du das ganze Deck generierst
4. **Backup:** Erstelle regelmäßig Backups deiner YAML-Datei

## Unterstützte Kartentypen

- Kreatur
- Legendäre Kreatur
- Artefaktkreatur
- Legendäre Artefaktkreatur
- Spontanzauber
- Hexerei
- Verzauberung
- Artefakt
- Legendäres Artefakt
- Ausrüstung (Artifact - Equipment)
- Aura (Enchantment - Aura)
- Planeswalker

## Weitere Ressourcen

- [MTG Comprehensive Rules](https://magic.wizards.com/en/rules)
- [Scryfall API](https://scryfall.com/docs/api) für Kartenreferenzen
- [MTG Wiki](https://mtg.fandom.com/de/wiki/) für deutsche Terminologie
