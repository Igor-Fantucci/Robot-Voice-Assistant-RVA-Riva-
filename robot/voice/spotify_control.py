import spotipy
from spotipy.oauth2 import SpotifyOAuth
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Your Spotify Developer credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"

# Spotify configuration
scope = "user-modify-playback-state,user-read-playback-state"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope=scope))

def check_active_device():
    """Checks if there is an active device and returns the device ID."""
    devices = sp.devices()
    if not devices['devices']:
        print("No active device found. Open Spotify on a device.")
        return None
    return devices['devices'][0]['id']

def play_song(song_name):
    """Plays a specific song."""
    device_id = check_active_device()
    if not device_id:
        return False

    results = sp.search(q=song_name, type='track', limit=1)
    if results['tracks']['items']:
        track_uri = results['tracks']['items'][0]['uri']
        try:
            sp.start_playback(device_id=device_id, uris=[track_uri])
            print(f"Playing: {song_name}")
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error playing song: {e}")
            return False
    return False

def pause_song():
    """Pauses playback."""
    device_id = check_active_device()
    if device_id:
        try:
            sp.pause_playback(device_id=device_id)
            print("Playback paused.")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error pausing playback: {e}")

def resume_song():
    """Resumes playback."""
    device_id = check_active_device()
    if device_id:
        try:
            sp.start_playback(device_id=device_id)
            print("Playback resumed.")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error resuming playback: {e}")

def next_song():
    """Skips to the next song."""
    device_id = check_active_device()
    if device_id:
        try:
            sp.next_track(device_id=device_id)
            print("Next song.")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error skipping to the next song: {e}")

def previous_song():
    """Goes back to the previous song."""
    device_id = check_active_device()
    if device_id:
        try:
            sp.previous_track(device_id=device_id)
            print("Previous song.")
        except spotipy.exceptions.SpotifyException as e:
            print(f"Error going back to the previous song: {e}")

# Logic to execute commands from command-line arguments
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "play" and len(sys.argv) > 2:
            song_name = " ".join(sys.argv[2:])
            play_song(song_name)
        elif command == "pause":
            pause_song()
        elif command == "resume":
            resume_song()
        elif command == "next":
            next_song()
        elif command == "previous":
            previous_song()
        else:
            print("Invalid command.")
    else:
        print("No command provided.")
