import requests
import os
from voice_feedback import speak  # Import the speak function
from dotenv import load_dotenv

load_dotenv()

# Your OpenWeatherMap API Key
API_KEY = os.getenv("WEATHER_API_KEY")

def get_weather(city=None, language="en"):
    """
    Fetches weather conditions for the current location or a specific city and speaks them.
    """
    if not city:
        # Try to get the current location based on IP
        try:
            location_response = requests.get('http://ipinfo.io')
            location_data = location_response.json()
            city = location_data['city']
        except Exception as e:
            error_message = "Unable to determine your location."
            speak(error_message)
            return error_message  # Return the error message

    # OpenWeatherMap API URL (free version)
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang={language}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # Check if the request was successful
        if data["cod"] != 200:
            error_message = "Sorry, I couldn't retrieve the weather information."
            speak(error_message)
            return error_message  # Return the error message
        
        # Extract relevant data
        weather_description = data["weather"][0]["description"]
        temperature = data["main"]["temp"]
        humidity = data["main"]["humidity"]
        
        # Prepare the weather report
        weather_report = f"The weather in {city} is {weather_description}. The temperature is {temperature}°C with a humidity of {humidity}%."
        
        # Speak the weather conditions
        speak(weather_report)
        return weather_report  # Return the weather report
    
    except Exception as e:
        error_message = "Sorry, I couldn't retrieve the weather information."
        speak(error_message)
        return error_message  # Return the error message
