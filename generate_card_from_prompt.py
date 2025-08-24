#!/usr/bin/env python3
"""
AI-Powered MTG Card Generator
Generates complete MTG cards from a single prompt using LLM + Image Generation
"""

import asyncio
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.append(".")

from playwright.async_api import async_playwright

from generate_unified import UnifiedImageGenerator

try:
    import ollama

    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AICardGenerator:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / "output" / "ai_cards"
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize image generator with API mode
        self.image_generator = UnifiedImageGenerator()
        # Try to use API for image generation
        if os.getenv("REPLICATE_API_TOKEN"):
            self.image_generator.mode = "api"
            self.image_generator.api_model = "sdxl"  # Use working SDXL model
            print("Using Replicate API for image generation")
        else:
            self.image_generator.mode = "local"
            print("Using local model for image generation (if available)")

        # Initialize LLM (try OpenAI first, then Ollama)
        self.llm_client = None
        self.llm_type = None

        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            self.llm_client = OpenAI()
            self.llm_type = "openai"
            print("Using OpenAI for card generation")
        elif OLLAMA_AVAILABLE:
            try:
                # Test if Ollama is available
                ollama.list()
                self.llm_client = ollama
                self.llm_type = "ollama"
                print("Using Ollama for card generation")
            except:
                print("⚠️ Ollama not running. Using fallback generation.")
                self.llm_type = "fallback"
        else:
            print("⚠️ No LLM available. Using creative fallback generation.")
            self.llm_type = "fallback"

    def create_card_prompt(self, user_prompt: str) -> str:
        """Create a detailed prompt for the LLM to generate a card."""
        return f"""Create a Magic: The Gathering card based on this concept: "{user_prompt}"

Generate a complete, balanced MTG card in JSON format with these fields:
- name: Creative card name
- mana_cost: Use standard MTG notation like {{2}}{{R}}{{R}} or {{1}}{{U}}
- type_line: Card type (e.g., "Creature — Dragon", "Instant", "Sorcery", "Enchantment")
- oracle_text: Card abilities and effects. Use standard MTG wording. For creatures, include keywords like Flying, Haste, etc.
- power: (only for creatures, e.g., "4")
- toughness: (only for creatures, e.g., "3")
- flavor_text: Atmospheric quote that fits the card
- rarity: common/uncommon/rare/mythic (based on power level)
- colors: Array of color codes based on mana cost (W=white, U=blue, B=black, R=red, G=green)
- art_description: Detailed description of what the card art should show (for AI image generation)

Make the card balanced and interesting. Power level should match the mana cost.
For reference: 1 mana = small effect, 3 mana = medium creature/spell, 5+ mana = powerful effects.

Return ONLY valid JSON, no other text."""

    async def generate_card_data(self, user_prompt: str) -> Optional[dict]:
        """Use LLM to generate card data from prompt."""
        print(f"\n🤖 Generating card from: '{user_prompt}'")

        prompt = self.create_card_prompt(user_prompt)

        try:
            if self.llm_type == "openai":
                response = self.llm_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert Magic: The Gathering card designer. Create balanced, interesting cards.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                )
                card_json_str = response.choices[0].message.content

            elif self.llm_type == "ollama":
                response = ollama.chat(
                    model="llama2",  # or any model you have
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert Magic: The Gathering card designer.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                )
                card_json_str = response["message"]["content"]
            else:
                # Fallback: Generate a simple card based on keywords
                print("No LLM available, using fallback generation...")
                return self.generate_fallback_card(user_prompt)

            # Extract JSON from response (in case there's extra text)
            json_match = re.search(r"\{[^{}]*\}", card_json_str, re.DOTALL)
            if json_match:
                card_json_str = json_match.group()

            card_data = json.loads(card_json_str)

            # Add required fields
            card_data["layout"] = "normal"
            card_data["set"] = "AIC"
            card_data["set_name"] = "AI Custom"
            card_data["collector_number"] = "001"
            card_data["artist"] = "AI Generated"

            print(f"✅ Generated card: {card_data.get('name', 'Unknown')}")
            return card_data

        except Exception as e:
            print(f"❌ Error generating card data: {e}")
            return self.generate_fallback_card(user_prompt)

    def generate_fallback_card(self, user_prompt: str) -> dict:
        """Generate a creative card without LLM."""
        import random

        # Keywords for different aspects
        creature_keywords = [
            "dragon",
            "wizard",
            "warrior",
            "beast",
            "angel",
            "demon",
            "elemental",
            "phoenix",
            "vampire",
            "knight",
            "goblin",
            "elf",
        ]
        spell_keywords = [
            "destroy",
            "counter",
            "draw",
            "damage",
            "burn",
            "heal",
            "protect",
            "create",
            "transform",
            "copy",
        ]
        artifact_keywords = [
            "artifact",
            "machine",
            "construct",
            "device",
            "engine",
            "forge",
        ]

        prompt_lower = user_prompt.lower()

        # Determine card type
        is_creature = any(keyword in prompt_lower for keyword in creature_keywords)
        is_artifact = any(keyword in prompt_lower for keyword in artifact_keywords)

        # Determine colors and abilities based on keywords
        colors = []
        abilities = []

        # Red keywords
        if any(
            word in prompt_lower
            for word in ["fire", "burn", "rage", "fury", "dragon", "phoenix", "lava"]
        ):
            colors.append("R")
            abilities.extend(["Haste", "First strike"])

        # Blue keywords
        if any(
            word in prompt_lower
            for word in [
                "water",
                "sea",
                "mind",
                "control",
                "wizard",
                "illusion",
                "copy",
            ]
        ):
            colors.append("U")
            abilities.extend(["Flying", "Hexproof"])

        # Green keywords
        if any(
            word in prompt_lower
            for word in ["nature", "forest", "growth", "beast", "elf", "wild"]
        ):
            colors.append("G")
            abilities.extend(["Trample", "Reach"])

        # White keywords
        if any(
            word in prompt_lower
            for word in ["light", "heal", "protect", "angel", "knight", "justice"]
        ):
            colors.append("W")
            abilities.extend(["Vigilance", "Lifelink"])

        # Black keywords
        if any(
            word in prompt_lower
            for word in ["death", "dark", "shadow", "demon", "vampire", "necro"]
        ):
            colors.append("B")
            abilities.extend(["Deathtouch", "Menace"])

        if not colors:
            colors = [random.choice(["W", "U", "B", "R", "G"])]

        # Generate creative name
        name_parts = {
            "R": ["Flame", "Inferno", "Ember", "Scorching", "Blazing"],
            "U": ["Mystic", "Arcane", "Ethereal", "Temporal", "Mind"],
            "B": ["Shadow", "Death", "Cursed", "Grim", "Dark"],
            "G": ["Wild", "Primal", "Verdant", "Grove", "Nature's"],
            "W": ["Holy", "Divine", "Radiant", "Blessed", "Pure"],
        }

        type_names = {
            "dragon": ["Dragon", "Wyrm", "Drake"],
            "wizard": ["Wizard", "Mage", "Sorcerer"],
            "warrior": ["Warrior", "Champion", "Fighter"],
            "angel": ["Angel", "Seraph", "Guardian"],
            "demon": ["Demon", "Fiend", "Devil"],
            "beast": ["Beast", "Behemoth", "Creature"],
            "elemental": ["Elemental", "Spirit", "Incarnation"],
        }

        # Build name
        prefix = random.choice(name_parts.get(colors[0], ["Mystic"]))

        # Find matching type
        found_type = None
        for key, values in type_names.items():
            if key in prompt_lower:
                found_type = random.choice(values)
                break
        if not found_type:
            found_type = "Entity"

        name = f"{prefix} {found_type}"

        # Generate mana cost based on power
        if "powerful" in prompt_lower or "legendary" in prompt_lower:
            base_cost = random.randint(3, 5)
            rarity = "mythic"
        elif "weak" in prompt_lower or "small" in prompt_lower:
            base_cost = random.randint(1, 2)
            rarity = "common"
        else:
            base_cost = random.randint(2, 4)
            rarity = "uncommon"

        mana_cost = f"{{{base_cost}}}" + "".join([f"{{{c}}}" for c in colors[:2]])

        # Generate abilities text
        if is_creature:
            # Select 1-2 abilities
            selected_abilities = (
                random.sample(abilities, min(2, len(abilities)))
                if abilities
                else ["Haste"]
            )
            oracle_text = ", ".join(selected_abilities)

            # Add triggered ability based on prompt
            if "destroy" in prompt_lower:
                oracle_text += (
                    f"\nWhen {name} enters the battlefield, destroy target artifact."
                )
            elif "draw" in prompt_lower:
                oracle_text += f"\nWhen {name} enters the battlefield, draw a card."
            elif "damage" in prompt_lower:
                oracle_text += f"\nWhen {name} enters the battlefield, it deals 2 damage to any target."
            elif "create" in prompt_lower:
                oracle_text += (
                    f"\nWhen {name} enters the battlefield, create a 1/1 token."
                )

            # Calculate power/toughness based on cost
            total_mana = base_cost + len(colors)
            power = str(max(1, total_mana - 1))
            toughness = str(max(1, total_mana - 2))

            # Find creature type
            creature_type = "Elemental"
            for ct in [
                "Dragon",
                "Wizard",
                "Warrior",
                "Angel",
                "Demon",
                "Beast",
                "Phoenix",
                "Vampire",
            ]:
                if ct.lower() in prompt_lower:
                    creature_type = ct
                    break

            return {
                "name": name,
                "mana_cost": mana_cost,
                "type_line": f"{'Legendary ' if 'legendary' in prompt_lower else ''}Creature — {creature_type}",
                "oracle_text": oracle_text,
                "power": power,
                "toughness": toughness,
                "flavor_text": f'"{prompt_lower.capitalize()}."',
                "rarity": rarity,
                "colors": colors,
                "art_description": f"Epic fantasy art of a {prompt_lower}, highly detailed, magic the gathering style",
                "layout": "normal",
                "set": "AIC",
                "set_name": "AI Custom",
                "collector_number": "001",
                "artist": "AI Generated",
            }
        else:
            # Generate spell effect
            if "destroy" in prompt_lower:
                oracle_text = "Destroy target creature or artifact."
                spell_type = "Instant"
            elif "counter" in prompt_lower:
                oracle_text = "Counter target spell."
                spell_type = "Instant"
            elif "draw" in prompt_lower:
                oracle_text = f"Draw {random.randint(2,3)} cards."
                spell_type = "Sorcery"
            elif "damage" in prompt_lower:
                oracle_text = f"Deal {random.randint(3,5)} damage to any target."
                spell_type = "Instant"
            elif "create" in prompt_lower:
                oracle_text = f"Create {random.randint(2,3)} 1/1 creature tokens."
                spell_type = "Sorcery"
            else:
                oracle_text = "Draw two cards, then discard a card."
                spell_type = "Sorcery"

            return {
                "name": name,
                "mana_cost": mana_cost,
                "type_line": spell_type,
                "oracle_text": oracle_text,
                "flavor_text": f'"{prompt_lower.capitalize()}."',
                "rarity": rarity,
                "colors": colors,
                "art_description": f"Magical spell effect depicting {prompt_lower}, fantasy art style",
                "layout": "normal",
                "set": "AIC",
                "set_name": "AI Custom",
                "collector_number": "001",
                "artist": "AI Generated",
            }

    async def generate_complete_card(self, user_prompt: str):
        """Generate a complete MTG card from a single prompt."""
        print("\n" + "=" * 60)
        print("🎴 AI CARD GENERATOR")
        print("=" * 60)

        # Step 1: Generate card data using LLM
        card_data = await self.generate_card_data(user_prompt)
        if not card_data:
            print("Failed to generate card data")
            return None

        # Display generated card
        print("\n📋 Generated Card:")
        print(f"   Name: {card_data['name']}")
        print(f"   Cost: {card_data['mana_cost']}")
        print(f"   Type: {card_data['type_line']}")
        print(f"   Text: {card_data['oracle_text']}")
        if card_data.get("power"):
            print(f"   P/T: {card_data['power']}/{card_data['toughness']}")
        print(f"   Rarity: {card_data['rarity']}")

        # Step 2: Generate artwork
        print("\n🎨 Generating Artwork...")
        art_prompt = card_data.get("art_description", user_prompt)
        print(f"   Prompt: {art_prompt}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = card_data["name"].replace(" ", "_").replace(",", "")

        try:
            # Determine art style based on card type
            if "Dragon" in card_data["type_line"]:
                art_style = "mtg_classic"
            elif (
                "Horror" in card_data["type_line"] or "Zombie" in card_data["type_line"]
            ):
                art_style = "dark_gothic"
            elif "Angel" in card_data["type_line"]:
                art_style = "fantasy_art"
            else:
                art_style = "mtg_modern"

            image_path = self.image_generator.generate(
                prompt=art_prompt,
                style=art_style,
                output_name=f"{safe_name}_{timestamp}",
            )
            print("   ✅ Artwork generated")

            # Add image to card data
            if image_path:
                card_data["image_uris"] = {"art_crop": str(image_path.absolute())}
        except Exception as e:
            print(f"   ⚠️ Could not generate artwork: {e}")

        # Save card JSON
        json_path = self.output_dir / f"{safe_name}_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(card_data, f, indent=2)

        # Step 3: Render to PNG
        print("\n🖼️ Rendering Card to PNG...")
        png_path = await self.render_to_png(card_data, f"{safe_name}_{timestamp}")

        if png_path:
            print("\n" + "=" * 60)
            print("✨ SUCCESS!")
            print("=" * 60)
            print(f"📁 Card: {png_path}")
            print("📊 Size: 960x1344 px")
            print(f"📄 Data: {json_path}")
            return png_path

        return None

    async def render_to_png(self, card_json, output_name):
        """Render card JSON to PNG."""
        render_dir = self.base_dir / "mtg-card-generator" / "card-rendering"
        html_path = render_dir / "index.html"

        if not html_path.exists():
            print("   ❌ Renderer not found")
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1600, "height": 2400})

                await page.goto(f"file://{html_path.absolute()}")
                await page.wait_for_load_state("networkidle")

                await page.fill("#card-json", json.dumps(card_json, indent=2))
                await page.wait_for_timeout(500)

                await page.click("#render-button")
                await page.wait_for_selector(".mtg-card", timeout=5000)

                if "image_uris" in card_json:
                    await page.wait_for_timeout(3000)
                else:
                    await page.wait_for_timeout(1000)

                await page.evaluate(
                    """
                    () => {
                        const card = document.querySelector('.mtg-card');
                        if (card) {
                            card.style.transform = 'scale(4)';
                            card.style.transformOrigin = 'top left';
                        }
                    }
                """
                )
                await page.wait_for_timeout(500)

                card_element = await page.query_selector(".mtg-card")
                if card_element:
                    box = await card_element.bounding_box()
                    if box:
                        png_path = self.output_dir / f"{output_name}.png"
                        await page.screenshot(
                            path=str(png_path),
                            clip={
                                "x": box["x"],
                                "y": box["y"],
                                "width": box["width"],
                                "height": box["height"],
                            },
                            type="png",
                            omit_background=True,
                        )
                        await browser.close()
                        return png_path

                await browser.close()

        except Exception as e:
            print(f"   ❌ Render error: {e}")
            return None


async def main():
    """Main entry point."""
    print(
        """
╔══════════════════════════════════════════════════════════╗
║         🤖 AI-POWERED MTG CARD GENERATOR 🤖             ║
║                                                          ║
║  Describe any card concept and AI will create:          ║
║  • Card name, type, and mana cost                       ║
║  • Balanced abilities and stats                         ║
║  • Professional artwork                                 ║
║  • High-resolution card image                           ║
╚══════════════════════════════════════════════════════════╝
    """
    )

    generator = AICardGenerator()

    # Example prompts
    example_prompts = [
        "a powerful fire dragon that destroys artifacts",
        "a blue wizard that can copy spells",
        "a green nature elemental that creates forests",
        "a legendary vampire lord with lifelink",
        "a white angel that protects other creatures",
        "a colorless artifact creature that generates mana",
        "a black spell that resurrects creatures",
        "a red and blue instant that deals damage and draws cards",
    ]

    print("\n📝 Example prompts:")
    for i, prompt in enumerate(example_prompts[:5], 1):
        print(f"   {i}. {prompt}")

    print("\n💡 Enter your card concept (or number for example):")
    user_input = input("   > ").strip()

    # Check if user selected an example
    try:
        example_idx = int(user_input) - 1
        if 0 <= example_idx < len(example_prompts):
            user_prompt = example_prompts[example_idx]
            print(f"\n Using: {user_prompt}")
        else:
            user_prompt = user_input
    except:
        user_prompt = user_input

    if not user_prompt:
        user_prompt = "a legendary dragon with powerful abilities"
        print(f"Using default: {user_prompt}")

    # Generate the card
    await generator.generate_complete_card(user_prompt)

    # Ask if user wants to generate another
    print("\n🔄 Generate another card? (y/n)")
    if input("   > ").lower() == "y":
        await main()


if __name__ == "__main__":
    asyncio.run(main())
