"""Text-to-Speech service using Groq Playai TTS."""
import os
import requests
from typing import Generator

# Import config first to ensure .env is loaded
import backend.config  # noqa: F401

# Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GROQ_TTS_MODEL = "playai-tts"

# Voice configurations for male/female
# Basic (Groq PlayAI)
GROQ_VOICES = {
    "male": "Briggs-PlayAI",
    "female": "Celeste-PlayAI",
}

# Premium (ElevenLabs) 
# Using some standard ElevenLabs voice IDs (replace with your preferred ones)
ELEVENLABS_VOICES = {
    "male": "JBFqnCBsd6RMkjVDRZzb",    # "George"
    "female": "EXAVITQu4vr4xnSDxMaL",  # "Sarah"
}

DEFAULT_GENDER = "male"

def get_voice_for_gender(gender: str, provider: str = "groq") -> str:
    """Get the appropriate voice for the given gender and provider."""
    gender = gender.lower()
    if provider == "elevenlabs":
        return ELEVENLABS_VOICES.get(gender, ELEVENLABS_VOICES["male"])
    return GROQ_VOICES.get(gender, GROQ_VOICES["male"])

def generate_speech_stream_elevenlabs(text: str, voice_id: str) -> Generator[bytes, None, None]:
    """Stream audio from ElevenLabs."""
    if not ELEVENLABS_API_KEY:
        print("Error: ELEVENLABS_API_KEY not set")
        yield b""
        return

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
    
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_turbo_v2", # Low latency model
        "output_format": "mp3_44100_128",
    }

    try:
        response = requests.post(url, json=data, headers=headers, stream=True)
        
        if response.status_code != 200:
             print(f"ElevenLabs API Error ({response.status_code}): {response.text}")
             yield b""
             return

        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                yield chunk
    except Exception as e:
        print(f"ElevenLabs Connection Error: {e}")
        yield b""

def generate_speech_stream(text: str, voice: str = "male", provider: str = "groq") -> Generator[bytes, None, None]:
    """
    Generate speech audio from text using specified provider.
    
    Args:
        text: The text to convert to speech.
        voice: The voice persona (or gender like 'male'/'female').
        provider: "groq" (Basic) or "elevenlabs" (Premium).
        
    Yields:
        Audio chunk bytes (mp3).
    """
    # Resolve helper voice to actual ID if needed
    if voice in ["male", "female"]:
        voice_id = get_voice_for_gender(voice, provider)
    else:
        # Check if the provided voice name is actually a gender key
        # This handles cases where frontend might pass 'male' even if logic differs
        voice_lower = voice.lower()
        if voice_lower in ["male", "female"]:
             voice_id = get_voice_for_gender(voice_lower, provider)
        else:
             voice_id = voice

    if provider == "elevenlabs":
        yield from generate_speech_stream_elevenlabs(text, voice_id)
        return

    # Default: Groq (PlayAI)
    if not GROQ_API_KEY:
        print("Error: GROQ_API_KEY not set")
        yield b""
        return

    # Groq TTS endpoint
    url = "https://api.groq.com/openai/v1/audio/speech"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": GROQ_TTS_MODEL,
        "input": text,
        "voice": voice_id,
        "response_format": "mp3" 
    }

    try:
        response = requests.post(url, json=data, headers=headers, stream=True)
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                message = error_data.get("error", {}).get("message", "Unknown error")
            except:
                message = response.text
            print(f"Groq TTS API Error ({response.status_code}): {message}")
            yield b""
            return

        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                yield chunk

    except Exception as e:
        print(f"Groq TTS Connection Error: {e}")
        yield b""
