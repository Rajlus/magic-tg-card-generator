#!/usr/bin/env python3
"""Quick script to generate Magic card images."""

from pathlib import Path
import sys

# Add src to path for direct execution
sys.path.insert(0, str(Path(__file__).parent / "src"))

from magic_tg_card_generator.generate_image import main

if __name__ == "__main__":
    exit(main())