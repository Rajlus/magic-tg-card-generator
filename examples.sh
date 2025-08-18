#!/bin/bash

echo "🎴 Magic: The Gathering Card Generator - Examples"
echo "================================================"
echo ""

# Beispiel 1: Kreatur
echo "1️⃣ Kreatur erstellen:"
echo 'poetry run python -m magic_tg_card_generator generate "Lightning Dragon" --type Creature --mana-cost "3RR" --color Red --power 5 --toughness 4 --text "Flying, haste"'
echo ""

# Beispiel 2: Instant
echo "2️⃣ Instant-Zauber erstellen:"
echo 'poetry run python -m magic_tg_card_generator generate "Counterspell" --type Instant --mana-cost "UU" --color Blue --text "Counter target spell."'
echo ""

# Beispiel 3: Sorcery
echo "3️⃣ Sorcery-Zauber erstellen:"
echo 'poetry run python -m magic_tg_card_generator generate "Fireball" --type Sorcery --mana-cost "XR" --color Red --text "Deal X damage to any target."'
echo ""

# Beispiel 4: Enchantment
echo "4️⃣ Verzauberung erstellen:"
echo 'poetry run python -m magic_tg_card_generator generate "Glorious Anthem" --type Enchantment --mana-cost "1WW" --color White --text "Creatures you control get +1/+1."'
echo ""

# Beispiel 5: Artifact
echo "5️⃣ Artefakt erstellen:"
echo 'poetry run python -m magic_tg_card_generator generate "Sol Ring" --type Artifact --mana-cost "1" --color Colorless --text "Tap: Add 2 colorless mana."'
echo ""

echo "📝 Parameter-Erklärung:"
echo "  name         - Name der Karte (in Anführungszeichen)"
echo "  --type       - Kartentyp: Creature, Instant, Sorcery, Enchantment, Artifact, Planeswalker, Land"
echo "  --mana-cost  - Manakosten: Zahlen und Buchstaben (W=Weiß, U=Blau, B=Schwarz, R=Rot, G=Grün)"
echo "  --color      - Farbe: White, Blue, Black, Red, Green, Colorless, Multicolor"
echo "  --power      - Stärke (nur für Kreaturen)"
echo "  --toughness  - Widerstandskraft (nur für Kreaturen)"
echo "  --text       - Kartentext/Fähigkeiten"
echo ""

# Führe ein Beispiel aus
echo "🎯 Führe Beispiel 1 aus:"
poetry run python -m magic_tg_card_generator generate "Lightning Dragon" \
  --type Creature \
  --mana-cost "3RR" \
  --color Red \
  --power 5 \
  --toughness 4 \
  --text "Flying, haste"
