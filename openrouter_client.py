import os
import requests
import json
import logging
from typing import List, Dict, Any

class OpenRouterClient:
    """
    Client for OpenRouter API to generate AI completions.
    """
    
    def __init__(self):
        """Initialize the OpenRouter client."""
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            logging.warning("OPENROUTER_API_KEY environment variable is not set")
        
        self.api_base = "https://openrouter.ai/api/v1"
        self.model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini-search-preview")
        
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
            "temperature": 0.9,
            "max_tokens": 500,
            "top_p": 1,
            "presence_penalty": 0.6,
            "frequency_penalty": 0
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
