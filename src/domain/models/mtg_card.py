"""
MTG Card Domain Model

This module contains the core MTGCard class that represents a Magic: The Gathering card
with all its attributes and business logic methods.

Extracted from mtg_deck_builder.py as part of the domain model refactoring.
"""

from dataclasses import dataclass
from typing import Optional


def make_safe_filename(name: str) -> str:
    """Convert a card name to a safe filename, matching generate_card.py logic."""
    safe_name = name
    # Replace problematic characters with underscores
    for char in [
        "/",
        "\\",
        ":",
        "*",
        "?",
        '"',
        "<",
        ">",
        "|",
        "\u202f",
        "\u00a0",
        "—",
        "–",
    ]:
        safe_name = safe_name.replace(char, "_")
    # Replace spaces, commas, and apostrophes
    safe_name = safe_name.replace(" ", "_").replace(",", "").replace("'", "")
    return safe_name


def escape_for_shell(text: str) -> str:
    """Escape text for shell command"""
    # Replace double quotes with escaped double quotes
    text = str(text).replace('"', '\\"')
    # Return with double quotes around it
    return f'"{text}"'


def convert_mana_cost(cost) -> str:
    """Convert mana cost from compact format (2UR) to MTG format ({2}{U}{R})."""
    # Convert to string if it's an integer
    cost = str(cost) if cost is not None else ""

    if not cost or cost == "-" or cost == "":
        return ""

    # If already in the correct format, return as is
    if "{" in cost and "}" in cost:
        return cost

    # Convert compact format to MTG format
    result = ""
    i = 0
    while i < len(cost):
        char = cost[i]
        # Check if it's a number (generic mana)
        if char.isdigit():
            # Look ahead for multi-digit numbers
            j = i
            while j < len(cost) and cost[j].isdigit():
                j += 1
            result += "{" + cost[i:j] + "}"
            i = j
        # Check if it's a mana symbol (W, U, B, R, G, C, X)
        elif char.upper() in "WUBRGCX":
            result += "{" + char.upper() + "}"
            i += 1
        else:
            # Skip unknown characters
            i += 1

    return result


@dataclass
class MTGCard:
    """Represents a single MTG card with all attributes"""

    id: int
    name: str
    type: str
    cost: str = ""
    text: str = ""
    power: Optional[int] = None
    toughness: Optional[int] = None
    flavor: str = ""
    rarity: str = "common"
    art: str = ""
    set: str = "CMD"  # Card set, defaults to Commander
    status: str = "pending"  # pending, generating, completed, failed
    image_path: Optional[str] = None  # Path to card artwork image
    card_path: Optional[str] = None  # Path to full card image
    generated_at: Optional[str] = None  # Timestamp when generated
    generation_status: str = "pending"  # For tracking individual generation
    custom_image_path: Optional[str] = None  # Path to custom uploaded image

    def is_creature(self) -> bool:
        # Check for both English and German, including compound words
        type_lower = self.type.lower()
        return any(word in type_lower for word in ["creature", "kreatur"])

    def is_land(self) -> bool:
        # Works for both English and German (both use "Land")
        return "Land" in self.type

    def get_command(self, model: str = "sdxl", style: str = "mtg_modern") -> str:
        """Generate the command for generate_card.py"""
        # Use unbuffered Python output (-u flag) to ensure logs are captured immediately
        cmd_parts = ["poetry", "run", "python", "-u", "generate_card.py"]

        # Add name
        cmd_parts.extend(["--name", escape_for_shell(self.name)])

        # Add cost if not a land (lands have no mana cost)
        if not self.is_land() and self.cost:
            # Convert mana cost to proper MTG format
            formatted_cost = convert_mana_cost(self.cost)
            if formatted_cost:
                cmd_parts.extend(["--cost", escape_for_shell(formatted_cost)])

        # Add type
        cmd_parts.extend(["--type", escape_for_shell(self.type)])

        # Add text - ALWAYS include text, even for lands
        if self.text:
            cmd_parts.extend(["--text", escape_for_shell(self.text)])

        # Add P/T if creature - with debug logging
        if self.is_creature():
            # Always add P/T for creatures, even if values might be None
            if self.power is not None and self.toughness is not None:
                cmd_parts.extend(["--power", str(self.power)])
                cmd_parts.extend(["--toughness", str(self.toughness)])
            else:
                # Log error - creature MUST have P/T
                print(
                    f"ERROR: Creature '{self.name}' has invalid P/T: power={self.power}, toughness={self.toughness}"
                )
                # Still try to add what we have to avoid black card
                if self.power is not None:
                    cmd_parts.extend(["--power", str(self.power)])
                if self.toughness is not None:
                    cmd_parts.extend(["--toughness", str(self.toughness)])

        # Add flavor if exists
        if self.flavor:
            cmd_parts.extend(["--flavor", escape_for_shell(self.flavor)])

        # Add rarity
        cmd_parts.extend(["--rarity", self.rarity])

        # Add art description
        if self.art:
            cmd_parts.extend(["--art", escape_for_shell(self.art)])

        # Add model and style
        cmd_parts.extend(["--model", model])
        cmd_parts.extend(["--style", style])

        # Add custom image path if provided
        if hasattr(self, "custom_image_path") and self.custom_image_path:
            cmd_parts.extend(
                ["--custom-image", escape_for_shell(str(self.custom_image_path))]
            )

        return " ".join(cmd_parts)