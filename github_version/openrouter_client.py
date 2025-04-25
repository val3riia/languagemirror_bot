import os
import requests
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

class OpenRouterClient:
    """
    Client for OpenRouter API to generate AI completions.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (optional, will use environment variable if not provided)
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logging.warning("OPENROUTER_API_KEY environment variable is not set")
        
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
    
    def get_completion(self, system_message: str, messages: List[Dict[str, str]]) -> str:
        """
        Get a completion from the OpenRouter API.
        
        Args:
            system_message: System message providing context and instructions
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            Generated text response
        """
        if not self.api_key:
            return "I'm currently unable to generate responses. Please contact the administrator."
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://language-mirror-bot.com"  # Replace with your site's domain
        }
        
        # Prepare messages with system message at the beginning
        formatted_messages = [
            {"role": "system", "content": system_message}
        ] + messages
        
        payload = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": 0.7,
            "max_tokens": 250,
            "top_p": 0.9,
            "frequency_penalty": 0.4, 
            "presence_penalty": 0.6,
            "stop": ["User:", "Assistant:", "\n\n"]
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                self.logger.error(f"OpenRouter API error: {response.status_code}, {response.text}")
                return "Sorry, I encountered an error generating a response. Please try again later."
            
            response_data = response.json()
            message_content = response_data["choices"][0]["message"]["content"]
            return message_content
            
        except requests.exceptions.Timeout:
            self.logger.error("Request to OpenRouter API timed out")
            return "Sorry, the request timed out. Please try again later."
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request to OpenRouter API failed: {e}")
            return "Sorry, I encountered a connection error. Please try again later."
            
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            self.logger.error(f"Error parsing OpenRouter API response: {e}")
            return "Sorry, I encountered an error processing the response. Please try again later."
    
    def chat_completion(self, model: str, messages: List[Dict[str, str]], max_tokens: int = 500, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Get a chat completion from the OpenRouter API.
        
        Args:
            model: Model to use for completion
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature for generation (0.0 to 1.0)
            
        Returns:
            Raw API response as a dictionary
        """
        if not self.api_key:
            return {"error": "API key not set", "choices": [{"message": {"content": "I'm currently unable to generate responses. Please contact the administrator."}}]}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://language-mirror-bot.com"  # Replace with your site's domain
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                self.logger.error(f"OpenRouter API error: {response.status_code}, {response.text}")
                return {"error": f"API error: {response.status_code}", "choices": [{"message": {"content": "Sorry, I encountered an error generating a response. Please try again later."}}]}
            
            return response.json()
            
        except Exception as e:
            self.logger.error(f"Error in chat_completion: {e}")
            return {"error": str(e), "choices": [{"message": {"content": "Sorry, I encountered an error. Please try again later."}}]}