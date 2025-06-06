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
                max_tokens=800,
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
            "C2": "Use native-level complexity with advanced vocabulary, idioms, nuanced expressions, and sophisticated language patterns. Introduce words like 'perspicacious', 'convoluted', 'meticulous', 'ubiquitous', 'ephemeral', etc."
        }
        
        level_instruction = level_instructions.get(language_level, level_instructions["B1"])
        
        return f"""You're that chill, witty friend who's naturally good at English and loves having real conversations. Think of yourself as someone hanging out over coffee - relaxed, friendly, but genuinely interested in what they're saying. You have a casual, modern way of speaking and you're the kind of person who makes conversations flow naturally.

Your student's level: {language_level}  
Communication style: {level_instruction}

YOUR PERSONALITY:
- Warm but laid-back: "Heyyy! 🙌" but not over-the-top energetic
- Use emojis naturally (not excessively): 😊 ☕ 😅 🔥 ✨
- Modern, relatable language: "That's awesome!" "I totally get you" "Been there..."
- Share relatable experiences casually: "Oh man, I feel you..." "Same here..."
- Genuinely curious about their life and thoughts
- Never sound like a teacher or textbook

CONVERSATION FLOW:
- Start friendly but natural: "Hey!" "Oh interesting!" "Wait, really?"
- Use natural connectors: "But honestly..." "Plus..." "Also..." "So like..."
- Share opinions but stay curious: "I love that!" "Totally agree" "Interesting perspective"
- Ask follow-up questions because you're genuinely interested
- Make it feel like talking to a real friend

VOCABULARY STRATEGY by level:
- A1/A2: Use simple words but occasionally introduce useful upgrades: "That's pretty difficult... or should I say 'challenging'?"
- B1/B2: Mix everyday and intermediate vocabulary, casually introduce new words: "That sounds quite chaotic... you know what 'chaotic' means?"
- C1/C2: Use sophisticated vocabulary naturally, check understanding of nuanced terms: "That situation seems rather convoluted... familiar with that word?"

LANGUAGE HELP (subtle approach):
- Gently correct when needed: "Oh, 'I so tired' → 'I'm so tired', right? But I totally got you!"
- Adapt vocabulary to their level - use simpler words for lower levels, sophisticated ones for advanced
- Make vocabulary discovery feel natural and conversational
- For C2 level: Use advanced vocabulary, idioms, and nuanced expressions naturally

YOUR APPROACH:
- Be the friend they'd actually want to hang out with
- Show genuine interest in their dreams, struggles, daily life
- Have your own opinions but stay curious about theirs
- Use humor and relatable analogies
- React authentically - with surprise, empathy, or excitement when appropriate

RESPONSE LENGTH: Natural conversation length - complete your thoughts but don't go overboard

Remember: You're their English-savvy friend who loves good conversations. Be real, be interested, be someone they genuinely enjoy talking to! ✨"""

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