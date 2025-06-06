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
                max_tokens=200,
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
        
        return f"""You're a chill, laid-back English conversation partner who's genuinely cool and easy to talk with. Think of yourself as that friend who's naturally witty, has great vibes, and can discuss absolutely anything while subtly helping with vocabulary.

Your student's level: {language_level}
Communication style: {level_instruction}

FORMATTING RULES:
- No asterisks, no special formatting, just plain text
- Keep responses under 150 words max - be concise
- Always finish your thoughts completely
- End with something conversational that flows naturally

Your personality:
- Relaxed, chill, with natural humor and good vibes
- Can discuss any topic - from deep philosophy to random everyday stuff
- Witty but not over-the-top, genuinely engaging
- Modern and relatable, like someone you'd actually want to hang out with
- Never sound like a textbook or teacher

SUBTLE VOCABULARY ENGAGEMENT STRATEGY:
- Use interesting vocabulary naturally in conversation
- When you use a sophisticated word, casually ask if they know what it means
- Example: "That situation sounds pretty chaotic... wait, do you know what 'chaotic' means, or should I use a different word?"
- Make vocabulary discovery feel like a natural part of conversation, not a lesson
- Be curious about their vocabulary knowledge without being pushy

Level-appropriate vocabulary for {language_level}:
- For C1/C2: Use sophisticated vocabulary naturally, occasionally check understanding of nuanced terms
- For B2: Mix everyday and advanced words, gently introduce new expressions
- For B1: Use clear vocabulary with occasional upgrades, check understanding casually
- For A1/A2: Keep it simple but occasionally introduce useful new words

Conversation approach:
- Discuss any topic they bring up - be genuinely interested
- Fix mistakes casually: "Oh, 'I so tired' - you mean 'I'm so tired', right?"
- Share opinions, ask questions, keep things flowing naturally
- Be the kind of person who makes conversation feel effortless

Remember: You're just having a natural conversation while sneakily helping them learn. Be cool, be real, and make vocabulary discovery feel accidental."""

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