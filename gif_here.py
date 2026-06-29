import os
import glob
import shutil
import sys
import subprocess
from datetime import datetime
from PIL import Image

# ==================== CONFIGURATION ====================
# Samba Network Settings
SMB_SERVER = "1XX.1XX.XXX.XXX"
SMB_SHARE = "config"                 # The root share name
SMB_REMOTE_PATH = "www/here"          # Folder path inside the share
SMB_USER = "USER"
SMB_PASS = "PASS"

# Local Directory Settings
BASE_DIR = os.path.expanduser("~/outputs")
SOURCE_DIR = os.path.join(BASE_DIR, "here")
GIF_DIR = os.path.join(SOURCE_DIR, "gif")

# File Tracking
REQUIRED_FILES = ["trafficmapHERE.png", "weatherimgHERE.png"]
WEATHER_FILE = "weatherimgHERE.png"
TRAFFIC_FILE = "trafficmapHERE.png"
FINAL_GIF_NAME = "here.gif"           
# =======================================================

def check_local_files():
    """Checks if required source files exist and exits gracefully if they do not."""
    print("Checking for source images...")
    os.makedirs(GIF_DIR, exist_ok=True)
    
    missing_files = []
    for file_name in REQUIRED_FILES:
        if not os.path.exists(os.path.join(SOURCE_DIR, file_name)):
            missing_files.append(file_name)
            
    if missing_files:
        print(f"Error: Missing required files: {', '.join(missing_files)}")
        print("Exiting gracefully.")
        sys.exit(0)
        
    print("All required source files found.")

def archive_weather_image():
    """Copies weather image to the gif archive folder with HHMM name."""
    current_time = datetime.now().strftime("%H%M")
    new_name = f"{current_time}.png"
    shutil.copy2(os.path.join(SOURCE_DIR, WEATHER_FILE), os.path.join(GIF_DIR, new_name))
    print(f"Archived weather image as {new_name}")

def purge_old_frames():
    """Keeps only the 15 most recent PNG files in the gif directory."""
    png_files = glob.glob(os.path.join(GIF_DIR, "*.png"))
    png_files.sort(key=os.path.getmtime)
    
    if len(png_files) > 15:
        to_delete = png_files[:-15]
        for file_path in to_delete:
            try:
                os.remove(file_path)
            except OSError as e:
                print(f"Error deleting old file {file_path}: {e}")
        print(f"Purged {len(to_delete)} old frame(s). Kept the 15 newest.")

def generate_gif():
    """Compiles the remaining PNG frames into a single animated GIF."""
    png_files = glob.glob(os.path.join(GIF_DIR, "*.png"))
    png_files.sort()
    
    if not png_files:
        print("No frames found to generate GIF.")
        return False

    frames = [Image.open(f) for f in png_files]
    output_gif_path = os.path.join(SOURCE_DIR, FINAL_GIF_NAME)
    
    try:
        frames[0].save(
            output_gif_path,
            save_all=True,
            append_images=frames[1:],
            duration=500,
            loop=0
        )
        print(f"Generated animated GIF at {output_gif_path}")
        return True
    except Exception as e:
        print(f"Failed to generate GIF: {e}")
        return False
    finally:
        for frame in frames:
            frame.close()

def upload_to_samba():
    """Uploads the files using the native Linux smbclient utility."""
    print("Connecting to Samba server via system smbclient...")
    
    local_files = [
        os.path.join(SOURCE_DIR, TRAFFIC_FILE),
        os.path.join(SOURCE_DIR, WEATHER_FILE),
        os.path.join(SOURCE_DIR, FINAL_GIF_NAME)
    ]
    
    service = f"//{SMB_SERVER}/{SMB_SHARE}"
    remote_dir = SMB_REMOTE_PATH.replace("\\", "/")
    
    smb_commands = ""
    for local_path in local_files:
        filename = os.path.basename(local_path)
        dirname = os.path.dirname(local_path)
        smb_commands += f"lcd {dirname}; put {filename}; "
    
    cmd = [
        "smbclient", service,
        "-U", f"{SMB_USER}%{SMB_PASS}",
        "-D", remote_dir,
        "-c", smb_commands
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Successfully uploaded all 3 files to Samba!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Samba upload failed! Process exited with code {e.returncode}")
        return False

def cleanup_local_files():
    """Deletes the original source images and the built GIF from the directory."""
    print("Cleaning up local directory...")
    files_to_delete = [
        os.path.join(SOURCE_DIR, TRAFFIC_FILE),
        os.path.join(SOURCE_DIR, WEATHER_FILE),
        os.path.join(SOURCE_DIR, FINAL_GIF_NAME)
    ]
    
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Removed temporary local file: {os.path.basename(file_path)}")
            except OSError as e:
                print(f"Could not remove {os.path.basename(file_path)}: {e}")

if __name__ == "__main__":
    check_local_files()
    archive_weather_image()
    purge_old_frames()
    
    if generate_gif():
        # Only clean up if the upload successfully finishes
        if upload_to_samba():
            cleanup_local_files()
            
    print("Process complete!")
