#!/usr/bin/env python3
"""
MTG Deck XML Parser - Import/Export functionality for MTG decks
Supports conversion between XML and YAML formats
"""

import argparse
import sys
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List

import yaml


class MTGXMLParser:
    """Parser for converting MTG decks between XML and YAML formats"""

    def __init__(self):
        self.deck_data = {}

    def yaml_to_xml(self, yaml_path: str, xml_path: str = None) -> str:
        """
        Convert a YAML deck file to XML format

        Args:
            yaml_path: Path to input YAML file
            xml_path: Path to output XML file (optional)

        Returns:
            Path to created XML file
        """
        # Load YAML deck
        with open(yaml_path, encoding="utf-8") as f:
            deck_data = yaml.safe_load(f)

        # Create XML root element
        root = ET.Element("deck")
        root.set("version", "1.0")

        # Add deck metadata
        if "name" in deck_data:
            meta = ET.SubElement(root, "metadata")
            name_elem = ET.SubElement(meta, "name")
            name_elem.text = deck_data["name"]

            if "description" in deck_data:
                desc_elem = ET.SubElement(meta, "description")
                desc_elem.text = deck_data["description"]

            if "format" in deck_data:
                format_elem = ET.SubElement(meta, "format")
                format_elem.text = deck_data["format"]

        # Add cards
        cards_elem = ET.SubElement(root, "cards")
        cards_elem.set("count", str(len(deck_data.get("cards", []))))

        for card in deck_data.get("cards", []):
            card_elem = ET.SubElement(cards_elem, "card")

            # Add all card attributes
            for key, value in card.items():
                if value is not None:
                    if key in ["power", "toughness", "id"]:
                        # Numeric attributes
                        card_elem.set(key, str(value))
                    elif key == "status":
                        # Status as attribute
                        card_elem.set("status", str(value))
                    else:
                        # Text elements
                        elem = ET.SubElement(card_elem, key)
                        elem.text = str(value) if value else ""

        # Format XML with indentation
        xml_str = ET.tostring(root, encoding="unicode")
        dom = minidom.parseString(xml_str)
        pretty_xml = dom.toprettyxml(indent="  ")

        # Remove extra blank lines
        lines = [line for line in pretty_xml.split("\n") if line.strip()]
        pretty_xml = "\n".join(lines)

        # Save to file
        if xml_path is None:
            yaml_file = Path(yaml_path)
            xml_path = yaml_file.parent / f"{yaml_file.stem}.xml"

        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        print(f"✅ Exported deck to: {xml_path}")
        return xml_path

    def xml_to_yaml(self, xml_path: str, yaml_path: str = None) -> str:
        """
        Convert an XML deck file to YAML format

        Args:
            xml_path: Path to input XML file
            yaml_path: Path to output YAML file (optional)

        Returns:
            Path to created YAML file
        """
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()

        deck_data = {}

        # Parse metadata
        meta = root.find("metadata")
        if meta is not None:
            name = meta.find("name")
            if name is not None and name.text:
                deck_data["name"] = name.text

            desc = meta.find("description")
            if desc is not None and desc.text:
                deck_data["description"] = desc.text

            format_elem = meta.find("format")
            if format_elem is not None and format_elem.text:
                deck_data["format"] = format_elem.text

        # Parse cards
        cards = []
        cards_elem = root.find("cards")

        if cards_elem is not None:
            for card_elem in cards_elem.findall("card"):
                card = {}

                # Get attributes
                for attr in ["id", "power", "toughness", "status"]:
                    if attr in card_elem.attrib:
                        value = card_elem.get(attr)
                        if attr in ["id", "power", "toughness"]:
                            # Convert to int if possible
                            try:
                                card[attr] = int(value)
                            except (ValueError, TypeError):
                                card[attr] = value
                        else:
                            card[attr] = value

                # Get child elements
                for child in card_elem:
                    if child.text:
                        card[child.tag] = child.text
                    else:
                        card[child.tag] = ""

                # Ensure required fields
                if "id" not in card:
                    card["id"] = len(cards) + 1
                if "status" not in card:
                    card["status"] = "pending"

                cards.append(card)

        deck_data["cards"] = cards

        # Save to YAML
        if yaml_path is None:
            xml_file = Path(xml_path)
            yaml_path = xml_file.parent / f"deck_{xml_file.stem}.yaml"

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(
                deck_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        print(f"✅ Imported deck to: {yaml_path}")
        print(f"   Total cards: {len(cards)}")

        return yaml_path

    def validate_xml(self, xml_path: str) -> bool:
        """
        Validate an XML deck file

        Args:
            xml_path: Path to XML file to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            if root.tag != "deck":
                print(f"❌ Invalid root element: {root.tag} (expected 'deck')")
                return False

            cards_elem = root.find("cards")
            if cards_elem is None:
                print("❌ No cards element found")
                return False

            card_count = 0
            for card in cards_elem.findall("card"):
                card_count += 1

                # Check for required fields
                name = card.find("name")
                if name is None or not name.text:
                    print(f"❌ Card {card_count} missing name")
                    return False

                type_elem = card.find("type")
                if type_elem is None or not type_elem.text:
                    print(f"❌ Card {card_count} ({name.text}) missing type")
                    return False

            print(f"✅ XML validation successful: {card_count} cards found")
            return True

        except ET.ParseError as e:
            print(f"❌ XML parsing error: {e}")
            return False
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False

    def merge_decks(self, xml_files: list[str], output_yaml: str) -> str:
        """
        Merge multiple XML deck files into a single YAML deck

        Args:
            xml_files: List of XML files to merge
            output_yaml: Output YAML file path

        Returns:
            Path to created YAML file
        """
        merged_deck = {
            "name": "Merged Deck",
            "description": f"Merged from {len(xml_files)} deck files",
            "cards": [],
        }

        card_id = 1

        for xml_file in xml_files:
            print(f"Merging: {xml_file}")

            tree = ET.parse(xml_file)
            root = tree.getroot()

            cards_elem = root.find("cards")
            if cards_elem is not None:
                for card_elem in cards_elem.findall("card"):
                    card = {"id": card_id}

                    # Get attributes
                    for attr in ["power", "toughness", "status"]:
                        if attr in card_elem.attrib:
                            value = card_elem.get(attr)
                            if attr in ["power", "toughness"]:
                                try:
                                    card[attr] = int(value)
                                except (ValueError, TypeError):
                                    card[attr] = value
                            else:
                                card[attr] = value

                    # Get child elements
                    for child in card_elem:
                        if child.text:
                            card[child.tag] = child.text
                        else:
                            card[child.tag] = ""

                    # Ensure status
                    if "status" not in card:
                        card["status"] = "pending"

                    merged_deck["cards"].append(card)
                    card_id += 1

        # Save merged deck
        with open(output_yaml, "w", encoding="utf-8") as f:
            yaml.dump(
                merged_deck,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )

        print(f"✅ Merged {len(merged_deck['cards'])} cards into: {output_yaml}")
        return output_yaml


def main():
    """Command-line interface for the XML parser"""
    parser = argparse.ArgumentParser(
        description="MTG Deck XML Parser - Convert between XML and YAML formats"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Export command (YAML to XML)
    export_parser = subparsers.add_parser("export", help="Export YAML deck to XML")
    export_parser.add_argument("yaml_file", help="Input YAML deck file")
    export_parser.add_argument("-o", "--output", help="Output XML file (optional)")

    # Import command (XML to YAML)
    import_parser = subparsers.add_parser("import", help="Import XML deck to YAML")
    import_parser.add_argument("xml_file", help="Input XML deck file")
    import_parser.add_argument("-o", "--output", help="Output YAML file (optional)")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate XML deck file")
    validate_parser.add_argument("xml_file", help="XML file to validate")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge multiple XML decks")
    merge_parser.add_argument("xml_files", nargs="+", help="XML files to merge")
    merge_parser.add_argument("-o", "--output", required=True, help="Output YAML file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    mtg_parser = MTGXMLParser()

    try:
        if args.command == "export":
            mtg_parser.yaml_to_xml(args.yaml_file, args.output)

        elif args.command == "import":
            mtg_parser.xml_to_yaml(args.xml_file, args.output)

        elif args.command == "validate":
            if mtg_parser.validate_xml(args.xml_file):
                sys.exit(0)
            else:
                sys.exit(1)

        elif args.command == "merge":
            mtg_parser.merge_decks(args.xml_files, args.output)

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
