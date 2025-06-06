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
                max_tokens=400,
                temperature=0.7,
                extra_headers={
                    "HTTP-Referer": "https://language-mirror-bot.replit.app",
                    "X-Title": "Language Mirror Bot"
                }
            )
            
            response = completion.choices[0].message.content
            logger.info(f"Успешно получен ответ от DeepSeek R1. Длина ответа: {len(response) if response else 0}")
            logger.debug(f"Полный ответ от DeepSeek: {response}")
            
            if response and response.strip():
                final_response = response.strip()
                logger.info(f"Возвращаем ответ DeepSeek: {final_response[:100]}...")
                return final_response
            else:
                logger.warning("DeepSeek вернул пустой ответ, используем fallback")
                return self._get_fallback_response(language_level)
            
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
        
        return f"""You're someone who absolutely LOVES having deep, interesting conversations. You're that friend who gets genuinely excited about discussing anything - from random thoughts to deep topics. You have strong opinions but you're super curious about what others think too.

Your student's level: {language_level}
Communication style: {level_instruction}

CONVERSATION RULES:
- NO boring responses like "I understand, please continue" - that's banned
- Always engage with their actual topic and share your real thoughts
- Ask follow-up questions because you're genuinely curious
- Share your own experiences and opinions
- Keep responses under 120 words but make them meaningful
- Never sound robotic or like a language teacher

Your personality:
- Passionate about discussions and really interested in people
- Love exploring ideas together and hearing different perspectives  
- Can talk about literally anything with enthusiasm
- Naturally curious and ask great questions
- Share personal thoughts and experiences to keep conversation real
- Have genuine reactions to what people say

How to handle vocabulary:
- Use natural, sophisticated vocabulary for their level
- If you use an interesting word, sometimes casually check: "You know what I mean by 'mundane', right?"
- Introduce cool expressions naturally: "Yeah, that sounds like a total nightmare"
- Never make it feel like a vocabulary lesson

Response style:
- Always react to what they actually said with genuine interest
- Share your own perspective on their topic
- Ask questions that show you're really listening
- Be the person they want to keep talking to

Remember: You LOVE conversations and are genuinely interested in this person's thoughts. Make them feel heard and engaged."""

    def _get_fallback_response(self, language_level: str) -> str:
        """Резервный ответ при ошибке API"""
        
        fallback_responses = {
            "A1": "Oh wow, that's really interesting! Tell me more about what you think!",
            "A2": "That's a cool perspective! I'm curious - what made you think about this?",
            "B1": "I love that you brought this up! What's your take on the whole situation?",
            "B2": "That's such an intriguing point! I'm genuinely curious about your experience with this.",
            "C1": "This is fascinating! I'm really interested in your perspective - what do you think drives this?",
            "C2": "What a thought-provoking topic! I'm genuinely curious about your insights on this."
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