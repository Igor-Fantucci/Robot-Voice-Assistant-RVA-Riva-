#!/home/fantucci/robot/.venv/bin/python3

import sys
import subprocess
import os
import whisper
from termcolor import cprint
from thefuzz import process
from voice_feedback import speak  # Import the speak function
import config_manager

# Initialize config_manager
config_manager.init()

# Load the Whisper model (do this once at the beginning of the script)
audio_model = whisper.load_model("base")

# Log function
def log(message, color="white"):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{message}{colors['reset']}")

# Predefined list of applications
predefined_apps = {
    "spotify": "spotify",
    "firefox": "firefox",
    "discord": "discord",
    "code": "code",  # Visual Studio Code
    "vscode": "code",
    "visual studio code": "code",
    "settings": "gnome-control-center",  # Example for GNOME settings
    "terminal": "gnome-terminal",  # Example for GNOME terminal
    "calculator": "gnome-calculator",  # Example for GNOME calculator
}

# Directories where applications are usually installed
search_dirs = ["/usr/bin", "/usr/local/bin", "/snap/bin", os.path.expanduser("~/.local/bin")]

def find_apps():
    """
    Searches for executable applications in the specified directories.
    """
    apps = []
    for directory in search_dirs:
        try:
            # Use the 'find' command to search for executable files
            result = subprocess.run(["find", directory, "-type", "f", "-executable"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                apps.extend(result.stdout.decode("utf-8").splitlines())
        except Exception as e:
            log(f"Error searching in {directory}: {e}", "red")
    return apps

def find_best_match(app_name, apps):
    """
    Uses fuzzy matching to find the closest application name.
    """
    # Combine predefined apps with dynamically found apps
    all_apps = list(predefined_apps.keys()) + [app.split('/')[-1] for app in apps]
    result = process.extractOne(app_name, all_apps)
    return result[0] if result[1] > 70 else None  # 70 is the similarity threshold

def open_app(app_name):
    """
    Opens the specified application.
    """
    try:
        # Check if the app is in the predefined list
        if app_name in predefined_apps:
            app_command = predefined_apps[app_name]
            log(f"Trying to execute: {app_command}", "yellow")
            # Use subprocess.Popen without waiting for the process to complete
            subprocess.Popen([app_command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log(f"Opening {app_name}", "green")
        else:
            # Search for the app using the 'which' command
            result = subprocess.run(["which", app_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                app_path = result.stdout.decode("utf-8").strip()
                log(f"Found executable: {app_path}", "blue")
                # Use subprocess.Popen without waiting for the process to complete
                subprocess.Popen([app_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                log(f"Opened {app_path}", "green")
            else:
                # Try to find the app in snap or flatpak
                snap_result = subprocess.run(["snap", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if app_name in snap_result.stdout.decode("utf-8"):
                    subprocess.Popen(["snap", "run", app_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    log(f"Opened {app_name} via snap", "green")
                else:
                    flatpak_result = subprocess.run(["flatpak", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if app_name in flatpak_result.stdout.decode("utf-8"):
                        subprocess.Popen(["flatpak", "run", app_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        log(f"Opened {app_name} via flatpak", "green")
                    else:
                        log(f"Application '{app_name}' not found.", "red")
                        speak(f"Sorry, I couldn't find the application '{app_name}'.")
    except Exception as e:
        log(f"Failed to open {app_name}: {e}", "red")
        speak("Sorry, I couldn't open the application.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("Usage: open_app.py <app_name>", "red")
        sys.exit(1)

    app_name = sys.argv[1]
    log(f"Searching for applications matching '{app_name}'...", "yellow")

    apps = find_apps()
    matched_app = find_best_match(app_name, apps)

    if matched_app:
        log(f"Found a matching application: {matched_app}", "blue")
        open_app(matched_app)
    else:
        log(f"No app found matching '{app_name}'", "red")
        speak(f"Sorry, I couldn't find the application '{app_name}'.")
