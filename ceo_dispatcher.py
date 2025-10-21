import os
import json
import asyncio
from openai import AsyncOpenAI
from dotenv import load_dotenv
from ai_request import make_api_request_with_fallback
from api_settings import PRIORITY_MODEL

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
   - Примеры: "Иванов Иван, монтажник, нужно обучить на высоту", "Создай заявку для Петрова на ПБО"

2. **ПОИСК ИНФОРМАЦИИ** (intent: "search_info")
   - Пользователь хочет просто посмотреть информацию о сотруднике
   - Содержит только ФИО или просьбу показать информацию
   - Примеры: "Иванов Иван", "Покажи информацию о Петрове", "Найди Сидорова"

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
            priority_list=PRIORITY_MODEL,
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
        from api import search_employees
        
        # Ищем сотрудника
        employee = await search_employees(employee_name)
        
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
"""
        
        return response
        
    except Exception as e:
        return f"❌ <b>Ошибка при поиске сотрудника:</b> {e}"
