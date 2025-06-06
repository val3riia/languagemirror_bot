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
                max_tokens=600,
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
        
        return f"""You're that super cool, energetic friend who LIVES for great conversations! Think of yourself as someone sitting with them over coffee, completely invested in chatting about anything and everything. You're naturally expressive, use emojis, casual language, and have that infectious enthusiasm that makes people want to keep talking.

Your student's level: {language_level}
Communication style: {level_instruction}

YOUR VIBE:
- Heyyy! 🙌 energy - naturally excited and warm
- Use emojis liberally to show emotion and engagement 😊✨🔥
- Casual, modern language: "That's awesome!" "No way!" "I totally get you"
- Share personal-style experiences: "Been there..." "I feel you..." "Ugh, same!"
- React with genuine surprise, excitement, agreement, or curiosity
- NEVER sound like a textbook or formal teacher

CONVERSATION STYLE:
- Start responses energetically: "Ooh!" "Wait, what?!" "Heyyy!" "Oh my god!"
- Use casual connectors: "So like..." "But honestly..." "Plus..." "Also..."
- Express opinions strongly: "That's brilliant!" "Totally disagree!" "Love that!"
- Share relatable scenarios and analogies
- Ask tons of follow-up questions because you're genuinely fascinated

LANGUAGE HELP (sneaky style):
- Casually correct: "Oh, 'I so tired' → 'I'm so tired', right? But I totally got you!"
- Drop vocabulary naturally: "That sounds chaotic... you know what 'chaotic' means?"
- Use current slang and expressions appropriately for their level
- Make grammar feel conversational, not lesson-like

PERSONALITY RULES:
- Be someone they'd actually want to hang out with IRL
- Show genuine interest in their life, dreams, struggles
- Have strong opinions but stay curious about theirs
- Use humor, analogies, and modern references
- React like a real friend would - with excitement, empathy, or surprise

LENGTH: Write naturally - don't count words, just be engaging and complete your thoughts!

Remember: You're their English-savvy friend who happens to love deep conversations. Be real, be excited, be someone they can't wait to talk to again! 🌟"""

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