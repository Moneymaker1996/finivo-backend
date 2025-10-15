# utils/voice_engine.py
"""
Google Cloud Text-to-Speech utility for converting text to speech (MP3/OGG/WAV).
For use with Elite plan voice nudges or future voice integrations.
"""

from google.cloud import texttospeech
import os

def generate_voice_nudge(text: str, user_id: int) -> str:
    client = texttospeech.TextToSpeechClient()

    synthesis_input = texttospeech.SynthesisInput(text=text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-F"
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    audio_dir = os.path.join(os.getcwd(), "static", "audio")
    os.makedirs(audio_dir, exist_ok=True)
    output_path = os.path.join(audio_dir, f"nudge_{user_id}.mp3")
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

    return output_path
