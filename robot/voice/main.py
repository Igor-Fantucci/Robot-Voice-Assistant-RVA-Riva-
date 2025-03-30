import os
import sys
import time
import wave
from array import array
from os.path import exists

import click
import pyaudio
import whisper
import torch
from termcolor import cprint

import basic_mode_manager
import command_manager
import config_manager
import voice_feedback
from master_mode_manager import isMasterSpeaking
from utils import trim

try:
    if not exists('misc'):
        os.mkdir('misc')
except Exception as e:
    print('unable to create training directory')
    print(e)
    exit(1)

# initializing PyAudio ...
pyAudio = pyaudio.PyAudio()

def log(text, color=None, attrs=None):
    if attrs is None:
        attrs = []
    if color is None:
        print(text)
    elif config_manager.config['logs']:
        cprint(text, color, attrs=attrs)


def detect_silence(audio_data, threshold, silence_duration, rate, chunk):
    """
    Detects silence in the audio.
    :param audio_data: Audio data (array of amplitudes).
    :param threshold: Amplitude threshold to consider silence.
    :param silence_duration: Minimum duration of silence (in seconds).
    :param rate: Audio sample rate.
    :param chunk: Audio chunk size.
    :return: True if silence is detected, False otherwise.
    """
    silent_chunks = 0
    required_silent_chunks = int(silence_duration * rate / chunk)

    for amplitude in audio_data:
        if abs(amplitude) < threshold:
            silent_chunks += 1
            if silent_chunks >= required_silent_chunks:
                return True
        else:
            silent_chunks = 0

    return False


def record_until_silence(stream, chunk, format, channels, rate, threshold, silence_duration, is_hotword=False):
    """
    Records audio until silence is detected and at least 3 seconds of audio are recorded.
    :return: List of audio frames.
    """
    frames = []
    silent_chunks = 0
    required_silent_chunks = int(silence_duration * rate / chunk)
    start_time = time.time()  # Starts the timer

    log("Waiting command..." if not is_hotword else "Waiting hot word...", "blue" if not is_hotword else "yellow", attrs=["bold"])

    while True:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        audio_data = array('h', data)
        audio_data = trim(audio_data)

        if len(audio_data) == 0:
            continue

        # Checks if the audio is below the silence threshold
        if max(audio_data) < threshold:
            silent_chunks += 1
        else:
            silent_chunks = 0

        # If it's a hot-word, sends the audio every x seconds
        if is_hotword and (time.time() - start_time) >= 1.2:
            break

        # Checks if silence is detected and if at least 3 seconds have passed
        if not is_hotword and silent_chunks >= required_silent_chunks and (time.time() - start_time) >= 3.0:
            break

    return frames


@click.command()
@click.option("--model", default="base", help="Model to use",
              type=click.Choice(["tiny", "base", "small", "medium", "large"]))
@click.option("--ui", default="false", help="Launch in UI Mode [true/false]",
              type=click.Choice(["true", "false"]))
def main(model='base', ui='false'):
    """
    Main function of the program.
    """
    if ui == 'true':
        sys.stdout = sys.stderr

    # Initializes configuration management
    config_manager.init()

    # Initial greetings
    voice_feedback.init()
#   voice_feedback.greet() # activate it if you want a greeting

    model = model + ".en"
    audio_model = whisper.load_model(model)
    
    if torch.cuda.is_available():
        audio_model = audio_model.to('cuda')
        log("Using GPU for processing.", "green", attrs=["bold"])
    else:
        log("GPU not available. Using CPU.", "yellow", attrs=["bold"])

    # Audio settings
    CHUNK = config_manager.config['chunk-size']
    FORMAT = pyaudio.paInt16
    CHANNELS = config_manager.config['channels']
    RATE = config_manager.config['rate']
    SPEECH_THRESHOLD = config_manager.config['speech-threshold']
    SILENCE_THRESHOLD = 3000  # Adjust as needed
    SILENCE_DURATION = 0.8  # Minimum duration of silence to stop recording (in seconds)

    # Opens the audio stream
    stream = pyAudio.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)

    log("🐧 Loading command file...", "blue")

    # Initializes command management
    command_manager.init()

    # Master mode
    if config_manager.config['master-mode']:
        enabled = os.path.exists('training-data/master-mode')
        if enabled:
            log(f'MASTER MODE: ENABLED', "blue", attrs=['bold'])
            voice_feedback.speak('Master mode enabled, waiting for command...', wait=True)
        else:
            config_manager.config['master-mode'] = False
            voice_feedback.speak('Configure master mode before using it!', wait=True)
            log(f'MASTER MODE: DISABLED', "red", attrs=['bold'])

    # Basic mode with hot word
    if config_manager.config['use-hot-word-in-basic-mode']:
        while True:
            frames = record_until_silence(stream, CHUNK, FORMAT, CHANNELS, RATE, SPEECH_THRESHOLD, SILENCE_DURATION, is_hotword=True)

            # Saves the recorded audio
            wf = wave.open('training-data/hot-word-data.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            # Transcribes the audio
            result = audio_model.transcribe('training-data/hot-word-data.wav', fp16=False, language='english')
            text = result["text"].lower().strip()
            text = "".join([ch for ch in text if ch.isalpha() or ch.isdigit() or ch == ' ']).lower()

            if basic_mode_manager.compare(text):
                log("Hot word detected...", "magenta", attrs=["bold"])
                voice_feedback.speak('Yes Master ...', wait=True)
                frames = record_until_silence(stream, CHUNK, FORMAT, CHANNELS, RATE, SPEECH_THRESHOLD, SILENCE_DURATION)

                # Saves the command audio
                wf = wave.open('misc/last-mic-fetch.wav', 'wb')
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
                wf.close()

                # Transcribes and processes the command
                result = audio_model.transcribe('misc/last-mic-fetch.wav', fp16=False, language='english')
                text = result["text"].lower().strip()
                analyze_text(text)
            else:
                log('Hot word not detected.', "red", attrs=['bold'])
                time.sleep(0.5)
    else:
        log(f'🚀 Voice control ready...', "blue")
        while True:
            frames = record_until_silence(stream, CHUNK, FORMAT, CHANNELS, RATE, SPEECH_THRESHOLD, SILENCE_DURATION)

            # Saves the recorded audio
            wf = wave.open('misc/last-mic-fetch.wav', 'wb')
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
            wf.setframerate(RATE)
            wf.writeframes(b''.join(frames))
            wf.close()

            # Transcribes and processes the command
            result = audio_model.transcribe('misc/last-mic-fetch.wav', fp16=False, language='english')
            text = result["text"].lower().strip()
            analyze_text(text)


def analyze_text(text):
    """
    Analyzes the transcribed text and executes corresponding commands.
    """
    if text == '':
        return

    log(f'You: {text}', "blue", attrs=["bold"])

    if text[-1] in " .!?":
        text = text[:-1]

    command_manager.launch_if_any(text)


if __name__ == "__main__":
    main()
