import requests
import json
import os
from gtts import gTTS
import pygame
import time
from difflib import SequenceMatcher
from fuzzywuzzy import fuzz

from dotenv import load_dotenv

load_dotenv()

# Mistral AI API settings
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
HISTORY_FILE = "conversation_history.json"
CONFIG_FILE = "ai_config.json"

# Default AI settings
default_ai_config = {
    "response_style": "short",  # Can be "short" or "detailed"
}

# Function to load AI configuration
def load_ai_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    return default_ai_config

# Function to save AI configuration
def save_ai_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)

# Function to get appropriate system message based on response style
def get_system_message(style):
    if style == "short":
        return "You are a helpful assistant that responds shortly and concisely, using only a few sentences."
    else:  # detailed
        return "You are a helpful assistant that provides detailed and comprehensive responses."

# Function to load conversation history from a file
def load_conversation_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    # Initialize with different system messages based on the current response style
    ai_config = load_ai_config()
    system_message = get_system_message(ai_config["response_style"])
    return [{"role": "system", "content": system_message}]

# Function to save conversation history to a file
def save_conversation_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as file:
        json.dump(history, file, ensure_ascii=False, indent=4)

# Function to toggle response style
def toggle_response_style():
    ai_config = load_ai_config()
    current_style = ai_config["response_style"]
    new_style = "detailed" if current_style == "short" else "short"
    ai_config["response_style"] = new_style
    save_ai_config(ai_config)
    
    # Update the system message in the conversation history
    history = load_conversation_history()
    if history and history[0]["role"] == "system":
        history[0]["content"] = get_system_message(new_style)
        save_conversation_history(history)
    
    return new_style

# Function to check if text matches a command using fuzzy matching
def is_fuzzy_command_match(text, commands, threshold=80):
    """
    Checks if the provided text matches any of the commands
    using fuzzy matching with a similarity threshold.
    
    Args:
        text: The text to check
        commands: List of commands to compare against
        threshold: Minimum similarity percentage (0-100)
        
    Returns:
        Boolean: True if it matches any command above the threshold
    """
    text_lower = text.lower()
    
    for command in commands:
        # Use fuzzywuzzy's token sort ratio algorithm for better matching
        similarity = fuzz.token_sort_ratio(text_lower, command.lower())
        if similarity >= threshold:
            return True
            
    return False

# Import the speak function from voice_feedback
from voice_feedback import speak

def chat_with_mistral(prompt):
    """
    Sends a message to Mistral AI and displays chunks as they arrive.
    In short mode: speaks only the first complete sentence.
    In detailed mode: speaks the entire response.
    Returns the full response string.
    """
    # Load the conversation history at the beginning of each call
    conversation_history = load_conversation_history()
    
    # List of commands to toggle response style
    toggle_commands = ["toggle response style", "switch response style", "change response style"]
    
    # Check if this is a command to toggle response style using fuzzy matching
    if is_fuzzy_command_match(prompt, toggle_commands, threshold=80):
        new_style = toggle_response_style()
        response_msg = f"Response style switched to {new_style} mode."
        speak(response_msg)
        print(f"Assistant: {response_msg}")
        return response_msg
    
    # Add the user's message to the history
    conversation_history.append({"role": "user", "content": prompt})
    
    # Load current AI config to determine response style
    current_config = load_ai_config()
    response_style = current_config["response_style"]
    
    # Request headers
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    
    # Adjust max_tokens based on response style
    max_tokens = 35 if response_style == "short" else 200
    
    # Request payload
    payload = {
        "model": "mistral-medium",
        "messages": conversation_history,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "top_p": 0.9,
        "stream": True
    }
    
    # Send the request to the API
    response = requests.post(
        MISTRAL_API_URL,
        headers=headers,
        json=payload,
        stream=True
    )
    
    if response.status_code == 200:
        full_response = ""
        
        # For short mode: track first sentence only
        current_sentence = ""
        first_sentence_spoken = False
        
        print("Assistant: ", end="", flush=True)
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    
                    if data == "[DONE]":
                        continue
                    
                    try:
                        json_data = json.loads(data)
                        content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        
                        if content:
                            # Print the content incrementally
                            print(content, end="", flush=True)
                            
                            # Add to full response
                            full_response += content
                            
                            # Different behavior based on response style
                            if response_style == "short":
                                # In short mode, only speak the first sentence
                                if not first_sentence_spoken:
                                    current_sentence += content
                                    
                                    # Check if we have a complete sentence ending with a period
                                    if current_sentence.strip().endswith("."):
                                        speak(current_sentence.strip())
                                        first_sentence_spoken = True
                            
                    except json.JSONDecodeError:
                        continue
        
        print()  # New line after response is complete
        
        if response_style == "short":
            # Short mode: Handle any remaining text if first sentence not spoken
            if current_sentence.strip() and not first_sentence_spoken:
                speak(current_sentence.strip())
        else:
            # Detailed mode: Speak the entire response
            speak(full_response.strip())
        
        # Add the AI's complete response to the history
        conversation_history.append({"role": "assistant", "content": full_response})
        save_conversation_history(conversation_history)
        
        return full_response
    else:
        error_msg = f"Error querying the API: {response.status_code} - {response.text}"
        print(error_msg)
        speak("Sorry, I encountered an error when trying to get a response.")
        return error_msg

if __name__ == "__main__":
    print("Welcome to the Mistral AI chat! Type 'exit' to quit.")
    print(f"Current response style: {load_ai_config()['response_style']}")
    print("You can say 'toggle response style' to switch between short and detailed responses.")
    
    try:
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                print("Chat ended.")
                break
            
            # This directly handles both streaming and TTS
            response = chat_with_mistral(user_input)
    
    finally:
        pygame.mixer.quit()
