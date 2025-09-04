import asyncio
import logging
import telebot
from ceo import ceo_dispatcher
from dotenv import load_dotenv
import os

load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен вашего бота
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    bot.reply_to(message, 
        "Привет! Я бот для поиска сотрудников. Просто напишите имя или фамилию сотрудника, и я найду информацию о нем."
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Обработчик команды /help"""
    bot.reply_to(message,
        "Как использовать бота:\n"
        "1. Просто напишите имя или фамилию сотрудника\n"
        "2. Я найду информацию о сотруднике и его удостоверениях\n"
        "3. Для выхода используйте /exit"
    )

@bot.message_handler(commands=['exit'])
def exit_command(message):
    """Обработчик команды /exit"""
    bot.reply_to(message, "До свидания! 👋")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Обработчик всех текстовых сообщений"""
    user_message = message.text
    
    # Отправляем сообщение о том, что обрабатываем запрос
    processing_msg = bot.reply_to(message, "🔍 Ищу информацию о сотруднике...")
    
    try:
        # Создаем асинхронную функцию для обработки
        async def process_request():
            # Создаем историю сообщений для ceo_dispatcher
            messages = [
                {"role": "user", "content": user_message}
            ]
            
            # Отправляем сообщение в ceo_dispatcher
            result = await ceo_dispatcher(messages)
            
            # Отправляем результат (уже отформатированный)
            bot.edit_message_text(
                result,
                chat_id=processing_msg.chat.id,
                message_id=processing_msg.message_id
            )
        
        # Запускаем асинхронную функцию
        asyncio.run(process_request())
        
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")
        bot.edit_message_text(
            f"❌ Произошла ошибка: {str(e)}",
            chat_id=processing_msg.chat.id,
            message_id=processing_msg.message_id
        )

def main():
    """Запуск бота"""
    print("🤖 Бот запущен...")
    bot.polling(none_stop=True)

if __name__ == '__main__':
    main()
