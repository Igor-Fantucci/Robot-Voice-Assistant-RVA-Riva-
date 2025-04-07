#!/home/fantucci/robot/.venv/bin/python3

import sys
import subprocess
import os
import signal
from termcolor import cprint
from thefuzz import process
from voice_feedback import speak
import config_manager

# Initialize config_manager
config_manager.init()

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

# Predefined list of applications with their process names
predefined_apps = {
    "spotify": "spotify",
    "firefox": "firefox",
    "discord": "discord",
    "code": "code",  # Visual Studio Code
    "vscode": "code",
    "visual studio code": "code",
    "settings": "gnome-control-center",
    "terminal": "gnome-terminal",
    "calculator": "gnome-calculator",
    "chrome": "chrome",
    "google chrome": "chrome",
    "brave": "brave-browser",
    "libreoffice": "soffice.bin",
    "thunderbird": "thunderbird",
}

def find_running_apps():
    """
    Finds all running applications by checking running processes.
    """
    try:
        # Get list of all running processes
        result = subprocess.run(["ps", "-eo", "comm"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            processes = result.stdout.decode("utf-8").splitlines()
            return [p.strip() for p in processes if p.strip()]
    except Exception as e:
        log(f"Error finding running apps: {e}", "red")
    return []

def find_best_match(app_name, running_apps):
    """
    Uses fuzzy matching to find the closest running application name.
    """
    # Combine predefined apps with running apps
    all_apps = list(predefined_apps.keys()) + running_apps
    result = process.extractOne(app_name, all_apps)
    return result[0] if result[1] > 70 else None  # 70 is the similarity threshold

def get_process_name(app_name):
    """
    Gets the actual process name from our predefined list or returns the input.
    """
    return predefined_apps.get(app_name.lower(), app_name)

def close_app(app_name):
    """
    Closes the specified application.
    """
    try:
        process_name = get_process_name(app_name)
        log(f"Attempting to close: {process_name}", "yellow")
        
        # Try to gracefully close the application first
        try:
            # For X11 applications, we can use wmctrl to close windows
            subprocess.run(["wmctrl", "-c", app_name], check=True)
            log(f"Sent close signal to {app_name}", "green")
            speak(f"Closed {app_name}")
            return
        except subprocess.CalledProcessError:
            pass  # Fall through to kill method
        
        # If graceful close fails, use pkill to terminate the process
        result = subprocess.run(["pkill", "-f", process_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            log(f"Successfully closed {process_name}", "green")
            speak(f"Closed {app_name}")
        else:
            # Try alternative method with killall
            result = subprocess.run(["killall", process_name], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                log(f"Successfully closed {process_name} using killall", "green")
                speak(f"Closed {app_name}")
            else:
                log(f"Failed to close {process_name}", "red")
                speak(f"Sorry, I couldn't close {app_name}")
    except Exception as e:
        log(f"Error closing {app_name}: {e}", "red")
        speak("Sorry, I encountered an error while trying to close the application.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        log("Usage: close_app.py <app_name>", "red")
        sys.exit(1)

    app_name = sys.argv[1]
    log(f"Searching for running applications matching '{app_name}'...", "yellow")

    running_apps = find_running_apps()
    matched_app = find_best_match(app_name, running_apps)

    if matched_app:
        log(f"Found a matching running application: {matched_app}", "blue")
        close_app(matched_app)
    else:
        log(f"No running app found matching '{app_name}'", "red")
        speak(f"Sorry, I couldn't find a running application matching '{app_name}'.")
