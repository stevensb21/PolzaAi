import os
import json
import asyncio
import logging
import urllib.parse
from telebot import TeleBot
from telebot.async_telebot import AsyncTeleBot
from telebot.types import Message
import requests
from dotenv import load_dotenv

from validate import makeOrderformat, validateOrder
from api import search_employees, addPeople, UpdatePeople
from notification_types import NotificationType
from notification_storage import NotificationStorage
from notification_scheduler import NotificationScheduler
from generateDocx import create_tetracom_document
from ceo_dispatcher import ceo_dispatcher, handle_search_request

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем бота
bot = AsyncTeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))

# Словарь для хранения истории чата каждого пользователя
user_chat_histories = {}

# Словарь для хранения фото из заявок пользователей
user_photos = {}

# Инициализация системы уведомлений
notification_storage = NotificationStorage()
notification_scheduler = None

async def process_order(user_id: int, message_text: str):
    """Обрабатывает заказ пользователя"""
    try:
        # Получаем историю чата пользователя
        chat_history = user_chat_histories.get(user_id, [])
        
        # Валидируем заказ
        validation_result = await validateOrder(message_text, chat_history)
        
        # Парсим JSON ответ
        try:
            if isinstance(validation_result, str):
                # Убираем markdown блоки если есть
                json_str = validation_result.strip()
                if json_str.startswith('```json'):
                    json_str = json_str[7:]  # Убираем ```json
                if json_str.endswith('```'):
                    json_str = json_str[:-3]  # Убираем ```
                json_str = json_str.strip()
                
                order_data = json.loads(json_str)
            else:
                order_data = validation_result
        except json.JSONDecodeError as e:
            return f"❌ Ошибка парсинга JSON: {e}\n📋 Исходный ответ: {validation_result}"
            
        # Проверяем, есть ли ошибки в данных
        if order_data.get("error") == "missing_data":
            # Добавляем сообщение пользователя в историю для следующей итерации
            chat_history.append({"role": "user", "content": message_text})
            user_chat_histories[user_id] = chat_history
            return f"❌ Не хватает данных: {order_data.get('message')}\n\nПожалуйста, уточните недостающие данные."
        
        # Добавляем сообщение пользователя в историю
        chat_history.append({"role": "user", "content": message_text})
        chat_history.append({"role": "assistant", "content": str(order_data)})
        
        # Форматируем заказ
        order_json = await makeOrderformat(message_text, chat_history)
        
        # Парсим JSON ответ от makeOrderformat
        try:
            if isinstance(order_json, str):
                # Убираем markdown блоки если есть
                json_str = order_json.strip()
                if json_str.startswith('```json'):
                    json_str = json_str[7:]  # Убираем ```json
                if json_str.endswith('```'):
                    json_str = json_str[:-3]  # Убираем ```
                json_str = json_str.strip()
                
                order_data = json.loads(json_str)
            else:
                order_data = order_json
        except json.JSONDecodeError as e:
            return f"❌ Ошибка парсинга JSON заказа: {e}\n📋 Исходный ответ: {order_json}"
            
        # Проверяем, существует ли сотрудник
        existing_employee = await search_employees(order_data.get("full_name"))
        
        if existing_employee and isinstance(existing_employee, dict):
            # Обновляем существующего сотрудника
            order_data["id"] = existing_employee.get("id")
            result = await UpdatePeople(order_data)
            
            if result and result.get("success"):
                data = result.get("data", {})
                full_name = data.get("full_name", "Неизвестно")
                position = data.get("position", "Не указана")
                phone = data.get("phone", "Не указан")
                status = data.get("status", "Неизвестно")
                employee_id = data.get("id", "Неизвестен")
                
                # Кодируем ФИО для URL
                encoded_name = urllib.parse.quote(full_name)
                search_url = f"http://labor.tetrakom-crm-miniapp.ru/safety?search_fio={encoded_name}&search_position=&search_phone=&search_status=&certificate_id=&certificate_status="
                
                response_text = f"""
✅ <b>Сотрудник успешно обновлен!</b>

👤 <b>ФИО:</b> {full_name}
💼 <b>Должность:</b> {position}
📄 <b>СНИЛС:</b> {data.get("snils", "Не указан")}
🔢 <b>ИНН:</b> {data.get("inn", "Не указан")}
📞 <b>Телефон:</b> {phone}
📅 <b>Дата рождения:</b> {data.get("birth_date", "Не указана")}
📊 <b>Статус:</b> {status}
🆔 <b>ID:</b> {employee_id}
"""
            else:
                error_msg = result.get('message', 'Неизвестная ошибка') if result else 'Ошибка обновления'
                response_text = f"❌ <b>Ошибка обновления:</b> {error_msg}"
        else:
            # Добавляем нового сотрудника
            result = await addPeople(order_data)
            
            if result and result.get("success"):
                data = result.get("data", {})
                full_name = data.get("full_name", "Неизвестно")
                position = data.get("position", "Не указана")
                phone = data.get("phone", "Не указан")
                status = data.get("status", "Неизвестно")
                employee_id = data.get("id", "Неизвестен")
                
                # Кодируем ФИО для URL
                encoded_name = urllib.parse.quote(full_name)
                search_url = f"http://labor.tetrakom-crm-miniapp.ru/safety?search_fio={encoded_name}&search_position=&search_phone=&search_status=&certificate_id=&certificate_status="
                
                response_text = f"""
🎉 <b>Сотрудник успешно добавлен!</b>

👤 <b>ФИО:</b> {full_name}
💼 <b>Должность:</b> {position}
📄 <b>СНИЛС:</b> {data.get("snils", "Не указан")}
🔢 <b>ИНН:</b> {data.get("inn", "Не указан")}
📞 <b>Телефон:</b> {phone}
📅 <b>Дата рождения:</b> {data.get("birth_date", "Не указана")}
📊 <b>Статус:</b> {status}
🆔 <b>ID:</b> {employee_id}
"""
            else:
                error_msg = result.get('message', 'Неизвестная ошибка') if result else 'Ошибка добавления'
                response_text = f"❌ <b>Ошибка добавления:</b> {error_msg}"
        
        # Добавляем результат в историю
        chat_history.append({"role": "assistant", "content": str(result)})
        
        # Отправляем уведомления
        if result and result.get("success"):
            data = result.get("data", {})
            employee_id = data.get("id")
            full_name = data.get("full_name", "")
            
            # Кодируем ФИО для URL
            encoded_name = urllib.parse.quote(full_name)
            search_url = f"http://labor.tetrakom-crm-miniapp.ru/safety?search_fio={encoded_name}&search_position=&search_phone=&search_status=&certificate_id=&certificate_status="
            
            notification_data = {
                "full_name": full_name,
                "position": data.get("position", "Не указана"),
                "snils": data.get("snils", "Не указан"),
                "inn": data.get("inn", "Не указан"),
                "phone": data.get("phone", "Не указан"),
                "birth_date": data.get("birth_date", "Не указана"),
                "status": data.get("status", "Неизвестно"),
                "employee_id": employee_id,
                "search_url": search_url
            }
            
            if result.get("message") == "Человек успешно добавлен":
                # Генерируем DOCX файл
                try:
                    # Подготавливаем данные для генерации документа
                    order_data = {
                        'employee': {
                            'full_name': data.get("full_name", ""),
                            'position': data.get("position", ""),
                            'snils': data.get("snils", ""),
                            'inn': data.get("inn", ""),
                            'phone': data.get("phone", ""),
                            'birth_date': data.get("birth_date", ""),
                            'photo': ''  # Фото не нужно для DOCX
                        }
                    }
                    
                    # Генерируем DOCX файл
                    logger.info(f"Данные для DOCX: {order_data}")
                    docx_filename = create_tetracom_document(order_data)
                    logger.info(f"DOCX файл создан: {docx_filename}")
                    logger.info(f"Тип возвращаемого значения: {type(docx_filename)}")
                    
                except Exception as e:
                    logger.error(f"Ошибка создания DOCX файла: {e}")
                    docx_filename = None
                
                # Отправляем уведомление о новом сотруднике всем подписчикам
                if notification_scheduler:
                    # Получаем всех подписчиков на этот тип уведомления
                    subscribers = notification_storage.get_subscribers(NotificationType.EMPLOYEE_REGISTERED)
                    logger.info(f"Подписчики на EMPLOYEE_REGISTERED: {subscribers}")
                    logger.info(f"Передаем source_user_id: {user_id}")
                    if subscribers:
                        # Получаем фото пользователя
                        user_photo = user_photos.get(user_id)
                        logger.info(f"Фото пользователя {user_id}: {user_photo}")
                        await notification_scheduler.send_immediate_notification_with_photo_and_docx(
                            NotificationType.EMPLOYEE_REGISTERED,
                            notification_data,
                            subscribers,
                            user_id,  # Передаем ID пользователя для получения фото из истории
                            user_photo,  # Передаем фото напрямую
                            docx_filename  # Передаем DOCX файл
                        )
            else:
                # Отправляем уведомление об обновлении всем подписчикам
                if notification_scheduler:
                    # Получаем всех подписчиков на этот тип уведомления
                    subscribers = notification_storage.get_subscribers(NotificationType.EMPLOYEE_UPDATED)
                    if subscribers:
                        # Получаем фото пользователя
                        user_photo = user_photos.get(user_id)
                        logger.info(f"Фото пользователя {user_id}: {user_photo}")
                        await notification_scheduler.send_immediate_notification_with_photo(
                            NotificationType.EMPLOYEE_UPDATED,
                            notification_data,
                            subscribers,
                            user_id,  # Передаем ID пользователя для получения фото из истории
                            user_photo  # Передаем фото напрямую
                        )
        
        # Очищаем историю чата после успешного завершения
        user_chat_histories[user_id] = []
        
        return response_text
        
    except Exception as e:
        logger.error(f"Ошибка при обработке заказа: {e}")
        return f"❌ Произошла ошибка при обработке заказа: {e}"

@bot.message_handler(commands=['start'])
async def start_command(message: Message):
    """Обработчик команды /start"""
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    welcome_text = """
🤖 Добро пожаловать в бот для обработки заказов на обучение!

📝 Для создания заказа отправьте данные сотрудника в любом формате:
• ФИО
• Должность  
• Телефон
• СНИЛС
• Дата рождения
• ИНН (не обязательно)

💡 Вы можете отправлять данные частями - бот соберет их в один заказ.

🔍 Команды:
/start - Начать работу
/help - Помощь
/clear - Очистить историю чата
/notifications - Управление уведомлениями
/subscribe - Подписаться на уведомления
/unsubscribe - Отписаться от уведомлений
/stats - Статистика уведомлений
"""
    await bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['help'])
async def help_command(message: Message):
    """Обработчик команды /help"""
    help_text = """
📋 Помощь по использованию бота:

🤖 <b>Бот понимает 2 типа запросов:</b>

📋 <b>1. Создание заявки на обучение:</b>
• "Иванов Иван, монтажник, нужно обучить на высоту"
• "Создай заявку для Петрова на ПБО"
• "Сидоров Сидор, +7-999-123-45-67, СНИЛС 123-456-789, обучить на леса"

🔍 <b>2. Поиск информации о сотруднике:</b>
• "Иванов Иван"
• "Покажи информацию о Петрове"
• "Найди Сидорова"

📝 <b>Примеры сообщений для заявок:</b>
• "Иванов Иван Иванович, Менеджер, +7-999-123-45-67"
• "СНИЛС: 123-456-789 01, Дата: 01.01.1990"
• "ИНН: 1234567890"

🔍 <b>Команды:</b>
/start - Начать работу
/help - Помощь  
/clear - Очистить историю чата
/notifications - Управление уведомлениями
"""
    await bot.reply_to(message, help_text, parse_mode='HTML')

@bot.message_handler(commands=['clear'])
async def clear_command(message: Message):
    """Обработчик команды /clear"""
    user_id = message.from_user.id
    user_chat_histories[user_id] = []
    await bot.reply_to(message, "🧹 История чата очищена. Можете начать новый заказ.")

@bot.message_handler(commands=['notifications'])
async def notifications_command(message: Message):
    """Управление уведомлениями"""
    user_id = str(message.from_user.id)
    
    # Получаем текущие подписки
    subscriptions = notification_storage.get_user_subscriptions(user_id)
    
    if not subscriptions:
        response = """
🔕 <b>Управление уведомлениями</b>

Вы не подписаны ни на какие уведомления.

Используйте /subscribe для подписки на уведомления.
"""
    else:
        response = f"""
🔔 <b>Ваши подписки на уведомления:</b>

"""
        for sub in subscriptions:
            response += f"• {sub}\n"
        
        response += "\nИспользуйте /unsubscribe для отписки."
    
    await bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['subscribe'])
async def subscribe_command(message: Message):
    """Подписаться на уведомления"""
    user_id = str(message.from_user.id)
    
    # Подписываем на основные типы уведомлений
    notification_types = [
        NotificationType.EMPLOYEE_REGISTERED,
        NotificationType.EMPLOYEE_UPDATED,
        NotificationType.CERTIFICATE_EXPIRING,
        NotificationType.CERTIFICATE_EXPIRED
    ]
    
    notification_storage.subscribe_user(user_id, notification_types)
    
    response = """
✅ <b>Вы подписаны на уведомления!</b>

Теперь вы будете получать уведомления о:
• Новых сотрудниках
• Обновлениях данных сотрудников
• Истекающих сертификатах
• Просроченных сертификатах

Используйте /unsubscribe для отписки.
"""
    await bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['unsubscribe'])
async def unsubscribe_command(message: Message):
    """Отписаться от уведомлений"""
    user_id = str(message.from_user.id)
    
    notification_storage.unsubscribe_user(user_id)
    
    response = """
❌ <b>Вы отписаны от уведомлений</b>

Вы больше не будете получать уведомления.

Используйте /subscribe для повторной подписки.
"""
    await bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(commands=['stats'])
async def stats_command(message: Message):
    """Статистика уведомлений"""
    user_id = str(message.from_user.id)
    
    # Получаем статистику за последние 24 часа
    stats = notification_storage.get_notification_stats(24)
    
    response = f"""
📊 <b>Статистика уведомлений (за 24 часа)</b>

📤 <b>Отправлено:</b> {stats['total_sent']}
✅ <b>Успешно:</b> {stats['successful']}
❌ <b>Ошибок:</b> {stats['failed']}
📈 <b>Успешность:</b> {stats['success_rate']:.1f}%

🔔 <b>Ваши подписки:</b>
"""
    
    subscriptions = notification_storage.get_user_subscriptions(user_id)
    if subscriptions:
        for sub in subscriptions:
            response += f"• {sub}\n"
    else:
        response += "Нет активных подписок"
    
    await bot.reply_to(message, response, parse_mode='HTML')

@bot.message_handler(content_types=['text', 'photo'])
async def handle_message(message: Message):
    """Обработчик текстовых сообщений и сообщений с фото"""
    user_id = message.from_user.id
    
    # Проверяем, есть ли текст в сообщении или подписи к фото
    if message.text:
        message_text = message.text
        logger.info(f"Получено текстовое сообщение от пользователя {user_id}: {message_text[:50]}...")
    elif message.caption:
        message_text = message.caption
        logger.info(f"Получено сообщение с фото и текстом от пользователя {user_id}: {message_text[:50]}...")
        
        # Сохраняем фото из сообщения
        if message.photo:
            # Берем фото наибольшего размера
            photo = max(message.photo, key=lambda x: x.file_size)
            user_photos[user_id] = photo.file_id
            logger.info(f"Фото сохранено для пользователя {user_id}: {photo.file_id}")
    else:
        # Если это фото без текста - игнорируем
        logger.info(f"Получено фото без текста от пользователя {user_id} - игнорируем")
        return
    
    # Если текст пустой - игнорируем
    if not message_text or not message_text.strip():
        logger.info(f"Пустое сообщение от пользователя {user_id} - игнорируем")
        return
    
    # Показываем, что бот печатает
    await bot.send_chat_action(message.chat.id, 'typing')
    
    # Получаем историю чата для этого пользователя
    chat_history = user_chat_histories.get(user_id, [])
    
    # Определяем намерение пользователя через CEO диспетчер
    logger.info(f"Определяем намерение для сообщения: {message_text[:50]}...")
    ceo_result = await ceo_dispatcher(message_text, chat_history)
    
    if ceo_result.get("type") == "error":
        response = ceo_result.get("message", "❌ Ошибка определения намерения")
    else:
        intent = ceo_result.get("intent")
        confidence = ceo_result.get("confidence", 0.5)
        employee_name = ceo_result.get("employee_name", "")
        
        logger.info(f"Намерение: {intent}, уверенность: {confidence}, сотрудник: {employee_name}")
        
        if intent == "search_info":
            # Пользователь хочет просто посмотреть информацию
            logger.info(f"Обрабатываем запрос на поиск информации для: {employee_name}")
            response = await handle_search_request(employee_name, user_id)
            
        elif intent == "create_order":
            # Пользователь хочет создать заявку на обучение
            logger.info(f"Обрабатываем запрос на создание заявки для: {employee_name}")
            if chat_history:
                await bot.reply_to(message, f"📝 Продолжаю обработку заказа... (сообщений в истории: {len(chat_history)})")
            response = await process_order(user_id, message_text)
            
        elif intent == "unclear":
            # Намерение неясно, просим уточнить
            response = """🤔 <b>Не понял ваше намерение</b>

Пожалуйста, уточните, что вы хотите:

📋 <b>Создать заявку на обучение:</b>
• "Иванов Иван, монтажник, нужно обучить на высоту"
• "Создай заявку для Петрова на ПБО"

🔍 <b>Посмотреть информацию:</b>
• "Иванов Иван"
• "Покажи информацию о Петрове"
• "Найди Сидорова"

Или используйте команды:
/help - помощь
/start - начать заново"""
        else:
            # Неизвестное намерение
            response = "❌ Не удалось определить ваше намерение. Попробуйте еще раз или используйте /help"
    
    # Отправляем ответ с HTML разметкой
    await bot.reply_to(message, response, parse_mode='HTML')

async def main():
    """Основная функция запуска бота"""
    global notification_scheduler
    
    logger.info("Запуск Telegram бота...")
    
    # Проверяем наличие токена
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")
        return
    
    logger.info(f"Токен бота: {token[:10]}...")
    
    try:
        # Получаем информацию о боте
        bot_info = await bot.get_me()
        logger.info(f"Бот запущен: @{bot_info.username} ({bot_info.first_name})")
        
        # Инициализируем планировщик уведомлений
        notification_scheduler = NotificationScheduler(bot, notification_storage)
        await notification_scheduler.start()
        logger.info("Планировщик уведомлений запущен")
        
        # Запускаем бота
        logger.info("Ожидание сообщений...")
        await bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        # Останавливаем планировщик при завершении
        if notification_scheduler:
            await notification_scheduler.stop()

if __name__ == "__main__":
    asyncio.run(main())
