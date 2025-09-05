import asyncio
import logging
import telebot
from ceo import ceo_dispatcher
from dotenv import load_dotenv
import os
import time
from logger import bot as bot_log, debug, info, error, critical, log_function_entry, log_function_exit

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
    """Обрабатывает все входящие сообщения с надежной обработкой ошибок"""
    log_function_entry("handle_message", args=(message.text,))
    
    user_message = message.text
    processing_msg = None
    
    try:
        # Отправляем сообщение о том, что обрабатываем запрос
        processing_msg = bot.reply_to(message, "🔍 Ищу информацию о сотруднике...")
        
        # Создаем асинхронную функцию для обработки
        async def process_request():
            try:
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
                
            except Exception as e:
                error_msg = f"❌ Ошибка в process_request: {str(e)}"
                error(error_msg)
                # Пытаемся отправить сообщение об ошибке
                try:
                    bot.edit_message_text(
                        f"❌ Произошла ошибка при обработке запроса: {str(e)}",
                        chat_id=processing_msg.chat.id,
                        message_id=processing_msg.message_id
                    )
                except:
                    # Если не удалось отредактировать сообщение, отправляем новое
                    bot.reply_to(message, f"❌ Произошла ошибка при обработке запроса: {str(e)}")
        
        # Запускаем асинхронную функцию
        asyncio.run(process_request())
        
        log_function_exit("handle_message", result="Сообщение обработано успешно")
        
    except Exception as e:
        error_msg = f"❌ Ошибка обработки сообщения: {str(e)}"
        error(error_msg)
        log_function_exit("handle_message", error=error_msg)
        
        # Пытаемся отправить сообщение об ошибке
        try:
            if processing_msg:
                bot.edit_message_text(
                    f"❌ Произошла ошибка: {str(e)}",
                    chat_id=processing_msg.chat.id,
                    message_id=processing_msg.message_id
                )
            else:
                bot.reply_to(message, f"❌ Произошла ошибка: {str(e)}")
        except Exception as send_error:
            error(f"❌ Не удалось отправить сообщение об ошибке: {str(send_error)}")

@bot.message_handler(commands=['reset'])
def reset_chat(message):
    """Сбрасывает историю чата"""
    log_function_entry("reset_chat", args=(message.text,))
    
    try:
        # Создаем историю сообщений для ceo_dispatcher
        messages = []
        
        # Отправляем сообщение в ceo_dispatcher
        asyncio.run(ceo_dispatcher(messages, []))
        
        # Отправляем результат
        bot.reply_to(message, "✅ История чата сброшена")
        
        log_function_exit("reset_chat", result="История чата сброшена")
        
    except Exception as e:
        error_msg = f"❌ Ошибка сброса истории чата: {str(e)}"
        error(error_msg)
        log_function_exit("reset_chat", error=error_msg)
        bot.reply_to(message, "❌ Произошла ошибка при сбросе истории чата")

def main():
    """Главная функция с надежной обработкой ошибок подключения"""
    log_function_entry("main")
    
    max_retries = 5
    retry_delay = 5  # секунд
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                info(f"🔄 Попытка переподключения {attempt}/{max_retries}")
                time.sleep(retry_delay)
            
            print("🤖 Бот запущен...")
            bot.polling(
                none_stop=True,
                interval=1,
                timeout=20,
                long_polling_timeout=20
            )
            
            log_function_exit("main", result="Бот запущен успешно")
            break
            
        except (ConnectionError, ConnectionResetError, ConnectionAbortedError) as e:
            error_msg = f"❌ Ошибка подключения (попытка {attempt + 1}/{max_retries}): {str(e)}"
            error(error_msg)
            
            if attempt == max_retries - 1:
                critical("❌ КРИТИЧЕСКАЯ ОШИБКА: Превышено максимальное количество попыток переподключения")
                log_function_exit("main", error="Превышено максимальное количество попыток переподключения")
                break
            else:
                info(f"⏳ Ожидание {retry_delay} секунд перед следующей попыткой...")
                
        except Exception as e:
            error_msg = f"❌ Неожиданная ошибка (попытка {attempt + 1}/{max_retries}): {str(e)}"
            error(error_msg)
            
            if attempt == max_retries - 1:
                critical("❌ КРИТИЧЕСКАЯ ОШИБКА: Превышено максимальное количество попыток")
                log_function_exit("main", error=error_msg)
                break
            else:
                info(f"⏳ Ожидание {retry_delay} секунд перед следующей попыткой...")

if __name__ == '__main__':
    main()
