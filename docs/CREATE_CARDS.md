# 🎴 MTG Card Creator - Anleitung

## Komplette Karten mit KI-Artwork erstellen

### 🚀 Schnellstart

```bash
# Interaktiver Modus - Schritt für Schritt
poetry run python create_new_card.py
```

Das Skript führt dich durch alle Schritte:
1. **Kartenname** eingeben
2. **Manakosten** festlegen (z.B. `{2}{R}{R}` für 2 generisches + 2 rotes Mana)
3. **Kartentyp** wählen (Creature, Instant, Sorcery, etc.)
4. **Kartentext** schreiben (Fähigkeiten, Effekte)
5. **Power/Toughness** für Kreaturen
6. **Flavor Text** (optional)
7. **Seltenheit** (common/uncommon/rare/mythic)
8. **Artwork-Beschreibung** - Was soll auf dem Bild zu sehen sein?
9. **Art Style** auswählen

### 📝 Beispiele für Kartenerstellung

#### Beispiel 1: Roter Drache
```
Card Name: Inferno Ancient
Mana Cost: {4}{R}{R}{R}
Type: Legendary Creature — Elder Dragon
Text: Flying, trample\nWhenever ~ attacks, it deals 3 damage to each opponent.
Power: 7
Toughness: 6
Flavor: "The mountains themselves bow before its fury."
Rarity: mythic
Art: ancient red dragon breathing fire over volcanic mountains
Style: mtg_classic
```

#### Beispiel 2: Blauer Instant
```
Card Name: Temporal Reversal
Mana Cost: {1}{U}{U}
Type: Instant
Text: Counter target spell. Draw a card.
Flavor: "Time is merely a suggestion."
Rarity: rare
Art: swirling vortex of time magic, clock fragments floating
Style: fantasy_art
```

#### Beispiel 3: Grüne Kreatur
```
Card Name: Forest Guardian
Mana Cost: {2}{G}{G}
Type: Creature — Elemental
Text: Vigilance\n{T}: Add {G}{G} to your mana pool.
Power: 3
Toughness: 5
Rarity: uncommon
Art: massive tree elemental protecting ancient forest
Style: oil_painting
```

### 🎨 Verfügbare Art Styles

- **realistic** - Fotorealistisch
- **anime** - Anime/Manga-Stil
- **oil_painting** - Ölgemälde
- **watercolor** - Wasserfarben
- **comic_book** - Comic-Stil
- **fantasy_art** - Fantasy-Kunst
- **dark_gothic** - Düster/Gothic
- **steampunk** - Steampunk-Ästhetik
- **cyberpunk** - Cyberpunk-Stil
- **mtg_classic** - Klassischer MTG-Stil
- **mtg_modern** - Moderner MTG-Stil
- **mtg_sketch** - Skizzenhafter Stil

### 💎 Mana-Symbole

- `{W}` - Weißes Mana (Plains)
- `{U}` - Blaues Mana (Island)
- `{B}` - Schwarzes Mana (Swamp)
- `{R}` - Rotes Mana (Mountain)
- `{G}` - Grünes Mana (Forest)
- `{1}`, `{2}`, etc. - Generisches Mana
- `{X}` - Variable Kosten
- `{C}` - Farbloses Mana

### 📁 Output

Alle erstellten Karten werden gespeichert in:
```
output/custom_cards/
├── CardName_20250818_123456.png    # Fertige Karte (960x1344 px)
├── CardName_20250818_123456.json   # Kartendaten
└── images/                          # Generierte Artworks
```

### 🔧 Erweiterte Nutzung

#### Batch-Erstellung mit vordefiniertem Set

```python
# In create_new_card.py
predefined_cards = [
    {
        "name": "Fire Elemental",
        "mana_cost": "{3}{R}{R}",
        "type_line": "Creature — Elemental",
        "oracle_text": "Haste",
        "power": "5",
        "toughness": "4",
        "rarity": "common",
        "art_prompt": "fire elemental creature",
        "art_style": "mtg_classic",
        # ... weitere Details
    },
    # Weitere Karten...
]

for card in predefined_cards:
    await creator.create_card(card)
```

### 🎯 Tipps für gute Karten

1. **Balance**: Manakosten sollten zur Stärke passen
2. **Kartentext**: Nutze offizielle MTG-Formulierungen
3. **Art Prompts**: Sei spezifisch aber nicht zu komplex
4. **Flavor Text**: Kurz und atmosphärisch

### 🚦 Workflow

1. **Idee entwickeln** - Was für eine Karte soll es sein?
2. **Balance prüfen** - Ist die Karte fair?
3. **Artwork beschreiben** - Was soll man sehen?
4. **Generieren** - Skript ausführen
5. **Review** - PNG prüfen und ggf. neu generieren

### ⚡ Schnelle Tests

```bash
# Test ohne Bilderstellung (nur Layout)
poetry run python test_png_generation.py

# Test mit existierendem Bild
poetry run python test_png_simple.py
```

### 🛠️ Troubleshooting

**Problem**: Kein Bild wird generiert
- Prüfe API-Keys in `.env`
- Stelle sicher, dass Replicate-Guthaben vorhanden ist

**Problem**: Browser-Fehler
- Installiere Playwright: `poetry run playwright install chromium`

**Problem**: Bild wird nicht angezeigt
- Prüfe, ob der Bildpfad korrekt ist
- Warte länger beim Rendering (3-5 Sekunden)

### 📚 Weitere Ressourcen

- [MTG Comprehensive Rules](https://magic.wizards.com/en/rules)
- [Scryfall für Kartenbeispiele](https://scryfall.com)
- [MTG Wiki für Keywords](https://mtg.fandom.com/wiki/Keyword_ability)
