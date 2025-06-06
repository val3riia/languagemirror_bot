"""
DeepSeek API клиент для Language Mirror Bot.
Обеспечивает доступ к модели DeepSeek R1 через OpenRouter API.
"""

import os
import json
import logging
from typing import List, Dict, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class DeepSeekClient:
    """Клиент для работы с DeepSeek R1 через OpenRouter API"""
    
    def __init__(self):
        """Инициализация клиента DeepSeek"""
        self.api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.error("DEEPSEEK_API_KEY не найден в переменных окружения")
            raise ValueError("DEEPSEEK_API_KEY не установлен")
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )
        
        # Модель DeepSeek R1
        self.model = "deepseek/deepseek-r1-0528:free"
        
        logger.info("DeepSeek клиент инициализирован успешно")
    
    def generate_discussion_response(
        self, 
        user_message: str, 
        language_level: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Генерирует ответ для дискуссии с пользователем.
        
        Args:
            user_message: Сообщение пользователя
            language_level: Уровень владения языком (A1-C2)
            conversation_history: История беседы
            
        Returns:
            Ответ бота для продолжения дискуссии
        """
        try:
            # Системный промпт для дискуссий
            system_prompt = self._get_discussion_system_prompt(language_level)
            
            # Формируем историю сообщений
            messages = [{"role": "system", "content": system_prompt}]
            
            # Добавляем историю беседы, если есть
            if conversation_history:
                messages.extend(conversation_history)
            
            # Добавляем текущее сообщение пользователя
            messages.append({"role": "user", "content": user_message})
            
            logger.info(f"Отправка запроса к DeepSeek R1 для уровня {language_level}")
            logger.debug(f"Количество сообщений в истории: {len(messages)}")
            
            # Запрос к DeepSeek R1
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://language-mirror-bot.replit.app",
                    "X-Title": "Language Mirror Bot"
                }
            )
            
            response = completion.choices[0].message.content
            logger.info("Успешно получен ответ от DeepSeek R1")
            
            return response.strip() if response else "I understand. Please continue sharing your thoughts."
            
        except Exception as e:
            logger.error(f"Ошибка при обращении к DeepSeek R1: {e}")
            return self._get_fallback_response(language_level)
    
    def _get_discussion_system_prompt(self, language_level: str) -> str:
        """Формирует системный промпт для дискуссий на основе уровня языка"""
        
        level_instructions = {
            "A1": "Use very simple vocabulary and short sentences. Speak slowly and clearly.",
            "A2": "Use basic vocabulary and simple grammar. Be patient and encouraging.",
            "B1": "Use everyday vocabulary. Explain new words when needed.",
            "B2": "Use varied vocabulary and more complex sentences. Introduce advanced topics naturally.",
            "C1": "Use sophisticated vocabulary and complex grammar. Discuss abstract topics.",
            "C2": "Use native-level complexity. Discuss any topic with full linguistic range."
        }
        
        level_instruction = level_instructions.get(language_level, level_instructions["B1"])
        
        return f"""You're an incredibly vibrant, enthusiastic English conversation buddy with burning eyes for language and absolutely amazing humor! Think of yourself as that super energetic friend who's obsessed with words and makes learning feel like the coolest thing ever.

Your student's level: {language_level}
Communication style: {level_instruction}

ABSOLUTE FORMATTING RULES (FOLLOW THESE EXACTLY):
- ZERO asterisks allowed - not even one single asterisk anywhere
- NO special formatting symbols at all
- Write in completely plain text
- Finish every single thought completely - NEVER cut off mid-sentence
- Always end with something that keeps the conversation going

Your personality (be VIBRANT and MODERN):
- Super enthusiastic with infectious energy and burning passion for language
- Crack amazing jokes and use hilarious analogies
- Share wild stories and random observations that make people laugh
- Be the kind of person who lights up a room when they talk
- Modern, trendy, with that cool factor that makes learning addictive
- Use contemporary slang and expressions naturally

VOCABULARY HIGHLIGHTING SYSTEM:
- When you use sophisticated or interesting vocabulary, put the word in parentheses like this: (sophisticated)
- Only highlight words that are genuinely cool and worth learning
- Example: "I'm absolutely (mesmerized) by how quickly you're picking this up!"
- Choose words that feel natural but impressive for their level

Level-specific vocabulary for {language_level}:
- For C1/C2: Use nuanced expressions, academic vocabulary, sophisticated turns of phrase - highlight the really juicy ones
- For B2: Mix everyday and advanced vocabulary - highlight the stepping-stone words
- For B1: Use clear vocabulary with some challenging terms - highlight practical upgrades
- For A1/A2: Simple vocabulary with occasional gems - highlight the confidence boosters

Language help approach:
- Fix mistakes with humor: "Haha, 'I so tired' should be 'I'm so tired' - but your enthusiasm came through loud and clear!"
- Tell stories instead of giving lists
- Show natural collocations: "We say 'running on fumes' not 'driving on fumes' - English is weird like that!"
- Use modern idioms and slang: "You're absolutely crushing it!" instead of "You're doing very well"

Content boundaries:
- Avoid heavy topics (politics, religion, wars)
- Redirect with energy: "Whoa, that's getting heavy! Let's talk about something that'll make us both smile - what's the weirdest food combo you secretly love?"
- Keep it upbeat and contemporary

Remember: You're the friend who makes English feel like the coolest superpower ever. Be energetic, complete every thought, and make vocabulary feel like collecting treasure!"""

    def _get_fallback_response(self, language_level: str) -> str:
        """Резервный ответ при ошибке API"""
        
        fallback_responses = {
            "A1": "That's interesting! Can you tell me more?",
            "A2": "I see what you mean. What do you think about that?",
            "B1": "That's a good point. How did you come to that conclusion?",
            "B2": "Interesting perspective! I'd love to hear more about your experience with this.",
            "C1": "That's quite thought-provoking. What factors do you think contribute to this situation?",
            "C2": "Fascinating insight! How do you think this phenomenon might evolve in the future?"
        }
        
        return fallback_responses.get(language_level, fallback_responses["B1"])
    
    def is_available(self) -> bool:
        """Проверяет доступность DeepSeek API"""
        try:
            # Простой тестовый запрос
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
                extra_headers={
                    "HTTP-Referer": "https://language-mirror-bot.replit.app",
                    "X-Title": "Language Mirror Bot"
                }
            )
            return True
        except Exception as e:
            logger.error(f"DeepSeek API недоступен: {e}")
            return False


# Глобальный экземпляр клиента
deepseek_client = None

def get_deepseek_client() -> Optional[DeepSeekClient]:
    """Получает экземпляр DeepSeek клиента"""
    global deepseek_client
    
    if deepseek_client is None:
        try:
            deepseek_client = DeepSeekClient()
        except Exception as e:
            logger.error(f"Не удалось инициализировать DeepSeek клиент: {e}")
            return None
    
    return deepseek_client