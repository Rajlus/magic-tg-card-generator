#!/usr/bin/env python3
"""
Complete MTG Card Creator - From concept to finished PNG with artwork.
Creates a new Magic card with AI-generated artwork and professional layout.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.append(".")

import os

from generate_unified import UnifiedImageGenerator


class MTGCardCreator:
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / "output" / "custom_cards"
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Initialize image generator with API configuration
        self.image_generator = UnifiedImageGenerator()

        # Configure API mode if token available
        if os.getenv("REPLICATE_API_TOKEN"):
            self.image_generator.mode = "api"
            self.image_generator.api_model = "sdxl"  # Use working SDXL model
            print("✅ Using Replicate API for artwork generation")
        else:
            self.image_generator.mode = "local"
            print("⚠️ No API token found - artwork generation may fail")

    def get_card_details(self):
        """Interactive prompt for card details."""
        print("\n" + "=" * 60)
        print("🎴 MTG CARD CREATOR - Create Your Custom Card!")
        print("=" * 60)

        # Basic info
        name = input("\n📝 Card Name: ") or "Custom Card"

        # Mana cost
        print("\n💎 Mana Cost (Examples: {2}{R}{R}, {1}{U}, {W}{W}, {3})")
        mana_cost = input("   Mana Cost: ") or "{2}{R}"

        # Card type
        print(
            "\n📋 Card Type (Examples: Creature — Dragon, Instant, Sorcery, Enchantment)"
        )
        type_line = input("   Type: ") or "Creature — Dragon"

        # Card text
        print("\n📜 Card Text (Use \\n for line breaks)")
        print("   Example: Flying, haste\\nWhen ~ enters the battlefield, draw a card.")
        oracle_text = input("   Text: ") or "Flying"
        oracle_text = oracle_text.replace("\\n", "\n").replace("~", name)

        # Power/Toughness (for creatures)
        power = None
        toughness = None
        if "creature" in type_line.lower():
            print("\n⚔️ Power/Toughness")
            power = input("   Power: ") or "3"
            toughness = input("   Toughness: ") or "3"

        # Flavor text
        flavor_text = input("\n💭 Flavor Text (optional): ")

        # Rarity
        print("\n⭐ Rarity (common/uncommon/rare/mythic)")
        rarity = input("   Rarity: ") or "rare"

        # Art description
        print("\n🎨 Artwork Description")
        print("   Describe what should be shown on the card art:")
        art_prompt = input("   Art: ") or f"fantasy art of {name}"

        # Art style
        print("\n🖌️ Art Style Options:")
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
        style_choice = input("   Choose style (number or name): ")

        try:
            style_idx = int(style_choice) - 1
            art_style = (
                styles[style_idx] if 0 <= style_idx < len(styles) else "mtg_classic"
            )
        except:
            art_style = style_choice if style_choice in styles else "mtg_classic"

        # Determine colors from mana cost
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

        return {
            "name": name,
            "mana_cost": mana_cost,
            "type_line": type_line,
            "oracle_text": oracle_text,
            "power": power,
            "toughness": toughness,
            "flavor_text": flavor_text,
            "rarity": rarity,
            "art_prompt": art_prompt,
            "art_style": art_style,
            "colors": colors,
            "layout": "normal",
            "set": "CUS",
            "set_name": "Custom Set",
            "collector_number": "001",
            "artist": "AI Generated",
        }

    async def create_card(self, card_details=None):
        """Create a complete MTG card with artwork."""

        # Get card details interactively if not provided
        if not card_details:
            card_details = self.get_card_details()

        print("\n" + "=" * 60)
        print(f"🎴 Creating: {card_details['name']}")
        print("=" * 60)

        # Step 1: Generate artwork
        print("\n🎨 Step 1: Generating Artwork...")
        print(f"   Prompt: {card_details['art_prompt']}")
        print(f"   Style: {card_details['art_style']}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = card_details["name"].replace(" ", "_").replace(",", "")

        try:
            # Try API first (faster)
            image_path = self.image_generator.generate(
                prompt=card_details["art_prompt"],
                style=card_details["art_style"],
                output_name=f"{safe_name}_{timestamp}",
            )
            print(f"   ✅ Artwork generated: {image_path.name}")
        except Exception as e:
            print(f"   ⚠️ Could not generate artwork: {e}")
            print("   Using placeholder yellow background")
            image_path = None

        # Step 2: Create card JSON
        print("\n📋 Step 2: Creating Card Data...")
        card_json = {
            "name": card_details["name"],
            "mana_cost": card_details["mana_cost"],
            "type_line": card_details["type_line"],
            "oracle_text": card_details["oracle_text"],
            "flavor_text": card_details["flavor_text"],
            "rarity": card_details["rarity"],
            "colors": card_details["colors"],
            "layout": card_details["layout"],
            "set": card_details["set"],
            "set_name": card_details["set_name"],
            "collector_number": card_details["collector_number"],
            "artist": card_details["artist"],
        }

        # Add power/toughness if creature
        if card_details["power"]:
            card_json["power"] = card_details["power"]
            card_json["toughness"] = card_details["toughness"]

        # Add image if generated
        if image_path:
            card_json["image_uris"] = {"art_crop": str(image_path.absolute())}

        # Save card JSON
        json_path = self.output_dir / f"{safe_name}_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(card_json, f, indent=2)
        print(f"   ✅ Card data saved: {json_path.name}")

        # Step 3: Render to PNG
        print("\n🖼️ Step 3: Rendering Card to PNG...")
        png_path = await self.render_to_png(card_json, f"{safe_name}_{timestamp}")

        if png_path:
            print("\n" + "=" * 60)
            print("✨ SUCCESS! Your card has been created!")
            print("=" * 60)
            print(f"📁 Card Location: {png_path}")
            print("📊 Dimensions: 960x1344 px (high resolution)")
            if image_path:
                print(f"🎨 Artwork: {image_path.name}")
            print(f"📄 JSON Data: {json_path.name}")

            return png_path
        else:
            print("\n❌ Failed to render card to PNG")
            return None

    async def render_to_png(self, card_json, output_name):
        """Render card JSON to PNG using Playwright."""

        render_dir = self.base_dir / "mtg-card-generator" / "card-rendering"
        html_path = render_dir / "index.html"

        if not html_path.exists():
            print(f"   ❌ Error: Renderer not found at {html_path}")
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1600, "height": 2400})

                # Load renderer
                await page.goto(f"file://{html_path.absolute()}")
                await page.wait_for_load_state("networkidle")

                # Inject card data
                await page.fill("#card-json", json.dumps(card_json, indent=2))
                await page.wait_for_timeout(500)

                # Click render
                await page.click("#render-button")
                await page.wait_for_selector(".mtg-card", timeout=5000)

                # Wait for image to load if present
                if "image_uris" in card_json:
                    await page.wait_for_timeout(3000)
                else:
                    await page.wait_for_timeout(1000)

                # Apply 4x scale for quality
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

                # Screenshot
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
                        print("   ✅ Card rendered to PNG")
                        await browser.close()
                        return png_path

                await browser.close()

        except Exception as e:
            print(f"   ❌ Rendering error: {e}")
            return None


async def main():
    """Main entry point."""
    creator = MTGCardCreator()

    # Example: Create card with predefined details (uncomment to use)
    # predefined_card = {
    #     "name": "Lightning Phoenix",
    #     "mana_cost": "{2}{R}{R}",
    #     "type_line": "Creature — Phoenix",
    #     "oracle_text": "Flying, haste\nWhen Lightning Phoenix dies, return it to the battlefield at the beginning of the next end step.",
    #     "power": "4",
    #     "toughness": "2",
    #     "flavor_text": "\"From ashes to flame, the cycle continues.\"",
    #     "rarity": "mythic",
    #     "art_prompt": "majestic phoenix made of lightning and fire, soaring through storm clouds, fantasy art, highly detailed",
    #     "art_style": "mtg_modern",
    #     "colors": ["R"],
    #     "layout": "normal",
    #     "set": "CUS",
    #     "set_name": "Custom Set",
    #     "collector_number": "001",
    #     "artist": "AI Generated"
    # }
    # await creator.create_card(predefined_card)

    # Interactive mode
    await creator.create_card()


if __name__ == "__main__":
    print(
        """
╔══════════════════════════════════════════════════════════╗
║           🎴 MTG CUSTOM CARD CREATOR 🎴                  ║
║                                                          ║
║  Create professional Magic: The Gathering cards with     ║
║  AI-generated artwork and authentic card layouts!        ║
╚══════════════════════════════════════════════════════════╝
    """
    )

    asyncio.run(main())
