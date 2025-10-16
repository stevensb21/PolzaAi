#!/usr/bin/env python3
"""
Скрипт для тестирования Telegram бота
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram_bot import process_order

load_dotenv()

async def test_bot():
    """Тестирует функции бота без запуска Telegram API"""
    
    print("🧪 Тестирование функций бота...")
    
    # Тестовые данные
    test_messages = [
        "Иванов Иван Иванович, Менеджер, +7-999-123-45-67, СНИЛС: 123-456-789 01, 01.01.1990",
        "Петров Петр Петрович",
        "Инженер, +7-888-777-66-55",
        "СНИЛС: 987-654-321 00, 15.05.1985"
    ]
    
    user_id = 12345  # Тестовый ID пользователя
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Тест {i}: {message}")
        print("-" * 50)
        
        try:
            result = await process_order(user_id, message)
            print(f"✅ Результат: {result}")
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    print("🚀 Запуск тестирования...")
    asyncio.run(test_bot())
    print("\n✅ Тестирование завершено!")
