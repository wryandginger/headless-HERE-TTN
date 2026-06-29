#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

# Configurations
HOME_DIR = Path.home()
TEMP_DIR = HOME_DIR / "temp"
DEST_DIR = HOME_DIR / "outputs/here"
TARGET_COUNT = 10
TZ = "America/Los_Angeles"
FREQ = "97.3"
PROGRAM = "0"
TIMEOUT_SECONDS = 300  # 5 minutes maximum runtime limit

# nrsc5 output name must end in .png; AAS files dump to ~/temp
COMMAND = ["nrsc5", FREQ, PROGRAM, "-o", os.path.join(TEMP_DIR, "1.png"), "--dump-aas-files", str(TEMP_DIR)]


def get_captured_files():
    """Finds all matching PNG files dumped by nrsc5 in the temp directory."""
    pattern = re.compile(
        r"^\d+_(trafficMap_[0-2]_[0-2]|WeatherImage_[0-2]_[0-2])_[a-zA-Z0-9]+\.png$"
    )
    if not TEMP_DIR.exists():
        return []
    all_pngs = TEMP_DIR.glob("*.png")
    return [f for f in all_pngs if pattern.match(f.name)]


def get_large_font(size):
    """Attempts to load a standard TrueType font to support custom sizing."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "Arial.ttf",
    ]

    for path in font_paths:
        try:
            return ImageFont.truetype(path, size)
        except IOError:
            continue

    print("Warning: Could not find TrueType font. Falling back to default.")
    return ImageFont.load_default()


def process_images(files):
    """Stitches traffic map tiles, overlays weather data, and moves results."""
    print("Processing captured images...")

    traffic_tiles = {}
    weather_file = None

    for f in files:
        if "trafficMap" in f.name:
            match = re.search(r"trafficMap_([0-2])_([0-2])", f.name)
            if match:
                row, col = map(int, match.groups())
                traffic_tiles[(row, col)] = f
        elif "WeatherImage" in f.name:
            weather_file = f

    # 1. Assemble the 3x3 Traffic Map
    canvas = Image.new("RGBA", (600, 600))
    for (row, col), filepath in traffic_tiles.items():
        with Image.open(filepath) as tile:
            tile = tile.resize((200, 200))
            canvas.paste(tile, (col * 200, row * 200))

    # 2. Add Timestamp to Traffic Map using exact requested format
    # Enforce configured time zone for timestamping
    draw = ImageDraw.Draw(canvas)
    local_time = datetime.now(ZoneInfo(TZ))
    timestamp_str = local_time.strftime("%m/%d %H:%M")
    
    font = get_large_font(size=24)
    
    # Calculate box bounds dynamically or use padding adjustments
    text_w = 170
    text_h = 30
    text_x = 600 - text_w - 10
    text_y = 600 - text_h - 10
    
    # Draw background box and text overlay
    draw.rectangle([text_x - 5, text_y - 2, 590, 590], fill="black")
    draw.text((text_x, text_y), timestamp_str, fill="white", font=font)

    # Save initial map to temp directory
    traffic_path = TEMP_DIR / "trafficmapHERE.png"
    canvas.save(traffic_path)
    print(f"Created base traffic map: {traffic_path}")

    # 3. Create Weather Overlay Image
    if weather_file and weather_file.exists():
        weather_canvas = canvas.copy()
        with Image.open(weather_file) as weather_img:
            weather_img = weather_img.resize((600, 600)).convert("RGBA")
            weather_canvas.alpha_composite(weather_img)

        weather_path = TEMP_DIR / "weatherimgHERE.png"
        weather_canvas.save(weather_path)
        print(f"Created weather overlay map: {weather_path}")
    else:
        print("Warning: WeatherImage overlay file missing. Skipping overlay.")
        weather_path = None

    # 4. Move outputs to destination folder using shutil.move (cross-drive safe)
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    if traffic_path.exists():
        shutil.move(str(traffic_path), str(DEST_DIR / "trafficmapHERE.png"))
    if weather_path and weather_path.exists():
        shutil.move(str(weather_path), str(DEST_DIR / "weatherimgHERE.png"))

    print(f"Successfully moved final files to {DEST_DIR}")


def cleanup_temp():
    """Deletes all png and jpg files from the temp directory."""
    print("Cleaning up image files from temp directory...")
    if not TEMP_DIR.exists():
        return
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        for filepath in TEMP_DIR.glob(ext):
            try:
                filepath.unlink()
            except Exception as e:
                print(f"Could not delete {filepath.name}: {e}")
    print("Cleanup complete.")


def main():
    # Ensure temp directory exists before starting nrsc5
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Starting nrsc5 command...")
    process = subprocess.Popen(
        COMMAND, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    start_time = time.time()

    try:
        while True:
            captured_files = get_captured_files()
            count = len(captured_files)
            print(f"Downloaded {count}/{TARGET_COUNT} files...", end="\r")

            if count >= TARGET_COUNT:
                print(f"\nTarget of {TARGET_COUNT} files reached.")
                break

            # Check if execution time has exceeded the configured 5-minute timeout
            if (time.time() - start_time) >= TIMEOUT_SECONDS:
                print(f"\nTimeout limit of {TIMEOUT_SECONDS} seconds reached. Ending capture loop.")
                break

            time.sleep(2)

    finally:
        print("Terminating nrsc5 process...")
        process.terminate()
        process.wait()

    captured_files = get_captured_files()
    if len(captured_files) >= TARGET_COUNT:
        process_images(captured_files)
    else:
        print(f"Aborting image generation: Only found {len(captured_files)}/{TARGET_COUNT} files.")

    cleanup_temp()


if __name__ == "__main__":
    main()
