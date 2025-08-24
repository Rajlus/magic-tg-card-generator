#!/usr/bin/env python3
"""
Unified MTG Card Generator - Combines automatic and manual card creation.
Supports command-line flags for quick generation or interactive mode.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.append(".")

from playwright.async_api import async_playwright

from generate_unified import UnifiedImageGenerator

try:
    from openai import OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class UnifiedCardGenerator:
    def __init__(self, output_dir: str = "output/cards", api_model: str = None):
        """Initialize the unified card generator."""
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / output_dir
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize image generator
        self.image_generator = UnifiedImageGenerator()
        if os.getenv("REPLICATE_API_TOKEN"):
            self.image_generator.mode = "api"

            # Available models
            available_models = {
                "sdxl": "stability-ai/sdxl",
                "sdxl-lightning": "bytedance/sdxl-lightning-4step",
                "flux-schnell": "black-forest-labs/flux-schnell",
                "flux-dev": "black-forest-labs/flux-dev",
                "playground": "playgroundai/playground-v2.5-1024px-aesthetic",
                "dalle3": "dalle-3 (requires OpenAI key instead)",
            }

            # Set model
            if api_model:
                if api_model in available_models:
                    self.image_generator.api_model = api_model
                    print(f"✅ Using image model: {api_model}")
                else:
                    print(f"⚠️ Unknown model '{api_model}', using default: sdxl")
                    print(f"   Available: {', '.join(available_models.keys())}")
                    self.image_generator.api_model = "sdxl"
            else:
                self.image_generator.api_model = "sdxl"
                print("ℹ️ Using default image model: sdxl")

            self.has_image_api = True
        else:
            self.has_image_api = False
            print("⚠️ No REPLICATE_API_TOKEN found - images will be placeholders")

        # Initialize LLM if available
        self.llm_client = None
        if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
            self.llm_client = OpenAI()
            self.has_llm = True
        else:
            self.has_llm = False

    def generate_from_prompt(self, prompt: str) -> dict:
        """Generate card details from a simple prompt using LLM or fallback."""
        import random

        if self.has_llm:
            return self._generate_with_llm(prompt)

        # Fallback generation without LLM
        prompt_lower = prompt.lower()

        # Determine colors
        colors = []
        if any(
            w in prompt_lower for w in ["fire", "burn", "dragon", "rage", "phoenix"]
        ):
            colors.append("R")
        if any(w in prompt_lower for w in ["water", "sea", "ocean", "wave", "wizard"]):
            colors.append("U")
        if any(
            w in prompt_lower for w in ["nature", "forest", "elf", "beast", "growth"]
        ):
            colors.append("G")
        if any(
            w in prompt_lower for w in ["light", "angel", "heal", "protect", "knight"]
        ):
            colors.append("W")
        if any(
            w in prompt_lower for w in ["death", "shadow", "vampire", "demon", "undead"]
        ):
            colors.append("B")

        if not colors:
            colors = [random.choice(["R", "U", "G", "W", "B"])]

        # Determine creature type
        creature_types = {
            "dragon": "Dragon",
            "wizard": "Wizard",
            "angel": "Angel",
            "demon": "Demon",
            "vampire": "Vampire",
            "beast": "Beast",
            "elemental": "Elemental",
            "warrior": "Warrior",
            "knight": "Knight",
            "phoenix": "Phoenix",
            "satyr": "Satyr",
            "demigod": "Demigod",
        }

        found_type = "Elemental"
        for keyword, ctype in creature_types.items():
            if keyword in prompt_lower:
                found_type = ctype
                break

        # Determine if legendary
        is_legendary = "legendary" in prompt_lower or any(
            name in prompt_lower for name in ["percy", "annabeth", "grover", "nico"]
        )

        # Generate name
        name_prefixes = {
            "R": ["Blazing", "Inferno", "Scorching", "Ember"],
            "U": ["Mystic", "Arcane", "Tidal", "Azure"],
            "G": ["Wild", "Verdant", "Primal", "Grove"],
            "W": ["Radiant", "Divine", "Holy", "Pure"],
            "B": ["Shadow", "Grim", "Dark", "Cursed"],
        }

        # Check for specific character names
        if "percy" in prompt_lower:
            name = "Percy Jackson, Son of the Sea"
            colors = ["U"]
            found_type = "Human Demigod"
        elif "annabeth" in prompt_lower:
            name = "Annabeth Chase, Wisdom's Daughter"
            colors = ["W", "U"]
            found_type = "Human Demigod"
        else:
            prefix = random.choice(name_prefixes.get(colors[0], ["Mystic"]))
            name = f"{prefix} {found_type}"
            if is_legendary:
                name = (
                    name
                    + ", "
                    + random.choice(["the Eternal", "the Mighty", "the Unbound"])
                )

        # Determine rarity and cost
        if is_legendary or "mythic" in prompt_lower:
            rarity = "mythic"
            base_cost = random.randint(3, 5)
        elif "powerful" in prompt_lower:
            rarity = "rare"
            base_cost = random.randint(3, 4)
        else:
            rarity = "uncommon"
            base_cost = random.randint(2, 3)

        mana_cost = f"{{{base_cost}}}" + "".join(f"{{{c}}}" for c in colors)

        # Generate abilities
        abilities = []
        if found_type == "Dragon" or "flying" in prompt_lower:
            abilities.append("Flying")
        if "R" in colors:
            abilities.append(random.choice(["Haste", "First strike"]))
        if "U" in colors:
            abilities.append(random.choice(["Hexproof", "Flying"]))
        if "G" in colors:
            abilities.append(random.choice(["Trample", "Reach"]))
        if "W" in colors:
            abilities.append(random.choice(["Vigilance", "Lifelink"]))
        if "B" in colors:
            abilities.append(random.choice(["Deathtouch", "Menace"]))

        oracle_text = ", ".join(abilities[:2]) if abilities else "Haste"

        # Add triggered ability
        if "destroy" in prompt_lower:
            oracle_text += f"\\nWhen {name.split(',')[0]} enters the battlefield, destroy target artifact."
        elif "draw" in prompt_lower:
            oracle_text += (
                f"\\nWhen {name.split(',')[0]} enters the battlefield, draw a card."
            )
        elif "damage" in prompt_lower:
            oracle_text += (
                f"\\n{colors[0]}: {name.split(',')[0]} deals 2 damage to any target."
            )

        # Power/Toughness
        total_cost = base_cost + len(colors)
        power = str(max(2, total_cost - 1))
        toughness = str(max(1, total_cost - 2))

        return {
            "name": name,
            "mana_cost": mana_cost,
            "type_line": f"{'Legendary ' if is_legendary else ''}Creature — {found_type}",
            "oracle_text": oracle_text,
            "power": power,
            "toughness": toughness,
            "flavor_text": f'"{prompt.capitalize()}"',
            "rarity": rarity,
            "colors": colors,
            "art_description": f"Epic fantasy art of {prompt}, highly detailed, magic the gathering style",
        }

    def _generate_with_llm(self, prompt: str) -> dict:
        """Generate card using OpenAI GPT."""
        system_prompt = """You are an expert Magic: The Gathering card designer.
        Create balanced, interesting cards. Return ONLY valid JSON with these fields:
        name, mana_cost, type_line, oracle_text, power (if creature), toughness (if creature),
        flavor_text, rarity, colors (array), art_description"""

        response = self.llm_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Create an MTG card based on: {prompt}"},
            ],
            temperature=0.8,
        )

        card_json = json.loads(response.choices[0].message.content)
        return card_json

    async def create_card(
        self,
        prompt: Optional[str] = None,
        name: Optional[str] = None,
        mana_cost: Optional[str] = None,
        type_line: Optional[str] = None,
        oracle_text: Optional[str] = None,
        power: Optional[str] = None,
        toughness: Optional[str] = None,
        flavor_text: Optional[str] = None,
        rarity: Optional[str] = None,
        art_description: Optional[str] = None,
        art_style: Optional[str] = None,
        interactive: bool = False,
    ):
        """Create a card with provided details or generate from prompt."""

        # Mode 1: Generate everything from prompt
        if prompt and not name:
            print(f"\n🤖 Generating card from prompt: '{prompt}'")
            card_data = self.generate_from_prompt(prompt)
            if not art_description:
                art_description = card_data.get("art_description", prompt)

        # Mode 2: Use provided details
        elif name:
            card_data = {
                "name": name,
                "mana_cost": mana_cost or "{2}",
                "type_line": type_line or "Creature",
                "oracle_text": oracle_text or "",
                "power": power,
                "toughness": toughness,
                "flavor_text": flavor_text or "",
                "rarity": rarity or "uncommon",
                "colors": self._extract_colors(mana_cost or "{2}"),
                "art_description": art_description or f"Fantasy art of {name}",
            }

        # Mode 3: Interactive input
        else:
            card_data = self._interactive_input()
            art_description = card_data.get("art_description")
            art_style = card_data.get("art_style", art_style)

        # Clean up oracle text
        if "oracle_text" in card_data:
            card_data["oracle_text"] = card_data["oracle_text"].replace("\\n", "\n")

        # Add metadata
        card_data.update(
            {
                "layout": "normal",
                "set": "CUS",
                "set_name": "Custom",
                "collector_number": "001",
                "artist": "AI Generated",
            }
        )

        print("\n📋 Card Details:")
        print(f"   Name: {card_data['name']}")
        print(f"   Cost: {card_data['mana_cost']}")
        print(f"   Type: {card_data['type_line']}")
        if card_data.get("power"):
            print(f"   P/T: {card_data['power']}/{card_data['toughness']}")

        # Generate artwork
        if self.has_image_api:
            print("\n🎨 Generating Artwork...")
            try:
                # Use art_description from card_data if not explicitly provided
                if not art_description:
                    # Check for known characters to provide better descriptions
                    name_lower = card_data["name"].lower()
                    if "percy" in name_lower and "jackson" in name_lower:
                        art_description = "teenage boy with black hair and green eyes, wielding bronze sword Riptide, surrounded by swirling water and sea creatures, wearing orange Camp Half-Blood t-shirt"
                    elif "annabeth" in name_lower:
                        art_description = "blonde teenage girl with grey eyes, holding bronze dagger, wearing Camp Half-Blood t-shirt, architectural blueprints floating around her"
                    elif "grover" in name_lower:
                        art_description = "young satyr with curly hair and goat legs, playing reed pipes, surrounded by nature magic and plants"
                    elif "nico" in name_lower:
                        art_description = "pale teenage boy in black clothes, summoning shadows and skeleton warriors, dark aura"
                    else:
                        art_description = card_data.get(
                            "art_description",
                            f"Epic fantasy art of {card_data['name']}, highly detailed, magic the gathering style",
                        )

                if not art_style:
                    # Auto-select style based on card type
                    if "Dragon" in card_data.get("type_line", ""):
                        art_style = "mtg_classic"
                    elif "Demon" in card_data.get(
                        "type_line", ""
                    ) or "Zombie" in card_data.get("type_line", ""):
                        art_style = "dark_gothic"
                    else:
                        art_style = "mtg_modern"

                print(f"   Prompt: {art_description[:80]}...")
                print(f"   Style: {art_style}")

                image_path = self.image_generator.generate(
                    prompt=art_description,
                    style=art_style,
                    output_name=card_data["name"].replace(" ", "_").replace(",", ""),
                )

                if image_path:
                    card_data["image_uris"] = {"art_crop": str(image_path.absolute())}
                    print("   ✅ Artwork generated")
            except Exception as e:
                print(f"   ⚠️ Artwork generation failed: {e}")

        # Save JSON
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = card_data["name"].replace(" ", "_").replace(",", "")
        json_path = self.output_dir / f"{safe_name}_{timestamp}.json"

        with open(json_path, "w") as f:
            json.dump(card_data, f, indent=2)

        # Render to PNG
        print("\n🖼️ Rendering Card...")
        png_path = await self._render_to_png(card_data, f"{safe_name}_{timestamp}")

        if png_path:
            print("\n" + "=" * 60)
            print("✨ SUCCESS!")
            print("=" * 60)
            print(f"📁 Card: {png_path}")
            print(f"📄 JSON: {json_path}")
            return png_path

        return None

    def _extract_colors(self, mana_cost: str) -> list:
        """Extract colors from mana cost."""
        colors = []
        if "W" in mana_cost:
            colors.append("W")
        if "U" in mana_cost:
            colors.append("U")
        if "B" in mana_cost:
            colors.append("B")
        if "R" in mana_cost:
            colors.append("R")
        if "G" in mana_cost:
            colors.append("G")
        return colors or ["C"]

    def _interactive_input(self) -> dict:
        """Get card details interactively."""
        print("\n" + "=" * 60)
        print("🎴 INTERACTIVE CARD CREATION")
        print("=" * 60)

        name = input("\n📝 Card Name: ") or "Custom Card"
        mana_cost = input("💎 Mana Cost ({2}{R}): ") or "{2}{R}"
        type_line = input("📋 Type (Creature — Dragon): ") or "Creature"
        oracle_text = input("📜 Text (use \\n for breaks): ") or ""

        power = None
        toughness = None
        if "creature" in type_line.lower():
            power = input("⚔️ Power: ") or "3"
            toughness = input("🛡️ Toughness: ") or "3"

        flavor_text = input("💭 Flavor Text: ") or ""
        rarity = input("⭐ Rarity (common/uncommon/rare/mythic): ") or "rare"
        art_description = input("🎨 Art Description: ") or f"Fantasy art of {name}"

        print("\n🖌️ Art Styles:")
        styles = [
            "realistic",
            "anime",
            "oil_painting",
            "watercolor",
            "comic_book",
            "fantasy_art",
            "dark_gothic",
            "steampunk",
            "cyberpunk",
            "mtg_classic",
            "mtg_modern",
            "mtg_sketch",
        ]
        for i, style in enumerate(styles, 1):
            print(f"   {i}. {style}")

        style_input = input("Choose style (number or name): ")
        try:
            style_idx = int(style_input) - 1
            art_style = (
                styles[style_idx] if 0 <= style_idx < len(styles) else "mtg_modern"
            )
        except:
            art_style = style_input if style_input in styles else "mtg_modern"

        return {
            "name": name,
            "mana_cost": mana_cost,
            "type_line": type_line,
            "oracle_text": oracle_text,
            "power": power,
            "toughness": toughness,
            "flavor_text": flavor_text,
            "rarity": rarity,
            "colors": self._extract_colors(mana_cost),
            "art_description": art_description,
            "art_style": art_style,
        }

    async def _render_to_png(self, card_json: dict, output_name: str):
        """Render card to PNG using Playwright."""
        render_dir = self.base_dir / "mtg-card-generator" / "card-rendering"
        html_path = render_dir / "index.html"

        if not html_path.exists():
            print("❌ Renderer not found")
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
            print(f"❌ Render error: {e}")

        return None


async def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Generate Magic: The Gathering cards with AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick generation from prompt
  %(prog)s "a legendary fire dragon"

  # Specify details with flags
  %(prog)s --name "Lightning Bolt" --cost "{R}" --type "Instant" --text "Deal 3 damage"

  # Percy Jackson card
  %(prog)s "Percy Jackson demigod son of Poseidon" --style mtg_modern

  # Interactive mode
  %(prog)s --interactive

  # Mix prompt with overrides
  %(prog)s "powerful wizard" --cost "{2}{U}{U}" --rarity mythic
        """,
    )

    # Arguments
    parser.add_argument("prompt", nargs="?", help="Card concept or description")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Interactive mode"
    )

    # Card details
    parser.add_argument("--name", help="Card name")
    parser.add_argument(
        "--cost", "--mana", dest="mana_cost", help="Mana cost (e.g., {2}{R}{R})"
    )
    parser.add_argument(
        "--type", dest="type_line", help="Card type (e.g., 'Creature — Dragon')"
    )
    parser.add_argument("--text", dest="oracle_text", help="Card text/abilities")
    parser.add_argument("--power", help="Power (for creatures)")
    parser.add_argument("--toughness", help="Toughness (for creatures)")
    parser.add_argument("--flavor", dest="flavor_text", help="Flavor text")
    parser.add_argument(
        "--rarity", choices=["common", "uncommon", "rare", "mythic"], help="Card rarity"
    )

    # Art options
    parser.add_argument("--art", dest="art_description", help="Art description")
    parser.add_argument(
        "--style",
        dest="art_style",
        choices=[
            "realistic",
            "anime",
            "oil_painting",
            "watercolor",
            "comic_book",
            "fantasy_art",
            "dark_gothic",
            "steampunk",
            "cyberpunk",
            "mtg_classic",
            "mtg_modern",
            "mtg_sketch",
        ],
        help="Art style",
    )

    # Model selection
    parser.add_argument(
        "--model",
        dest="api_model",
        choices=["sdxl", "sdxl-lightning", "flux-schnell", "flux-dev", "playground"],
        default="sdxl",
        help="Image generation model (default: sdxl)",
    )

    # Output
    parser.add_argument("--output", default="output/cards", help="Output directory")

    args = parser.parse_args()

    # Create generator
    generator = UnifiedCardGenerator(output_dir=args.output, api_model=args.api_model)

    # Print header
    print(
        """
╔══════════════════════════════════════════════════════════╗
║            🎴 UNIFIED MTG CARD GENERATOR 🎴             ║
║                                                          ║
║  Create cards from prompts or detailed specifications    ║
╚══════════════════════════════════════════════════════════╝
    """
    )

    # Determine mode and create card
    if args.interactive or (not args.prompt and not args.name):
        # Interactive mode
        await generator.create_card(interactive=True)
    else:
        # Command-line mode
        await generator.create_card(
            prompt=args.prompt,
            name=args.name,
            mana_cost=args.mana_cost,
            type_line=args.type_line,
            oracle_text=args.oracle_text,
            power=args.power,
            toughness=args.toughness,
            flavor_text=args.flavor_text,
            rarity=args.rarity,
            art_description=args.art_description,
            art_style=args.art_style,
        )


if __name__ == "__main__":
    asyncio.run(main())
