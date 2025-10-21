import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from ai_request import make_api_request_with_fallback
from api_settings import ORDER_FORMAT_PRIORITY

load_dotenv()

# Инициализация клиента OpenAI
try:
    client = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",
        api_key=os.getenv("POLZA_AI_TOKEN")
    )
except Exception as e:
    print(f"Не удалось инициализировать OpenAI клиент: {e}")
    client = None

async def ceo_dispatcher(message_text, chat_history=None):
    """
    CEO диспетчер - определяет намерение пользователя и направляет в нужную ветку
    
    Args:
        message_text: Текст сообщения пользователя
        chat_history: История чата (опционально)
    
    Returns:
        dict: Результат с типом действия и данными
    """
    if not client:
        return {
            "type": "error",
            "message": "❌ Ошибка: OpenAI клиент не инициализирован"
        }
    
    # Подготавливаем сообщения для ИИ
    messages = [
        {
            "role": "system",
            "content": """Ты — CEO диспетчер для Telegram бота по работе с сотрудниками.

Твоя задача — определить намерение пользователя и направить запрос в нужную ветку.

У тебя есть 2 типа запросов:

1. **СОЗДАНИЕ ЗАЯВКИ НА ОБУЧЕНИЕ** (intent: "create_order")
   - Пользователь хочет создать заявку на обучение сотрудника
   - Содержит данные сотрудника + просьбу об обучении
   - Примеры: "Иванов Иван, монтажник, нужно обучить на высоту", "Создай заявку для Петрова на ПБО", "Сидоров Сидор, +7-999-123-45-67, СНИЛС 123-456-789, обучить на леса"

2. **ПОИСК ИНФОРМАЦИИ** (intent: "search_info")
   - Пользователь хочет просто посмотреть информацию о сотруднике
   - Содержит только ФИО или просьбу показать информацию
   - Примеры: "Иванов Иван", "Покажи информацию о Петрове", "Найди Сидорова", "Мазитов Ильнар Раисович"

КЛЮЧЕВЫЕ ПРИЗНАКИ:
- Если сообщение содержит ТОЛЬКО ФИО (без должности, телефона, СНИЛС, ИНН, даты рождения) → это ПОИСК ИНФОРМАЦИИ
- Если сообщение содержит ФИО + дополнительные данные + просьбу об обучении → это СОЗДАНИЕ ЗАЯВКИ
- Если есть слова "покажи", "найди", "информация", "данные" → это ПОИСК ИНФОРМАЦИИ
- Если есть слова "обучить", "заявка", "создать", "нужно" + данные сотрудника → это СОЗДАНИЕ ЗАЯВКИ

ВАЖНО: Анализируй ВСЮ историю чата + текущее сообщение для понимания контекста!

Возвращай ТОЛЬКО JSON в таком формате:
{
    "intent": "create_order" или "search_info",
    "employee_name": "ФИО сотрудника",
    "message": "Оригинальное сообщение пользователя",
    "confidence": 0.95
}

Если не можешь определить намерение, используй intent: "unclear" и confidence: 0.5"""
        },
        {
            "role": "user", 
            "content": f"История чата: {json.dumps(chat_history or [], ensure_ascii=False)}\n\nТекущее сообщение: {message_text}"
        }
    ]
    
    try:
        response, used_client, used_model = await make_api_request_with_fallback(
            priority_list=ORDER_FORMAT_PRIORITY,
            messages=messages,
            temperature=0.1,
            task_name="CEO диспетчер"
        )
        
        if not response.choices or not response.choices[0].message:
            return {
                "type": "error",
                "message": "❌ Ошибка: получен пустой ответ от OpenAI API"
            }
        
        ai_response = response.choices[0].message.content
        print(f"🤖 CEO диспетчер ответ: {ai_response}")
        
        try:
            # Парсим JSON ответ от ИИ
            result = json.loads(ai_response)
            
            # Проверяем обязательные поля
            if "intent" not in result:
                return {
                    "type": "error", 
                    "message": "❌ Ошибка: ИИ не вернул тип намерения"
                }
            
            return {
                "type": "success",
                "intent": result.get("intent"),
                "employee_name": result.get("employee_name", ""),
                "message": result.get("message", message_text),
                "confidence": result.get("confidence", 0.5)
            }
            
        except json.JSONDecodeError as e:
            return {
                "type": "error",
                "message": f"❌ Ошибка парсинга JSON от CEO диспетчера: {e}\nОтвет ИИ: {ai_response}"
            }
            
    except Exception as e:
        return {
            "type": "error",
            "message": f"❌ Ошибка CEO диспетчера: {e}"
        }

async def handle_search_request(employee_name, user_id):
    """
    Обрабатывает запрос на поиск информации о сотруднике
    
    Args:
        employee_name: ФИО сотрудника для поиска
        user_id: ID пользователя
    
    Returns:
        str: Форматированный ответ с информацией о сотруднике
    """
    try:
        print(f"🔍 ===== НАЧАЛО handle_search_request =====")
        print(f"🔍 Начинаем поиск сотрудника: {employee_name}")
        from api import search_employees
        
        # Ищем сотрудника
        employee = await search_employees(employee_name)
        print(f"🔍 Результат поиска: {'найден' if employee else 'не найден'}")
        
        if not employee:
            return f"❌ <b>Сотрудник не найден</b>\n\nПо запросу '{employee_name}' ничего не найдено.\n\nПопробуйте:\n• Проверить правильность написания ФИО\n• Использовать частичное совпадение имени"
        
        # Форматируем информацию о сотруднике
        full_name = employee.get('full_name', 'Не указано')
        position = employee.get('position', 'Не указана')
        phone = employee.get('phone', 'Не указан')
        snils = employee.get('snils', 'Не указан')
        inn = employee.get('inn', 'Не указан')
        birth_date = employee.get('birth_date', 'Не указана')
        status = employee.get('status', 'Не указан')
        employee_id = employee.get('id', 'Не указан')
        certificates = employee.get('certificates', [])
        
        # Форматируем дату рождения
        if birth_date and birth_date != 'Не указана':
            try:
                if "T" in str(birth_date):
                    from datetime import datetime
                    date_obj = datetime.fromisoformat(str(birth_date).replace("Z", "+00:00"))
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                elif "." in str(birth_date) and len(str(birth_date).split(".")) == 3:
                    formatted_date = str(birth_date)
                else:
                    formatted_date = str(birth_date)
            except:
                formatted_date = str(birth_date)
        else:
            formatted_date = "Не указана"
        
        # Форматируем информацию о сертификатах
        certificates_info = await format_certificates_info(certificates)
        
        response = f"""
🔍 <b>Информация о сотруднике</b>

👤 <b>ФИО:</b> {full_name}
💼 <b>Должность:</b> {position}
📞 <b>Телефон:</b> {phone}
📄 <b>СНИЛС:</b> {snils}
🔢 <b>ИНН:</b> {inn}
📅 <b>Дата рождения:</b> {formatted_date}
📊 <b>Статус:</b> {status}
🆔 <b>ID:</b> {employee_id}

{certificates_info}
"""
        
        print(f"🔍 ===== КОНЕЦ handle_search_request =====")
        return response
        
    except Exception as e:
        print(f"🔍 ===== ОШИБКА в handle_search_request: {e} =====")
        return f"❌ <b>Ошибка при поиске сотрудника:</b> {e}"

async def format_certificates_info(certificates):
    """
    Форматирует информацию о сертификатах сотрудника
    
    Args:
        certificates: Список сертификатов
    
    Returns:
        str: Форматированная информация о сертификатах
    """
    print(f"🔍 Форматируем {len(certificates)} сертификатов")
    if not certificates:
        return "📜 <b>Удостоверения:</b> Нет действующих удостоверений"
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    expired_certificates = []
    expiring_certificates = []
    valid_certificates = []
    
    for cert in certificates:
        if not isinstance(cert, dict):
            continue
            
        cert_name = cert.get('certificate_name', 'Неизвестное удостоверение')
        cert_number = cert.get('certificate_number', 'Без номера')
        assigned_date = cert.get('assigned_date', '')
        expiry_date = cert.get('expiry_date', '')
        
        # Пропускаем сертификаты без даты истечения
        if not expiry_date or expiry_date == 'null' or expiry_date == '':
            continue
            
        try:
            # Парсим дату истечения
            if "T" in str(expiry_date):
                expiry_dt = datetime.fromisoformat(str(expiry_date).replace("Z", "+00:00"))
            else:
                expiry_dt = datetime.strptime(str(expiry_date), "%Y-%m-%d")
            
            # Определяем статус сертификата
            if expiry_dt < now:
                # Просрочен
                expired_certificates.append({
                    'name': cert_name,
                    'number': cert_number,
                    'expiry_date': expiry_dt.strftime("%d.%m.%Y"),
                    'days_overdue': (now - expiry_dt).days
                })
            elif expiry_dt <= now + timedelta(days=30):
                # Скоро истекает (в течение 30 дней)
                expiring_certificates.append({
                    'name': cert_name,
                    'number': cert_number,
                    'expiry_date': expiry_dt.strftime("%d.%m.%Y"),
                    'days_remaining': (expiry_dt - now).days
                })
            else:
                # Действует
                valid_certificates.append({
                    'name': cert_name,
                    'number': cert_number,
                    'expiry_date': expiry_dt.strftime("%d.%m.%Y"),
                    'days_remaining': (expiry_dt - now).days
                })
                
        except Exception as e:
            print(f"❌ Ошибка при обработке сертификата {cert_name}: {e}")
            continue
    
    # Формируем текст
    result = "📜 <b>Удостоверения:</b>\n"
    
    if expired_certificates:
        result += "\n❌ <b>Просроченные:</b>\n"
        for cert in expired_certificates:
            result += f"• {cert['name']} №{cert['number']} (до {cert['expiry_date']}, просрочен на {cert['days_overdue']} дн.)\n"
    
    if expiring_certificates:
        result += "\n⚠️ <b>Скоро истекают:</b>\n"
        for cert in expiring_certificates:
            result += f"• {cert['name']} №{cert['number']} (до {cert['expiry_date']}, осталось {cert['days_remaining']} дн.)\n"
    
    if valid_certificates:
        result += "\n✅ <b>Действующие:</b>\n"
        for cert in valid_certificates:
            result += f"• {cert['name']} №{cert['number']} (до {cert['expiry_date']}, осталось {cert['days_remaining']} дн.)\n"
    
    if not expired_certificates and not expiring_certificates and not valid_certificates:
        result += "Нет удостоверений с указанными датами истечения"
    
    return result
