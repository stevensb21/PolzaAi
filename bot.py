import asyncio
import logging
import telebot
from ceo import ceo_dispatcher
from dotenv import load_dotenv
import os
import time
import fcntl
import sys
from logger import bot as bot_log, debug, info, error, critical, log_function_entry, log_function_exit
from generateDocx import create_tetracom_document

# Проверка на уже запущенный экземпляр
def check_single_instance():
    """Проверяет, что запущен только один экземпляр бота"""
    lock_file = '/tmp/polzaai_bot.lock'
    try:
        # Пытаемся создать файл блокировки
        lock_fd = os.open(lock_file, os.O_CREAT | os.O_WRONLY | os.O_TRUNC)
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Если успешно, записываем PID
        os.write(lock_fd, str(os.getpid()).encode())
        os.close(lock_fd)
        
        info("✅ Экземпляр бота запущен успешно")
        return True
    except (OSError, IOError):
        error("❌ Бот уже запущен! Остановите другой экземпляр перед запуском.")
        sys.exit(1)

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

# Словарь для хранения ID пользователей, которым нужно отправлять заявки
# Формат: {user_id: {"name": "Имя", "chat_id": chat_id}}
notification_users = {
    "8316311496": {"name": "Лариса", "chat_id": "8316311496"},
    "1174287803": {"name": "Пользователь 1174287803", "chat_id": "1174287803"}
}

def add_notification_user(user_id, name, chat_id):
    """Добавляет пользователя в список для уведомлений о готовых заявках"""
    notification_users[user_id] = {
        "name": name,
        "chat_id": chat_id
    }
    info(f"Добавлен пользователь для уведомлений: {name} (ID: {user_id}, Chat: {chat_id})")

def remove_notification_user(user_id):
    """Удаляет пользователя из списка уведомлений"""
    if user_id in notification_users:
        user_info = notification_users.pop(user_id)
        info(f"Удален пользователь из уведомлений: {user_info['name']} (ID: {user_id})")

async def get_certificate_details(certificate_names):
    """Получает полную информацию о сертификатах из API"""
    try:
        import requests
        from pull_order import BASE_URL
        
        # Получаем список всех сертификатов
        response = requests.get(
            f"{BASE_URL}/api/certificates",
            timeout=30,
            proxies={"http": None, "https": None},
            headers={
                'User-Agent': 'PolzaAI-Bot/1.0',
                'Authorization': f'Bearer {os.getenv("API_TOKEN")}'
            }
        )
        
        if response.status_code == 200:
            try:
                certificates_data = response.json()
                info(f"Получены данные сертификатов: {type(certificates_data)}")
                
                # Проверяем, что это список
                if isinstance(certificates_data, list):
                    certs_list = certificates_data
                elif isinstance(certificates_data, dict) and "data" in certificates_data:
                    certs_list = certificates_data["data"]
                else:
                    info(f"Неожиданный формат данных сертификатов: {certificates_data}")
                    return [{"name": name, "description": "Описание отсутствует"} for name in certificate_names]
                
                certificate_details = []
                
                for cert_name in certificate_names:
                    # Ищем сертификат по названию
                    found = False
                    for cert in certs_list:
                        if isinstance(cert, dict) and cert.get("name", "").lower() == cert_name.lower():
                            certificate_details.append({
                                "name": cert.get("name", cert_name),
                                "description": cert.get("description", "Описание отсутствует")
                            })
                            found = True
                            break
                    
                    if not found:
                        # Если не найден, добавляем с базовым описанием
                        certificate_details.append({
                            "name": cert_name,
                            "description": "Описание отсутствует"
                        })
                
                return certificate_details
                
            except Exception as e:
                error(f"Ошибка при обработке данных сертификатов: {e}")
                return [{"name": name, "description": "Описание отсутствует"} for name in certificate_names]
        else:
            info(f"Не удалось получить данные сертификатов: {response.status_code}")
            return [{"name": name, "description": "Описание отсутствует"} for name in certificate_names]
            
    except Exception as e:
        error(f"Ошибка при получении данных сертификатов: {e}")
        return [{"name": name, "description": "Описание отсутствует"} for name in certificate_names]

async def send_ready_order_notification(order_data):
    """Отправляет уведомление о готовой заявке всем подписанным пользователям"""
    try:
        info(f"Начинаем отправку уведомлений для заказа: {order_data}")
        employee = order_data.get("employee", {})
        employee_name = employee.get("full_name", "Неизвестно")
        employee_photo = employee.get("photo")
        info(f"Данные сотрудника: {employee_name}, фото: {employee_photo}")
        
        # Получаем полную информацию о сертификатах
        certificate_names = order_data.get("certificate", [])
        certificate_details = await get_certificate_details(certificate_names)
        
        # Формируем сообщение в том же формате, что и основной ответ
        birth_date = employee.get("birth_date", "Не указана")
        if birth_date != "Не указана" and birth_date:
            # Преобразуем дату из ISO формата в DD.MM.YYYY
            try:
                from datetime import datetime
                if "T" in birth_date:
                    birth_date = birth_date.split("T")[0]
                date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
                birth_date = date_obj.strftime("%d.%m.%Y")
            except:
                pass
        
        # Формируем список сертификатов с описаниями
        certificates_text = ""
        for cert in certificate_details:
            certificates_text += f"• {cert['name']} - {cert['description']}\n"
        
        message_text = f"""Заказ оформлен и отправлен в базу данных 
 для {employee_name} 
 с удостоверениями:
{certificates_text}
 СНИЛС: {employee.get("snils", "Не указан")} 
 ИНН: {employee.get("inn", "Не указан")} 
 Должность: {employee.get("position", "Не указана")} 
 Дата рождения: {birth_date} 
 Телефон: {employee.get("phone", "Не указан")}"""
        
        # Отправляем уведомление всем подписанным пользователям
        info(f"Список пользователей для уведомлений: {notification_users}")
        for user_id, user_info in notification_users.items():
            try:
                chat_id = user_info["chat_id"]
                user_name = user_info["name"]
                
                # Отправляем текстовое сообщение
                bot.send_message(chat_id, message_text, parse_mode="Markdown")
                
                # Если есть фото, отправляем его
                if employee_photo and employee_photo != "null":
                    try:
                        # Проверяем, является ли photo полным URL
                        if employee_photo.startswith('http'):
                            # Это уже полный URL
                            photo_url = employee_photo
                        else:
                            # Это file_id или имя файла, нужно получить полный URL
                            try:
                                # Пытаемся получить информацию о файле
                                file_info = bot.get_file(employee_photo)
                                photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
                            except:
                                # Если не удалось получить file_info, попробуем как file_id
                                try:
                                    # Пытаемся получить информацию о файле по file_id
                                    file_info = bot.get_file(employee_photo)
                                    photo_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
                                except:
                                    # Если все не удалось, пропускаем фото
                                    info(f"Не удалось получить URL для фото {employee_photo}")
                                    continue
                        
                        # Скачиваем фото
                        import requests
                        photo_response = requests.get(photo_url, timeout=10)
                        if photo_response.status_code == 200:
                            # Отправляем фото
                            bot.send_photo(chat_id, photo_response.content, 
                                         caption=f"Фото сотрудника: {employee_name}")
                            info(f"Фото отправлено для {user_name}")
                        else:
                            info(f"Не удалось загрузить фото для {user_name}: {photo_response.status_code}")
                    except Exception as e:
                        error(f"Ошибка при отправке фото для {user_name}: {e}")
                
                info(f"Уведомление отправлено пользователю {user_name} (ID: {user_id})")
                
            except Exception as e:
                error(f"Ошибка при отправке уведомления пользователю {user_info['name']}: {e}")
        
        info(f"Уведомления о готовой заявке для {employee_name} отправлены {len(notification_users)} пользователям")
        
        # Создаем документ Word
        try:
            info("Создаем документ Word...")
            create_tetracom_document(order_data, certificate_details)
            info("Документ Word успешно создан")
            
            # Отправляем документ всем подписанным пользователям
            from generateDocx import generate_filename
            filename = generate_filename(order_data, certificate_details)
            
            for user_id, user_info in notification_users.items():
                try:
                    chat_id = user_info["chat_id"]
                    user_name = user_info["name"]
                    
                    # Отправляем документ
                    with open(filename, 'rb') as doc_file:
                        bot.send_document(chat_id, doc_file, 
                                        caption=f"📄 Документ для заказа: {employee_name}")
                    info(f"Документ отправлен пользователю {user_name}")
                    
                except Exception as e:
                    error(f"Ошибка при отправке документа пользователю {user_info['name']}: {e}")
            
            # Удаляем временный файл
            try:
                os.remove(filename)
                info(f"Временный файл {filename} удален")
            except:
                pass
                
        except Exception as e:
            error(f"Ошибка при создании или отправке документа: {e}")
        
    except Exception as e:
        error(f"Ошибка при отправке уведомлений о готовой заявке: {e}")

@bot.message_handler(commands=['start'])
def start(message):
    """Обработчик команды /start"""
    bot.reply_to(message, 
        "🤖 **Добро пожаловать в бот для управления сотрудниками!**\n\n"
        "**Доступные команды:**\n"
        "• `/start` - Показать это сообщение\n"
        "• `/help` - Показать справку\n"
        "• `/subscribe` - Подписаться на уведомления о готовых заявках\n"
        "• `/unsubscribe` - Отписаться от уведомлений\n"
        "• `/notifications` - Показать список подписанных пользователей\n"
        "• `/exit` - Выход\n\n"
        "**Возможности:**\n"
        "• Поиск информации о сотрудниках\n"
        "• Создание заявок на удостоверения\n"
        "• Автоматические уведомления о готовых заявках\n\n"
        "Просто напишите имя сотрудника для поиска или отправьте данные для создания заявки!",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Обработчик команды /help"""
    bot.reply_to(message,
        "Как использовать бота:\n"
        "1. Просто напишите имя или фамилию сотрудника\n"
        "2. Я найду информацию о сотруднике и его удостоверениях\n"
        "3. Для создания заказа с фото:\n"
        "   - Отправьте фото с подписью (данные сотрудника)\n"
        "   - Или сначала фото, затем данные отдельным сообщением\n"
        "4. Для выхода используйте /exit"
    )

@bot.message_handler(commands=['exit'])
def exit_command(message):
    """Обработчик команды /exit"""
    bot.reply_to(message, "До свидания! 👋")

@bot.message_handler(commands=['subscribe'])
def subscribe_command(message):
    """Подписаться на уведомления о готовых заявках"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or message.from_user.username or "Пользователь"
    chat_id = message.chat.id
    
    add_notification_user(user_id, user_name, chat_id)
    bot.reply_to(message, f"✅ {user_name}, вы подписаны на уведомления о готовых заявках!")

@bot.message_handler(commands=['unsubscribe'])
def unsubscribe_command(message):
    """Отписаться от уведомлений о готовых заявках"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name or message.from_user.username or "Пользователь"
    
    remove_notification_user(user_id)
    bot.reply_to(message, f"❌ {user_name}, вы отписаны от уведомлений о готовых заявках!")

@bot.message_handler(commands=['notifications'])
def notifications_command(message):
    """Показать список подписанных пользователей"""
    if not notification_users:
        bot.reply_to(message, "📭 Нет подписанных пользователей на уведомления")
        return
    
    text = "📋 **Подписанные пользователи на уведомления:**\n\n"
    for user_id, user_info in notification_users.items():
        text += f"👤 {user_info['name']} (ID: {user_id})\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(content_types=['photo'])
def handle_photo_with_text(message):
    """Обработчик фотографий с текстом"""
    log_function_entry("handle_photo_with_text", args=(message.photo, message.caption))
    try:
        # Получаем фото с наилучшим качеством
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Получаем информацию о файле с повторными попытками
        max_retries = 3
        file_info = None
        
        for attempt in range(max_retries):
            try:
                file_info = bot.get_file(file_id)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    info(f"Попытка {attempt + 1} получения файла не удалась: {e}. Повторяю...")
                    time.sleep(1)  # Ждем 1 секунду перед повторной попыткой
                else:
                    raise e
        
        if not file_info:
            raise Exception("Не удалось получить информацию о файле после всех попыток")
            
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info.file_path}"
        
        # Проверяем доступность URL
        try:
            import requests
            test_response = requests.head(file_url, timeout=5)
            if test_response.status_code != 200:
                info(f"URL фото недоступен, используем file_id: {file_id}")
                file_url = file_id  # Используем file_id как fallback
        except Exception as e:
            info(f"Не удалось проверить доступность URL, используем file_id: {e}")
            file_url = file_id  # Используем file_id как fallback
        
        info(f"Получено фото: {file_url}")
        
        # Получаем текст из подписи к фото
        text_content = message.caption or ""
        
        if text_content:
            # Если есть текст - обрабатываем как заказ с фото
            info(f"Обрабатываем заказ с фото: {text_content}")
            
            # Создаем асинхронную функцию для обработки
            async def process_photo_order():
                try:
                    # Создаем историю сообщений для ceo_dispatcher
                    messages = [
                        {
                            "role": "user", 
                            "content": text_content,
                            "photo": file_url
                        }
                    ]
                    
                    # Отправляем сообщение в ceo_dispatcher
                    result = await ceo_dispatcher(messages)
                    
                    # Отправляем результат
                    bot.reply_to(message, result)
                    
                except Exception as e:
                    error_msg = f"❌ Ошибка обработки заказа с фото: {str(e)}"
                    error(error_msg)
                    bot.reply_to(message, error_msg)
            
            # Запускаем асинхронную обработку
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(process_photo_order())
            finally:
                loop.close()
            
        else:
            # Если нет текста - сохраняем фото для следующего сообщения
            global last_photo_url
            last_photo_url = file_url
            bot.reply_to(message, f"📸 Фото получено! URL: {file_url}\n\nТеперь отправьте данные сотрудника для создания заказа с фотографией.")
        
        log_function_exit("handle_photo_with_text", result="Фото с текстом успешно обработано")
        
    except Exception as e:
        error_msg = f"❌ Ошибка обработки фото: {str(e)}"
        error(error_msg)
        
        # Отправляем более понятное сообщение пользователю
        if "ConnectionResetError" in str(e) or "Connection aborted" in str(e):
            user_msg = "❌ Ошибка сети при получении фото. Попробуйте отправить фото еще раз."
        elif "timeout" in str(e).lower():
            user_msg = "❌ Превышено время ожидания. Попробуйте отправить фото еще раз."
        else:
            user_msg = f"❌ Ошибка обработки фото: {str(e)}"
        
        bot.reply_to(message, user_msg)
        log_function_exit("handle_photo_with_text", error=error_msg)

# Глобальная переменная для хранения последнего URL фото
last_photo_url = None

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
                
                # Добавляем фото в сообщение, если оно есть
                global last_photo_url
                if last_photo_url:
                    messages[0]["photo"] = last_photo_url
                    info(f"Добавляем фото в сообщение: {last_photo_url}")
                    # Очищаем фото после использования
                    last_photo_url = None
                
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
    
    # Проверяем, что запущен только один экземпляр
    check_single_instance()
    
    max_retries = 5
    retry_delay = 5  # секунд
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                info(f"🔄 Попытка переподключения {attempt}/{max_retries}")
                time.sleep(retry_delay)
            
            print("🤖 Бот запущен...")
            try:
                bot.remove_webhook()
                info("✅ Webhook удален успешно")
            except Exception as e:
                info(f"ℹ️ Webhook не был активен или уже удален: {e}")
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
