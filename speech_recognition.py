import os
import logging
import openai
import tempfile
import httpx
from io import BytesIO

# Configure logging
logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """
    A class to handle speech recognition for voice messages using OpenAI's Whisper API.
    """
    
    def __init__(self):
        """Initialize the speech recognizer."""
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY environment variable is not set. Voice recognition will not work.")
        
        # Set the API key for OpenAI
        openai.api_key = self.api_key
    
    async def download_voice_file(self, file_url, token):
        """
        Download a voice file from Telegram's servers.
        
        Args:
            file_url: The URL of the file to download
            token: The Telegram bot token
            
        Returns:
            BytesIO: A file-like object containing the audio data
        """
        try:
            # Set up request
            api_file_url = f"https://api.telegram.org/file/bot{token}/{file_url}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(api_file_url)
                if response.status_code != 200:
                    logger.error(f"Failed to download voice file: {response.status_code}")
                    return None
                
                # Return the content as a file-like object
                return BytesIO(response.content)
        except Exception as e:
            logger.error(f"Error downloading voice file: {e}")
            return None
    
    async def transcribe_voice(self, voice_file, language="en"):
        """
        Transcribe a voice message using OpenAI's Whisper API.
        
        Args:
            voice_file: A file-like object containing the voice message
            language: The language code (default: "en")
            
        Returns:
            str: The transcribed text or None if transcription failed
        """
        if not self.api_key:
            return "Sorry, voice recognition is currently unavailable. Please type your message instead."
        
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_file:
                temp_file.write(voice_file.getvalue())
                temp_file_path = temp_file.name
            
            # Transcribe with Whisper
            with open(temp_file_path, "rb") as audio_file:
                transcription = openai.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    language=language
                )
            
            # Clean up temporary file
            os.remove(temp_file_path)
            
            # Extract text from response
            transcribed_text = transcription.text
            logger.info(f"Transcribed text: {transcribed_text}")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Error transcribing voice message: {e}")
            return "Sorry, I couldn't transcribe your voice message. Please try again or type your message."