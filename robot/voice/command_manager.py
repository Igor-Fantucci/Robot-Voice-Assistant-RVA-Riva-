import json
import os.path
import shlex
import subprocess

from termcolor import cprint
from thefuzz import fuzz
from thefuzz import process
from dotenv import load_dotenv

import config_manager
import master_mode_manager
from voice_feedback import give_execution_feedback, speak, give_exiting_feedback
from ai_functions import chat_with_mistral  # Import the function we created
from notifier import notify
from weather import get_weather

# Stores commands from the commands.json file
commands = dict()

load_dotenv()

# Built-in actions
quitCommand = "see you later"  # Say this to turn off your voice control engine
activateMasterModeCommand = "activate master control mode"  # Say this to turn on master control mode
deactivateMasterModeCommand = "deactivate master control mode"  # Say this to turn off master control mode

# Internal variables
self_activated_master_mode = False  # Used for notifying the user if master control mode was enabled implicitly

# Stores all the keys in commands dictionary to be extracted by Fuzzy Matcher
choices = []


# Initializing commands with commands specified in commands.json
def init():
    global commands, choices
    commands = get_commands_from_file()
    name = config_manager.config['name']

    commands[f'see you later {name}'] = "<built-in>"
    commands[activateMasterModeCommand] = "<built-in>"
    commands[deactivateMasterModeCommand] = "<built-in>"

    choices = list(commands.keys())
    show_commands()

def get_weather_conditions():
    api_key = os.getenv("WEATHER_API_KEY")
    from weather import get_weather
    weather_info = get_weather(api_key)
    return weather_info

# Getting JSON data from file
def get_commands_from_file():
    return json.load(open(os.path.join(os.getcwd(), "commands.json")))


from spotify_control import play_song, pause_song, next_song, previous_song


def log(text, color=None, attrs=None):
    """
    Function to display colored logs in the terminal.
    """
    if attrs is None:
        attrs = []
    if color is None:
        print(text)
    else:
        cprint(text, color, attrs=attrs)


def launch_if_any(text):
    """
    Checks if the text matches a known command. Otherwise, sends it to the AI.
    """
    
    # Check if the command is to toggle AI response style
    if text.lower() in ["toggle response style", "switch response style", "change response style"]:
        log("Toggling AI response style...", "yellow")
        response = chat_with_mistral(text)  # This will handle the toggle internally
        return
        
    # Check if the command is to search the internet
    if text.lower().startswith("search for"):
        search_term = text[len("search for"):].strip()
        print(f"'{search_term}'")  # Debug

        if search_term:
            if "search for *" in commands:
                command_template = commands["search for *"]["exec"]
                feedback_template = commands["search for *"]["feedback"]

                # Format the command with the search term
                command = command_template.format(search_term)
                feedback = feedback_template.format(search_term)

                # Split the command into parts, but keep the search term as a single argument
                command_base = command.split(maxsplit=2)  # Split only the base command (python3 /path/to/script.py)
                final_command = command_base + [search_term]  # Add the search term as a single argument

                # Execute the command
                subprocess.Popen(final_command)
                speak(feedback)
            else:
                command = ["/usr/bin/python3", "/home/fantucci/robot/voice/search_for.py", search_term]
                print(f"Executing default command: {' '.join(command)}")  # Debug
                subprocess.Popen(command)
                speak(f"Searching the internet for {search_term}")
            return

    # Check if the command is to open an application
    if text.lower().startswith("open"):
        app_name = text[len("open"):].strip()
        log(f"Trying to open application: {app_name}", "yellow")
    
        # Call the script to open the application using the virtual environment Python
        result = subprocess.run(
            ["/home/fantucci/robot/.venv/bin/python3", "/home/fantucci/robot/voice/open_app.py", app_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True  # Decode stdout/stderr as text
        )
    
        # Log the output and errors
        if result.stdout:
            log(f"Script output: {result.stdout}", "blue")
        if result.stderr:
            log(f"Script errors: {result.stderr}", "red")
    
        # Check if the command was successful
        if result.returncode != 0:
            log(f"Command 'open' failed with return code {result.returncode}.", "red")
            speak("Sorry, I couldn't open the application.")
        else:
            log(f"Application '{app_name}' opened successfully.", "green")
            speak(f"Opened {app_name}")
        return
        
    # Check if the command is for Spotify
    if text.lower().startswith("play"):
        song_name = text[len("play"):].strip()
        if song_name:
            if play_song(song_name):
                speak(f"Playing {song_name} on Spotify")
            else:
                speak(f"Could not find {song_name} on Spotify")
        return
    elif text.lower() == "stop music":
        pause_song()
        speak("Paused Spotify")
        return
    elif text.lower() == "next track":
        next_song()
        speak("Skipping to next track")
        return
    elif text.lower() == "previous track":
        previous_song()
        speak("Going back to previous track")
        return

    # Check if the command is to get weather conditions
    if text.lower() == "climate conditions":
        # Get and speak weather conditions in English
        weather_info = get_weather(language="en")
        speak(weather_info)  # Speak the weather conditions
        return
    
    # Check if the text matches any known command
    probability = process.extractOne(text, choices)
    print("probability:", probability)

    if probability and is_text_prediction_applicable(text, probability[0]):
        try:
            command = commands[probability[0]]['exec']
        except TypeError:
            command = commands[probability[0]]

        if check_for_built_in_actions(probability[0]):
            return

        if not command:
            cprint(f">>> Error: Command is empty for '{probability[0]}'", "red", attrs=["bold"])
            return

        if isinstance(commands[probability[0]], dict) and commands[probability[0]]['feedback']:
            speak(commands[probability[0]]['feedback'], commands[probability[0]]['blocking'])
        else:
            give_execution_feedback()

        cprint(f'>>> executing: {command}', "green", attrs=["bold"])
        notify(f'Executing: {command}', 250)

        try:
            args = shlex.split(command)
            if args:
                subprocess.Popen(args, start_new_session=True)
            else:
                cprint(f">>> Error: Command split resulted in an empty list for '{command}'", "red", attrs=["bold"])
        except Exception as e:
            cprint(f">>> Error executing command: {e}", "red", attrs=["bold"])
    else:
        # If it's not a known command, send it to the AI
        log("Sending to AI...", "yellow")
        response = chat_with_mistral(text)  # Use the Mistral AI function


# Performs further fuzzy match to ensure the command to be executed is correct
def is_text_prediction_applicable(text, predicted_text):
    if ' ' in predicted_text:
        # Using Sort Ratio Fuzzy Match to validate if
        # the vocal and the probable command contain same words
        ratio = fuzz.token_sort_ratio(text, predicted_text)
        return ratio > 60  # Ratio threshold must be 60 or more accurate
    return True  # No further check is performed for single-word commands


# Before diving further, we perform a check for in-built actions here
# @returns: True if an implicit action is invoked
def check_for_built_in_actions(text):
    global self_activated_master_mode
    if text.startswith(quitCommand):
        give_execution_feedback()
        if self_activated_master_mode:
            speak('Deactivating Master Control Mode of this session', wait=True)
        give_exiting_feedback()
        exit(0)
    elif hasText(text, activateMasterModeCommand):
        if config_manager.config['master-mode']:
            speak('Master Control Mode is already Activated', wait=True)
            return True
        if not master_mode_manager.canEnableMasterMode():
            speak('You need to configure master control mode before using it, refer to the project\'s readme', wait=True)
            return True
        config_manager.config['master-mode'] = True
        self_activated_master_mode = True
        cprint(f'MASTER CONTROL MODE: ON', "blue", attrs=['bold'])
        speak('Activated Master Control Mode', wait=True)
        return True
    elif hasText(text, deactivateMasterModeCommand):
        if not config_manager.config['master-mode']:
            speak('Master Control Mode is already Off', wait=True)
            return True
        config_manager.config['master-mode'] = False
        self_activated_master_mode = False
        cprint(f'MASTER CONTROL MODE: OFF', "blue", attrs=['bold'])
        speak('Deactivated Master Control Mode', wait=True)
        return True
    return False


# Finds if the @source actually encloses the @text in it
def hasText(source, text):
    if text in source:
        index = source.find(text)
        return index == 0 or not source[index - 1].isalpha()
    return False


# Lists all the available commands to the console
def show_commands():
    if config_manager.config['show-commands-on-startup']:
        print(">>> Available Commands")
        for launcher in commands:
            print(launcher, ":", commands[launcher])
        print()
