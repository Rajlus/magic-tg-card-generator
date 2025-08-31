# MTG Deck XML Import/Export Guide

## Overview
The MTG Deck Builder now supports XML format for importing and exporting decks. This allows for:
- Easy sharing of decks with other applications
- Bulk importing of card sets
- Deck backups in a universal format
- Integration with external deck building tools

## GUI Usage

### Exporting to XML
1. Load a deck in the application
2. Click the "📤 Export XML" button in the toolbar
3. Choose a location and filename for the XML file
4. The deck will be exported with all card data preserved

### Importing from XML
1. Click the "📥 Import XML" button in the toolbar
2. Select an XML file to import
3. The deck will be converted to YAML format and automatically loaded
4. The new deck file will be saved in `saved_decks/deck_[xml_filename].yaml`

## Command Line Usage

The `mtg_xml_parser.py` script provides command-line functionality:

### Export YAML to XML
```bash
python mtg_xml_parser.py export saved_decks/your_deck.yaml -o output.xml
```

### Import XML to YAML
```bash
python mtg_xml_parser.py import input.xml -o saved_decks/new_deck.yaml
```

### Validate XML File
```bash
python mtg_xml_parser.py validate deck.xml
```

### Merge Multiple XML Files
```bash
python mtg_xml_parser.py merge deck1.xml deck2.xml deck3.xml -o merged_deck.yaml
```

## XML Format Specification

### Basic Structure
```xml
<?xml version="1.0" ?>
<deck version="1.0">
  <metadata>
    <name>Deck Name</name>
    <description>Deck Description</description>
    <format>Commander</format>
  </metadata>
  <cards count="100">
    <card id="1" power="3" toughness="4" status="pending">
      <name>Card Name</name>
      <type>Creature Type</type>
      <cost>{2}{U}{G}</cost>
      <text>Card abilities and rules text</text>
      <flavor>Flavor text</flavor>
      <rarity>rare</rarity>
      <art>Art description for generation</art>
    </card>
    <!-- More cards... -->
  </cards>
</deck>
```

### Card Attributes
- **id**: Unique card identifier (required)
- **power/toughness**: For creatures (optional)
- **status**: Generation status (pending/completed/failed)

### Card Elements
- **name**: Card name (required)
- **type**: Card type (required)
- **cost**: Mana cost
- **text**: Rules text
- **flavor**: Flavor text
- **rarity**: common/uncommon/rare/mythic
- **art**: Art description for image generation

## Example XML Files

### Minimal Card
```xml
<card id="1" status="pending">
  <name>Simple Land</name>
  <type>Land</type>
  <text>T: Add {G}.</text>
</card>
```

### Creature Card
```xml
<card id="2" power="2" toughness="2" status="pending">
  <name>Forest Guardian</name>
  <type>Creature — Elf Warrior</type>
  <cost>{1}{G}</cost>
  <text>Vigilance</text>
  <flavor>Protector of the ancient woods.</flavor>
  <rarity>common</rarity>
  <art>An elven warrior standing guard in a mystical forest</art>
</card>
```

### Spell Card
```xml
<card id="3" status="pending">
  <name>Lightning Strike</name>
  <type>Instant</type>
  <cost>{1}{R}</cost>
  <text>Lightning Strike deals 3 damage to any target.</text>
  <flavor>Thunder follows lightning.</flavor>
  <rarity>common</rarity>
  <art>A powerful bolt of lightning striking from stormy skies</art>
</card>
```

## Tips for XML Creation

1. **Card IDs**: Must be unique within the deck
2. **Status Field**: Set to "pending" for new cards that need generation
3. **Art Descriptions**: Provide detailed descriptions for better image generation
4. **Mana Costs**: Use standard MTG notation: {W}, {U}, {B}, {R}, {G}, {C}, {X}
5. **German Text**: The application supports German card text and names

## Integration with Other Tools

The XML format is designed to be compatible with common MTG deck building standards. You can:
- Export from other deck builders to XML
- Modify XML files with any text editor
- Use scripts to batch-process cards
- Version control your decks in XML format

## Troubleshooting

### Common Issues
1. **Invalid XML**: Ensure proper XML syntax with closing tags
2. **Missing Required Fields**: Every card needs at least `name` and `type`
3. **Encoding Issues**: Use UTF-8 encoding for special characters
4. **File Path Issues**: Use absolute paths or ensure relative paths are correct

### Validation
Always validate your XML before importing:
```bash
python mtg_xml_parser.py validate your_deck.xml
```

This will check for:
- Proper XML structure
- Required fields
- Valid card count
- Syntax errors
