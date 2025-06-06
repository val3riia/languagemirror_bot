#!/usr/bin/env python3
"""
Тест для проверки исправления управления сессиями.
Проверяет логику завершения сессий после обратной связи.
"""

import os
import sys
from unittest.mock import Mock, patch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_articles_feedback_completion():
    """Тестирует завершение сессии после обратной связи к статьям"""
    
    # Мокаем необходимые модули
    with patch('language_mirror_telebot.bot') as mock_bot, \
         patch('language_mirror_telebot.session_manager') as mock_session_manager:
        
        # Импортируем функцию после патчинга
        from language_mirror_telebot import handle_feedback_comment
        
        # Настраиваем моки
        mock_message = Mock()
        mock_message.from_user.id = 12345
        mock_message.text = "This was very helpful, thank you!"
        mock_message.chat.id = 12345
        
        mock_session = {"feedback_type": "helpful", "language_level": "B2"}
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager.end_session = Mock()
        
        # Вызываем функцию
        try:
            handle_feedback_comment(mock_message)
            
            # Проверяем, что сессия была завершена
            mock_session_manager.end_session.assert_called_once_with(12345)
            
            # Проверяем, что отправлено правильное сообщение
            mock_bot.send_message.assert_called()
            sent_message = mock_bot.send_message.call_args[0][1]
            
            assert "Ready for more?" in sent_message
            assert "/articles" in sent_message
            assert "/discussion" in sent_message
            
            logger.info("✅ Тест завершения сессии статей ПРОШЕЛ")
            return True
            
        except Exception as e:
            logger.error(f"❌ Тест завершения сессии статей ПРОВАЛЕН: {e}")
            return False

def test_discussion_feedback_completion():
    """Тестирует завершение сессии после обратной связи к дискуссиям"""
    
    with patch('language_mirror_telebot.bot') as mock_bot, \
         patch('language_mirror_telebot.session_manager') as mock_session_manager:
        
        from language_mirror_telebot import handle_discussion_feedback_comment
        
        mock_message = Mock()
        mock_message.from_user.id = 12345
        mock_message.text = "Great conversation!"
        mock_message.chat.id = 12345
        
        mock_session = {"feedback_type": "helpful", "language_level": "C1"}
        mock_session_manager.get_session.return_value = mock_session
        mock_session_manager.end_session = Mock()
        
        try:
            handle_discussion_feedback_comment(mock_message)
            
            mock_session_manager.end_session.assert_called_once_with(12345)
            
            mock_bot.send_message.assert_called()
            sent_message = mock_bot.send_message.call_args[0][1]
            
            assert "Ready for more?" in sent_message
            assert "/articles" in sent_message
            assert "/discussion" in sent_message
            
            logger.info("✅ Тест завершения сессии дискуссий ПРОШЕЛ")
            return True
            
        except Exception as e:
            logger.error(f"❌ Тест завершения сессии дискуссий ПРОВАЛЕН: {e}")
            return False

def main():
    """Запуск всех тестов"""
    logger.info("=== Тестирование исправлений управления сессиями ===")
    
    tests_passed = 0
    total_tests = 2
    
    if test_articles_feedback_completion():
        tests_passed += 1
    
    if test_discussion_feedback_completion():
        tests_passed += 1
    
    logger.info(f"Результат: {tests_passed}/{total_tests} тестов прошли")
    
    if tests_passed == total_tests:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОШЛИ! Исправления работают корректно.")
    else:
        logger.error("❌ Некоторые тесты провалились. Требуется дополнительная отладка.")
    
    return tests_passed == total_tests

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)