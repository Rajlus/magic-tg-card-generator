# 🎴 Unified MTG Card Generator - Komplettanleitung

## Das EINE Skript für ALLE Karten: `generate_card.py`

Dieses Skript vereint alle Funktionen:
- ⚡ **Quick Mode**: Nur ein Prompt eingeben
- 🎯 **Detailed Mode**: Volle Kontrolle mit Flags
- 💬 **Interactive Mode**: Schritt-für-Schritt Eingabe
- 🔀 **Mixed Mode**: Prompt + Flags kombinieren

---

## 🚀 Quick Start

### 1. Einfachster Weg - Nur Prompt:
```bash
poetry run python generate_card.py "a legendary fire dragon"
poetry run python generate_card.py "Percy Jackson, son of Poseidon"
poetry run python generate_card.py "powerful vampire lord with lifelink"
```

### 2. Mit Art Style:
```bash
poetry run python generate_card.py "dark demon lord" --style dark_gothic
poetry run python generate_card.py "mystical wizard" --style fantasy_art
poetry run python generate_card.py "robot warrior" --style cyberpunk
```

### 3. Interaktiv (ohne Parameter):
```bash
poetry run python generate_card.py --interactive
# oder einfach:
poetry run python generate_card.py
```

---

## 🎯 Detaillierte Kontrolle mit Flags

### Alle verfügbaren Flags:

| Flag | Kurz | Beschreibung | Beispiel |
|------|------|--------------|----------|
| `prompt` | | Basis-Konzept | `"fire dragon"` |
| `--name` | | Kartenname | `--name "Lightning Bolt"` |
| `--cost` | `--mana` | Manakosten | `--cost "{2}{R}{R}"` |
| `--type` | | Kartentyp | `--type "Creature — Dragon"` |
| `--text` | | Kartenfähigkeiten | `--text "Flying, haste"` |
| `--power` | | Stärke (Kreaturen) | `--power 5` |
| `--toughness` | | Widerstand | `--toughness 4` |
| `--flavor` | | Flavor-Text | `--flavor "Born from flame"` |
| `--rarity` | | Seltenheit | `--rarity mythic` |
| `--art` | | Artwork-Beschreibung | `--art "epic dragon"` |
| `--style` | | Art Style | `--style mtg_classic` |
| `--model` | | Bild-Modell | `--model flux-schnell` |
| `--output` | | Output-Ordner | `--output output/percy` |
| `--interactive` | `-i` | Interaktiv-Modus | `--interactive` |

### Verfügbare Bild-Modelle:
- `sdxl` - Stable Diffusion XL (Standard, ausgewogen)
- `sdxl-lightning` - SDXL Lightning (sehr schnell, 4 steps)
- `flux-schnell` - Flux Schnell (schnell, gut für Charaktere)
- `flux-dev` - Flux Development (höchste Qualität, langsamer)
- `playground` - Playground v2.5 (ästhetischer Stil)

### Verfügbare Art Styles:
- `realistic`, `anime`, `oil_painting`, `watercolor`
- `comic_book`, `fantasy_art`, `dark_gothic`
- `steampunk`, `cyberpunk`
- `mtg_classic`, `mtg_modern`, `mtg_sketch`

### Verfügbare Seltenheiten:
- `common`, `uncommon`, `rare`, `mythic`

---

## 📚 Percy Jackson Beispiele - Komplette Befehle

### 🔱 Die 4 Hauptkarten mit allen Details:

#### 1. Percy Jackson, Son of the Sea
```bash
poetry run python generate_card.py \
  --name "Percy Jackson, Son of the Sea" \
  --cost "{2}{U}{U}" \
  --type "Legendary Creature — Human Demigod" \
  --text "Islandwalk\n{T}: Create a 2/2 blue Hippocampus creature token.\n{2}{U}: Return target creature to its owner's hand.\nWhenever Percy Jackson, Son of the Sea attacks, you may draw a card." \
  --power 3 \
  --toughness 4 \
  --flavor "The sea does not like to be restrained." \
  --rarity mythic \
  --art "teenage demigod with black hair and green eyes, wielding a bronze sword, surrounded by swirling water and sea creatures, Camp Half-Blood in background" \
  --style mtg_modern \
  --model sdxl
```

#### 2. Annabeth Chase, Architect of Olympus
```bash
poetry run python generate_card.py \
  --name "Annabeth Chase, Architect of Olympus" \
  --cost "{1}{W}{U}" \
  --type "Legendary Creature — Human Demigod" \
  --text "Vigilance\nWhen Annabeth Chase, Architect of Olympus enters the battlefield, search your library for an artifact card, reveal it, and put it into your hand.\n{T}: Target creature gains hexproof until end of turn." \
  --power 2 \
  --toughness 3 \
  --flavor "Knowledge is the most powerful weapon." \
  --rarity rare \
  --art "blonde girl with grey eyes wearing Yankees cap, holding bronze dagger, architectural blueprints floating around her" \
  --style mtg_modern \
  --model sdxl
```

#### 3. Camp Half-Blood
```bash
poetry run python generate_card.py \
  --name "Camp Half-Blood" \
  --cost "{3}" \
  --type "Legendary Land" \
  --text "{T}: Add {C}.\n{2}, {T}: Add one mana of any color.\nDemigod creatures you control have hexproof.\n{5}: Create a 1/1 white Satyr creature token with \"{T}: Add {G}.\"" \
  --flavor "Safe haven for heroes in training." \
  --rarity mythic \
  --art "magical summer camp with Greek architecture, strawberry fields, climbing wall with lava, Big House in center, golden fleece on pine tree" \
  --style oil_painting \
  --model sdxl
```

#### 4. Riptide, Anaklusmos
```bash
poetry run python generate_card.py \
  --name "Riptide, Anaklusmos" \
  --cost "{2}" \
  --type "Legendary Artifact — Equipment" \
  --text "Equipped creature gets +3/+1 and has \"Whenever this creature deals combat damage, return target creature to its owner's hand.\"\nWhenever equipped creature dies, return Riptide to your hand.\nEquip {2}" \
  --flavor "It always returns when you need it most." \
  --rarity rare \
  --art "glowing bronze Greek sword with wave patterns on blade, transforming between sword and pen" \
  --style mtg_classic \
  --model sdxl
```

### Mit verschiedenen Modellen:
```bash
# Mit Flux Schnell (schneller, weniger Details)
poetry run python generate_card.py "Percy Jackson" --model flux-schnell

# Mit SDXL Lightning (sehr schnell, 4 steps)
poetry run python generate_card.py "Percy Jackson" --model sdxl-lightning

# Mit Flux Dev (höhere Qualität, langsamer)
poetry run python generate_card.py "Percy Jackson" --model flux-dev

# Mit Playground v2.5 (ästhetischer Stil)
poetry run python generate_card.py "Percy Jackson" --model playground
```

### Quick Mode Alternativen (nur Prompt):
```bash
# Percy selbst
poetry run python generate_card.py "Percy Jackson, demigod son of Poseidon who controls water"

# Annabeth
poetry run python generate_card.py "Annabeth Chase, daughter of Athena with strategic wisdom"

# Camp Half-Blood
poetry run python generate_card.py "Camp Half-Blood magical training ground for demigods"
```

### Detailed Mode (volle Kontrolle):
```bash
# Percy mit allen Details
poetry run python generate_card.py \
  --name "Percy Jackson, Son of the Sea" \
  --cost "{2}{U}{U}" \
  --type "Legendary Creature — Human Demigod" \
  --text "Islandwalk\n{T}: Create a 2/2 blue Hippocampus token.\nWhenever ~ attacks, draw a card." \
  --power 3 \
  --toughness 4 \
  --flavor "The sea does not like to be restrained." \
  --rarity mythic \
  --art "teenage boy with black hair wielding bronze sword, ocean waves, Camp Half-Blood" \
  --style mtg_modern

# Riptide (Percys Schwert)
poetry run python generate_card.py \
  --name "Riptide, Anaklusmos" \
  --cost "{2}" \
  --type "Legendary Artifact — Equipment" \
  --text "Equipped creature gets +3/+1.\nWhenever equipped creature dies, return Riptide to your hand.\nEquip {2}" \
  --flavor "It always returns when you need it most." \
  --rarity rare \
  --art "glowing bronze Greek sword transforming between sword and pen" \
  --style mtg_classic
```

### Mixed Mode (Prompt + Overrides):
```bash
# Basis-Prompt mit spezifischen Anpassungen
poetry run python generate_card.py "Grover the satyr" \
  --cost "{1}{G}{G}" \
  --rarity uncommon \
  --style fantasy_art

# Dragon mit festgelegten Stats
poetry run python generate_card.py "legendary fire dragon" \
  --power 7 \
  --toughness 5 \
  --cost "{4}{R}{R}" \
  --rarity mythic
```

---

## 🔄 Modi im Detail

### Mode 1: Quick Generation
```bash
poetry run python generate_card.py "your concept here"
```
- KI generiert alles automatisch
- Name, Kosten, Fähigkeiten werden aus dem Prompt abgeleitet
- Artwork wird basierend auf der Beschreibung erstellt

### Mode 2: Full Control
```bash
poetry run python generate_card.py \
  --name "Card Name" \
  --cost "{3}{R}" \
  --type "Creature — Type" \
  --text "Abilities" \
  --power 4 \
  --toughness 3
```
- Du kontrollierst jeden Aspekt
- Kein Prompt nötig, alles über Flags

### Mode 3: Interactive
```bash
poetry run python generate_card.py --interactive
```
- Schritt-für-Schritt Abfrage
- Ideal wenn du dir unsicher bist
- Zeigt alle Optionen an

### Mode 4: Hybrid
```bash
poetry run python generate_card.py "base concept" --cost "{5}" --rarity mythic
```
- Startet mit Prompt
- Überschreibt spezifische Werte mit Flags
- Beste Balance zwischen Geschwindigkeit und Kontrolle

---

## 💡 Praktische Beispiele

### Schnelle Session - 5 Karten in 2 Minuten:
```bash
# Dragon
poetry run python generate_card.py "legendary red dragon with firebreathing"

# Wizard
poetry run python generate_card.py "blue wizard that copies spells" --style anime

# Angel
poetry run python generate_card.py "protective white angel" --rarity mythic

# Vampire
poetry run python generate_card.py "vampire lord with lifelink" --cost "{3}{B}{B}"

# Artifact
poetry run python generate_card.py "artifact that generates mana" --type "Legendary Artifact"
```

### Komplettes Custom-Set:
```bash
# Erstelle Ordner für dein Set
mkdir -p output/my_set

# Generiere Karten
poetry run python generate_card.py "Fire Starter" --output output/my_set --rarity common
poetry run python generate_card.py "Flame Wizard" --output output/my_set --rarity uncommon
poetry run python generate_card.py "Inferno Dragon" --output output/my_set --rarity rare
poetry run python generate_card.py "Phoenix Lord" --output output/my_set --rarity mythic
```

### Batch-Skript für mehrere Karten:
```bash
#!/bin/bash
# save as: generate_percy_set.sh

cards=(
  "Percy Jackson demigod of the sea"
  "Annabeth Chase daughter of Athena"
  "Grover Underwood satyr protector"
  "Nico di Angelo son of Hades"
  "Thalia Grace daughter of Zeus"
)

for card in "${cards[@]}"; do
  poetry run python generate_card.py "$card" \
    --style mtg_modern \
    --output output/percy_jackson_set
  sleep 2
done
```

---

## 🛠️ Tipps & Tricks

### Für beste Ergebnisse:

**Prompts:**
- Sei spezifisch: "legendary fire dragon that destroys artifacts" > "dragon"
- Nutze MTG-Sprache: "enters the battlefield", "tap", "combat damage"
- Charaktere nennen: "Percy Jackson" wird erkannt

**Manakosten:**
- Verwende Standard-Notation: `{2}{R}{R}`, nicht "2RR"
- Multicolor: `{1}{U}{B}` für Blau-Schwarz
- Colorless: `{3}` für generisches Mana

**Kartentext:**
- `\n` für Zeilenumbrüche
- `~` wird durch Kartennamen ersetzt
- Keywords groß: "Flying, Haste" nicht "flying, haste"

**Art Styles:**
- `mtg_classic`: Dragons, Angels, traditionelle Fantasy
- `mtg_modern`: Planeswalker, neue Charaktere
- `dark_gothic`: Demons, Vampires, Horror
- `fantasy_art`: Elves, Merfolk, Enchantments

---

## 🐛 Troubleshooting

**Problem:** Kein Bild (gelber Kasten)
```bash
# Prüfe API Token
echo $REPLICATE_API_TOKEN

# Setze Token
export REPLICATE_API_TOKEN="dein_token"
```

**Problem:** "No module named playwright"
```bash
poetry add playwright
poetry run playwright install chromium
```

**Problem:** Karte wird nicht gerendert
```bash
# Teste Renderer direkt
poetry run python -c "from pathlib import Path; print(Path('mtg-card-generator/card-rendering/index.html').exists())"
```

---

## 📊 Output

Alle Karten werden gespeichert in:
```
output/cards/              # Standard-Ordner
├── Card_Name_timestamp.png   # Fertige Karte (960x1344 px)
├── Card_Name_timestamp.json  # Kartendaten
└── images/                   # Generierte Artworks
```

Oder mit `--output`:
```
output/my_custom_set/      # Dein eigener Ordner
```

---

## 🎯 Cheat Sheet

```bash
# Schnellste Methode
poetry run python generate_card.py "deine idee"

# Mit Style
poetry run python generate_card.py "deine idee" --style mtg_modern

# Volle Kontrolle
poetry run python generate_card.py \
  --name "Name" --cost "{2}{R}" --type "Creature" \
  --text "Abilities" --power 3 --toughness 3

# Interaktiv
poetry run python generate_card.py -i

# Percy Jackson
poetry run python generate_card.py "Percy Jackson son of Poseidon"

# Hilfe
poetry run python generate_card.py --help
```

Viel Spaß beim Erstellen deiner Karten! 🎴✨
