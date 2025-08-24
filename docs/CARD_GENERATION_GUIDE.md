# 🎴 MTG Card Generation - Vollständige Anleitung

## Übersicht

Du hast zwei Möglichkeiten, um professionelle Magic: The Gathering Karten mit KI-generiertem Artwork zu erstellen:

1. **`generate_card_from_prompt.py`** - Vollautomatisch aus einem Prompt
2. **`create_new_card.py`** - Schritt-für-Schritt mit manueller Kontrolle

Beide erstellen hochauflösende PNG-Karten (960x1344 px) mit echtem MTG-Layout.

---

## 📋 Voraussetzungen

### Installation
```bash
# Playwright für Browser-Rendering
poetry add playwright
poetry run playwright install chromium

# Optional für bessere KI-Generierung
poetry add openai  # Für GPT-4 (benötigt API-Key)
```

### API-Konfiguration (.env Datei)
```bash
# Für Bildgenerierung (ERFORDERLICH)
REPLICATE_API_TOKEN=dein_replicate_token

# Optional für bessere Kartengenerierung
OPENAI_API_KEY=dein_openai_key
```

---

## 🤖 Skript 1: generate_card_from_prompt.py

### **Was es macht:**
Generiert aus einem einzigen Satz eine komplette MTG-Karte inklusive:
- Name, Manakosten, Kartentyp
- Balancierte Fähigkeiten und Stats
- Flavor Text
- KI-generiertes Artwork
- Fertige PNG-Karte

### **Verwendung:**

```bash
poetry run python generate_card_from_prompt.py
```

### **Beispiel-Session:**

```
╔══════════════════════════════════════════════════════════╗
║         🤖 AI-POWERED MTG CARD GENERATOR 🤖             ║
╚══════════════════════════════════════════════════════════╝

Using Replicate API for image generation
⚠️ No LLM available. Using creative fallback generation.

📝 Example prompts:
   1. a powerful fire dragon that destroys artifacts
   2. a blue wizard that can copy spells
   3. a green nature elemental that creates forests
   4. a legendary vampire lord with lifelink
   5. a white angel that protects other creatures

💡 Enter your card concept (or number for example):
   > a legendary lightning phoenix
```

### **Eingabe-Beispiele:**

| Prompt | Resultat |
|--------|----------|
| "a powerful fire dragon" | Roter Drache mit Haste/First Strike |
| "a blue wizard that copies spells" | Blauer Wizard mit Copy-Abilities |
| "legendary vampire lord" | Schwarze Kreatur mit Lifelink/Deathtouch |
| "nature elemental that creates forests" | Grüne Kreatur mit Token-Generation |
| "artifact that generates mana" | Farbloses Artefakt mit Mana-Abilities |

### **Erweiterte Prompts:**

```
# Detaillierter Prompt für bessere Ergebnisse
"a legendary red and black dragon that deals damage when entering the battlefield and has flying"

# Mit Stärke-Hinweisen
"a weak goblin warrior"  → 1-2 Mana Kosten
"a powerful angel"        → 4-6 Mana Kosten
"a mythic demon lord"     → 6+ Mana Kosten
```

### **Output:**
```
output/ai_cards/
├── Lightning_Phoenix_20250824_140000.png    # Fertige Karte
├── Lightning_Phoenix_20250824_140000.json   # Kartendaten
└── (Artwork wird direkt integriert)
```

---

## 🎨 Skript 2: create_new_card.py

### **Was es macht:**
Interaktive Kartenerstellung mit voller Kontrolle über jeden Aspekt:
- Manuelle Eingabe aller Kartendetails
- Auswahl des Art Styles
- Präzise Artwork-Beschreibung
- Volle Kontrolle über Balance

### **Verwendung:**

```bash
poetry run python create_new_card.py
```

### **Schritt-für-Schritt Prozess:**

```
============================================================
🎴 MTG CARD CREATOR - Create Your Custom Card!
============================================================

📝 Card Name: Lightning Phoenix
💎 Mana Cost: {2}{R}{R}
📋 Card Type: Creature — Phoenix
📜 Card Text: Flying, haste\nWhen ~ dies, return it to the battlefield
⚔️ Power: 4
   Toughness: 2
💭 Flavor Text: "From ashes to lightning"
⭐ Rarity: rare
🎨 Art Description: phoenix made of pure lightning energy
🖌️ Art Style:
   1. realistic
   2. anime
   3. oil_painting
   4. watercolor
   5. comic_book
   6. fantasy_art
   7. dark_gothic
   8. steampunk
   9. cyberpunk
   10. mtg_classic
   11. mtg_modern
   12. mtg_sketch
   Choose style: 10
```

### **Verfügbare Art Styles:**

| Style | Beschreibung | Gut für |
|-------|--------------|---------|
| `mtg_classic` | Klassischer MTG-Stil | Dragons, Angels, Traditionelle Fantasy |
| `mtg_modern` | Moderner MTG-Stil | Planeswalker, Neue Sets |
| `dark_gothic` | Düster, Gothic | Demons, Zombies, Horror |
| `fantasy_art` | High Fantasy | Elves, Wizards, Enchantments |
| `realistic` | Fotorealistisch | Lands, Beasts, Soldiers |
| `oil_painting` | Ölgemälde-Stil | Legendary Creatures, Epische Szenen |
| `anime` | Anime/Manga | Tokens, Alternative Art |
| `cyberpunk` | Futuristisch | Artifacts, Constructs |
| `steampunk` | Steampunk | Artifacts, Thopters |

### **Tipps für gute Karten:**

#### Manakosten-Balance:
- 1 Mana: Kleine Effekte (1/1 Creature, "Draw a card")
- 3 Mana: Mittlere Kreaturen (3/3) oder gute Spells
- 5+ Mana: Mächtige Effekte, große Kreaturen

#### Kartentext-Formatierung:
- `\n` für Zeilenumbrüche
- `~` wird durch Kartennamen ersetzt
- Standard MTG-Keywords verwenden

#### Artwork-Beschreibungen:
```
✅ Gut: "massive red dragon breathing fire over mountain peaks"
❌ Schlecht: "dragon"

✅ Gut: "ethereal blue wizard casting time magic, swirling clocks"
❌ Schlecht: "wizard with magic"
```

---

## 🔧 Erweiterte Nutzung

### Batch-Generierung (mehrere Karten)

Erstelle eine Python-Datei `batch_generate.py`:

```python
import asyncio
from generate_card_from_prompt import AICardGenerator

async def generate_set():
    generator = AICardGenerator()

    prompts = [
        "a fire dragon that deals damage",
        "a blue merfolk that draws cards",
        "a green elf that creates tokens",
        "a white knight with vigilance",
        "a black vampire with lifelink"
    ]

    for prompt in prompts:
        print(f"\nGenerating: {prompt}")
        await generator.generate_complete_card(prompt)
        await asyncio.sleep(2)  # Pause zwischen Generierungen

asyncio.run(generate_set())
```

### Vordefinierte Karten

Für `create_new_card.py` mit vordefinierten Details:

```python
import asyncio
from create_new_card import MTGCardCreator

async def create_predefined():
    creator = MTGCardCreator()

    card = {
        "name": "Stormcaller Wizard",
        "mana_cost": "{2}{U}{R}",
        "type_line": "Creature — Human Wizard",
        "oracle_text": "Flying\nWhenever you cast an instant or sorcery spell, draw a card.",
        "power": "2",
        "toughness": "3",
        "flavor_text": "\"The storm answers only to me.\"",
        "rarity": "rare",
        "art_prompt": "wizard summoning lightning storm, blue and red magic",
        "art_style": "mtg_modern",
        "colors": ["U", "R"],
        "layout": "normal",
        "set": "CUS",
        "set_name": "Custom Set",
        "collector_number": "001",
        "artist": "AI Generated"
    }

    await creator.create_card(card)

asyncio.run(create_predefined())
```

---

## 🐛 Troubleshooting

### Problem: "No module named 'playwright'"
```bash
poetry add playwright
poetry run playwright install chromium
```

### Problem: Bild wird nicht generiert (gelber Kasten)
- Prüfe ob `REPLICATE_API_TOKEN` in `.env` gesetzt ist
- Stelle sicher, dass du Guthaben auf Replicate hast
- Test: `echo $REPLICATE_API_TOKEN`

### Problem: "No LLM available"
Das ist normal! Der Fallback-Generator funktioniert auch ohne GPT/Ollama.
Für bessere Ergebnisse:
```bash
# Option 1: OpenAI
echo "OPENAI_API_KEY=sk-..." >> .env

# Option 2: Ollama (lokal)
brew install ollama
ollama pull llama2
```

### Problem: Karte wird nicht gerendert
```bash
# Browser neu installieren
poetry run playwright install --force chromium
```

---

## 📊 Vergleich der Skripte

| Feature | generate_card_from_prompt.py | create_new_card.py |
|---------|------------------------------|-------------------|
| **Eingabe** | Ein Satz | Schritt für Schritt |
| **Kontrolle** | Automatisch | Volle Kontrolle |
| **Geschwindigkeit** | Sehr schnell | Detailliert |
| **KI-Generierung** | Alles | Nur Artwork |
| **Beste für** | Schnelle Ideen | Präzise Karten |
| **Art Style** | Automatisch | Manuell wählbar |

---

## 🎯 Best Practices

1. **Für schnelle Prototypen:** `generate_card_from_prompt.py`
2. **Für finale Karten:** `create_new_card.py`
3. **Artwork-Qualität:** Sei spezifisch in der Beschreibung
4. **Balance:** Orientiere dich an existierenden MTG-Karten
5. **Testing:** Generiere mehrere Versionen und wähle die beste

---

## 📁 Ausgabe-Struktur

```
output/
├── ai_cards/                    # Von generate_card_from_prompt.py
│   ├── Card_Name_timestamp.png
│   └── Card_Name_timestamp.json
├── custom_cards/                # Von create_new_card.py
│   ├── Card_Name_timestamp.png
│   └── Card_Name_timestamp.json
└── images/                      # Generierte Artworks
    └── *.jpg
```

---

## 🚀 Quick Start

```bash
# 1. Setup
poetry install
poetry add playwright
poetry run playwright install chromium

# 2. API Key hinzufügen
echo "REPLICATE_API_TOKEN=dein_token" >> .env

# 3. Erste Karte generieren (automatisch)
poetry run python generate_card_from_prompt.py
# Eingabe: "a legendary dragon"

# 4. Oder manuell mit voller Kontrolle
poetry run python create_new_card.py
# Folge den Anweisungen

# 5. Ergebnis anschauen
open output/ai_cards/  # Mac
# oder
explorer output\ai_cards\  # Windows
```

Viel Spaß beim Erstellen deiner eigenen Magic-Karten! 🎴✨
