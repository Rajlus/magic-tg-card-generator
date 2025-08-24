#!/usr/bin/env python3
"""
Clean up and organize MTG card output folder.
- Delete all JSON files
- Identify and delete cards with yellow placeholders
- Move all good cards to a consolidated folder
"""

import shutil
from pathlib import Path

import numpy as np
from PIL import Image


def has_yellow_placeholder(image_path):
    """Check if card has the yellow placeholder instead of real artwork."""
    try:
        img = Image.open(image_path)
        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Get image as numpy array
        img_array = np.array(img)

        # Sample the artwork area (approximately center-upper part of card)
        height, width = img_array.shape[:2]

        # Sample region where artwork should be (adjust based on card layout)
        # Roughly: top 20-60% vertically, middle 80% horizontally
        y_start = int(height * 0.15)
        y_end = int(height * 0.55)
        x_start = int(width * 0.1)
        x_end = int(width * 0.9)

        artwork_region = img_array[y_start:y_end, x_start:x_end]

        # Check for dominant yellow color (RGB ~255, 255, 0)
        # Yellow has high R and G, low B
        avg_color = artwork_region.mean(axis=(0, 1))

        # Criteria for yellow placeholder:
        # High red (>200), high green (>200), low blue (<100)
        # and low variance (solid color)
        is_yellow = (
            avg_color[0] > 200
            and avg_color[1] > 200  # Red channel
            and avg_color[2] < 100  # Green channel
        )  # Blue channel

        if is_yellow:
            # Additional check: low variance means solid color
            color_std = artwork_region.std(axis=(0, 1)).mean()
            if color_std < 30:  # Low variance = solid color
                return True

        return False

    except Exception as e:
        print(f"Error checking {image_path}: {e}")
        return False


def cleanup_output_folder():
    """Main cleanup function."""
    base_dir = Path(__file__).parent
    output_dir = base_dir / "output"

    if not output_dir.exists():
        print("No output folder found!")
        return

    # Create consolidated folder
    consolidated_dir = output_dir / "all_cards"
    consolidated_dir.mkdir(exist_ok=True)

    # Track statistics
    stats = {
        "json_deleted": 0,
        "cards_with_placeholder": 0,
        "good_cards_moved": 0,
        "total_cards": 0,
    }

    print("🧹 Starting cleanup...")
    print("-" * 50)

    # Process all subdirectories
    for subdir in output_dir.iterdir():
        if not subdir.is_dir() or subdir.name == "all_cards" or subdir.name == "images":
            continue

        print(f"\n📁 Processing: {subdir.name}/")

        # Delete JSON files
        for json_file in subdir.glob("*.json"):
            json_file.unlink()
            stats["json_deleted"] += 1
            print(f"   🗑️ Deleted JSON: {json_file.name}")

        # Process PNG files
        for png_file in subdir.glob("*.png"):
            stats["total_cards"] += 1

            # Check for yellow placeholder
            if has_yellow_placeholder(png_file):
                png_file.unlink()
                stats["cards_with_placeholder"] += 1
                print(f"   🟡 Deleted (placeholder): {png_file.name}")
            else:
                # Move good card to consolidated folder
                dest = consolidated_dir / png_file.name

                # Handle duplicates by adding number
                if dest.exists():
                    base = dest.stem
                    ext = dest.suffix
                    counter = 1
                    while dest.exists():
                        dest = consolidated_dir / f"{base}_{counter}{ext}"
                        counter += 1

                shutil.move(str(png_file), str(dest))
                stats["good_cards_moved"] += 1
                print(f"   ✅ Moved: {png_file.name}")

    # Clean up empty directories
    for subdir in output_dir.iterdir():
        if subdir.is_dir() and subdir.name not in ["all_cards", "images"]:
            if not any(subdir.iterdir()):
                subdir.rmdir()
                print(f"\n🗑️ Removed empty directory: {subdir.name}/")

    # Print summary
    print("\n" + "=" * 50)
    print("✨ CLEANUP COMPLETE!")
    print("=" * 50)
    print("📊 Statistics:")
    print(f"   • JSON files deleted: {stats['json_deleted']}")
    print(f"   • Cards with placeholders deleted: {stats['cards_with_placeholder']}")
    print(f"   • Good cards moved to all_cards/: {stats['good_cards_moved']}")
    print(f"   • Total cards processed: {stats['total_cards']}")
    print("\n📁 All good cards are now in: output/all_cards/")

    # List final cards
    final_cards = list(consolidated_dir.glob("*.png"))
    if final_cards:
        print(f"\n🎴 You have {len(final_cards)} finished cards:")
        for card in sorted(final_cards)[:10]:  # Show first 10
            size_kb = card.stat().st_size / 1024
            print(f"   • {card.name} ({size_kb:.0f} KB)")
        if len(final_cards) > 10:
            print(f"   ... and {len(final_cards) - 10} more")


if __name__ == "__main__":
    # Check for required library
    try:
        import numpy
        from PIL import Image
    except ImportError:
        print("Installing required libraries...")
        import subprocess

        subprocess.run(["poetry", "add", "pillow", "numpy"])
        print("Libraries installed. Please run the script again.")
        exit(1)

    cleanup_output_folder()
