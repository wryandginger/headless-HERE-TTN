#!/usr/bin/env python3

import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

# Configurations
HOME_DIR = Path("/app")
TEMP_DIR = HOME_DIR / "temp"
DEST_DIR = HOME_DIR / "outputs/here"
TARGET_COUNT = 10
TZ = "America/Los_Angeles"
FREQ = "99.9"
PROGRAM = "0"
TIMEOUT_SECONDS = 400  # 5 minutes maximum runtime limit for both frequencies
# Tries a second frequency after:
SWITCH_AFTER_SECONDS = 200
NEW_FREQ = "97.3"

# Helper to build nrsc5 command for a given frequency
def make_command(freq):
    # nrsc5 output is .png for easy cleanup. This is actually a wav file you can play to debug; AAS files dump to ~/temp
    return ["nrsc5", freq, PROGRAM, "-o", os.path.join(TEMP_DIR, "1.png"), "--dump-aas-files", str(TEMP_DIR)]


# The specific tiles we require (3x3 traffic map + one weather image)
EXPECTED_TRAFFIC_COORDS = [(r, c) for r in range(3) for c in range(3)]
EXPECTED_WEATHER_COORD = (0, 0)  # expecting WeatherImage_0_0_*.png


def get_captured_files():
    """Finds all matching PNG files dumped by nrsc5 in the temp directory."""
    pattern = re.compile(
        r"^\d+_(trafficMap_[0-2]_[0-2]|WeatherImage_[0-2]_[0-2])_[a-zA-Z0-9]+\.png$"
    )
    if not TEMP_DIR.exists():
        return []
    all_pngs = TEMP_DIR.glob("*.png")
    return [f for f in all_pngs if pattern.match(f.name)]


def find_required_files():
    """
    Look specifically for the 9 traffic tiles and the single WeatherImage_0_0 file.
    Returns a dict with keys:
      - ('traffic', r, c) -> Path or None
      - ('weather', 0, 0) -> Path or None
    """
    required = {}
    # Traffic tiles
    for r, c in EXPECTED_TRAFFIC_COORDS:
        pattern = f"*trafficMap_{r}_{c}_*.png"
        matches = list(TEMP_DIR.glob(pattern))
        required[("traffic", r, c)] = matches[0] if matches else None

    # WeatherImage_0_0
    w_pattern = f"*WeatherImage_{EXPECTED_WEATHER_COORD[0]}_{EXPECTED_WEATHER_COORD[1]}_*.png"
    w_matches = list(TEMP_DIR.glob(w_pattern))
    required[("weather", EXPECTED_WEATHER_COORD[0], EXPECTED_WEATHER_COORD[1])] = w_matches[0] if w_matches else None

    return required


def print_required_progress_inline(required_map, prev_len=0, start_time=None):
    tokens = []
    for r in range(3):
        for c in range(3):
            key = ("traffic", r, c)
            entry = required_map.get(key)
            status = "OK" if entry else "--"
            tokens.append(f"T{r}{c}:{status}")

    wkey = ("weather", EXPECTED_WEATHER_COORD[0], EXPECTED_WEATHER_COORD[1])
    wentry = required_map.get(wkey)
    wstatus = "OK" if wentry else "--"
    tokens.append(f"W{EXPECTED_WEATHER_COORD[0]}{EXPECTED_WEATHER_COORD[1]}:{wstatus}")

    found_count = sum(1 for v in required_map.values() if v)
    elapsed = ""
    if start_time:
        elapsed = f" elapsed={int(time.time() - start_time)}s"
    s = f"[{found_count}/{len(required_map)}] " + " ".join(tokens) + elapsed
    pad = ""
    if prev_len > len(s):
        pad = " " * (prev_len - len(s))

    sys.stdout.write("\r" + s + pad)
    sys.stdout.flush()
    return len(s)


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

    print("\nWarning: Could not find TrueType font. Falling back to default.")
    return ImageFont.load_default()


def process_images_from_required(required_map):
    """Stitches traffic map tiles, overlays weather data (from the required_map), and moves results."""
    print("\nProcessing captured images...")  # newline so we don't overwrite the progress line

    # Build traffic tile map from the required_map (should all exist)
    traffic_tiles = {}
    for r, c in EXPECTED_TRAFFIC_COORDS:
        key = ("traffic", r, c)
        path = required_map.get(key)
        if not path or not path.exists():
            raise FileNotFoundError(f"Required traffic tile missing: trafficMap_{r}_{c}")
        traffic_tiles[(r, c)] = path

    wkey = ("weather", EXPECTED_WEATHER_COORD[0], EXPECTED_WEATHER_COORD[1])
    weather_file = required_map.get(wkey)
    if not weather_file or not weather_file.exists():
        print("Warning: WeatherImage overlay file missing at processing time. Proceeding without overlay.")
        weather_file = None

    # 1. Assemble the 3x3 Traffic Map
    canvas = Image.new("RGBA", (600, 600))
    for (row, col), filepath in traffic_tiles.items():
        with Image.open(filepath) as tile:
            tile = tile.resize((200, 200))
            canvas.paste(tile, (col * 200, row * 200))

    # 2. Add Timestamp to Traffic Map 
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
    print("\nCleaning up image files from temp directory...")
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

    current_freq = FREQ
    print(f"Starting nrsc5 command at {current_freq}...")
    process = subprocess.Popen(
        make_command(current_freq), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    start_time = time.time()
    prev_len = 0
    crashed = False
    switched = False

    try:
        while True:
            # Check for the specific required files
            required_map = find_required_files()

            # Update progress inline
            prev_len = print_required_progress_inline(required_map, prev_len=prev_len, start_time=start_time)

            found_count = sum(1 for v in required_map.values() if v)
            if found_count >= TARGET_COUNT:
                # finalize the progress line and break
                sys.stdout.write("\n")
                sys.stdout.flush()
                print(f"Target of {TARGET_COUNT} required files reached.")
                break

            elapsed = time.time() - start_time

            # If enough time has passed and we haven't switched yet, switch frequency
            if not switched and elapsed >= SWITCH_AFTER_SECONDS:
                print("\nSwitching frequency to", NEW_FREQ, f"after {SWITCH_AFTER_SECONDS} seconds...")
                # terminate current process
                try:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=5)
                except Exception:
                    # best-effort: ignore if already dead
                    pass

                # start new nrsc5 at NEW_FREQ
                current_freq = NEW_FREQ
                print(f"Starting nrsc5 command at {current_freq}...")
                process = subprocess.Popen(
                    make_command(current_freq), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                switched = True

            # Check if nrsc5 process has exited
            poll = process.poll()
            if poll is not None:
                # Process has finished (either normally or crashed)
                if poll != 0:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    print(f"nrsc5 terminated unexpectedly with exit code {poll}. Aborting.")
                    crashed = True
                    break
                else:
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    print(f"nrsc5 exited (code {poll}). No more files will be produced.")
                    break

            # Check if execution time has exceeded the configured timeout
            if elapsed >= TIMEOUT_SECONDS:
                sys.stdout.write("\n")
                sys.stdout.flush()
                print(f"Timeout limit of {TIMEOUT_SECONDS} seconds reached. Ending capture loop.")
                break

            time.sleep(2)

    finally:
        # Terminate nrsc5 if it's still running
        try:
            if process.poll() is None:
                print("Terminating nrsc5 process...")
                process.terminate()
                process.wait(timeout=5)
        except Exception:
            # If it's already dead or cannot be terminated, ignore and continue cleanup path
            pass

    # If nrsc5 crashed, exit immediately (after cleanup)
    if crashed:
        cleanup_temp()
        sys.exit(1)

    # Final check: ensure we have the required files before processing
    required_map = find_required_files()
    found_count = sum(1 for v in required_map.values() if v)
    if found_count >= TARGET_COUNT:
        try:
            process_images_from_required(required_map)
        except Exception as e:
            print(f"Error while processing images: {e}")
    else:
        print(f"Aborting image generation: Only found {found_count}/{TARGET_COUNT} required files.")

    cleanup_temp()


if __name__ == "__main__":
    main()
