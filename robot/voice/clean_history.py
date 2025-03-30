import os
import json

def clean_history():
    """
    Clears the AI conversation history by emptying the content of the conversation_history.json file.
    """
    history_file = "conversation_history.json"
    if os.path.exists(history_file):
        try:
            with open(history_file, "w", encoding="utf-8") as file:
                json.dump([], file, ensure_ascii=False, indent=4)  # Overwrites the file with an empty list
            print("Conversation history cleared successfully.")
        except Exception as e:
            print(f"Error clearing history: {e}")
    else:
        print("History file not found.")

if __name__ == "__main__":
    clean_history()
