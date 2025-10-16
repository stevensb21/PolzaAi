from api_settings import DATE_CONVERSION_PRIORITY, ORDER_FORMAT_PRIORITY
from ai_request import make_api_request_with_fallback


async def convert_date(date):
    try:
        response, used_client, used_model = await make_api_request_with_fallback(
            priority_list=DATE_CONVERSION_PRIORITY,
            messages=[
                {"role": "system", "content": """

                    Ты конвертер дат, ты умеешь конвертировать дату из любого формата в sql формат yyyy-mm-dd
                    Возвращаешь только дату в sql формате yyyy-mm-dd в виде строки без кавычек

                """},
                {"role": "user", "content": date},   
            ],

            temperature=0.1,
            task_name="Конвертация даты"
        )
        
        if not response:
            print(f"❌ Не удалось конвертировать дату, возвращаем исходную: {date}")
            return date
            
        # Убираем кавычки если они есть
        result = response.choices[0].message.content.strip().strip('"').strip("'")
        print(f"📊 Использован: {used_client} / {used_model}")
        print(f"✅ Дата сконвертирована: {date} → {result}")
        return result
    except Exception as e:
        print(f"Ошибка при конвертации даты: {e}")
        return date



async def makeOrderformat(order, chat_history=None):
    messages_with_system = [
        {"role": "system", "content": """Ты форматируешь заказ для обучения сотрудника.

ВАЖНО: Анализируй ВСЮ историю чата + текущее сообщение!
Данные могут быть разбросаны по нескольким сообщениям.

ИЗ ВСЕХ СООБЩЕНИЙ извлекай:
- full_name - ФИО сотрудника (любой формат)
- position - должность сотрудника (любая профессия)
- phone - телефон сотрудника (любой формат)
- snils - СНИЛС сотрудника (XXX-XXX-XXX XX или XXXXXXXXXX)
- inn - ИНН сотрудника (не обязательно)
- birth_date - дата рождения (любой формат, конвертируй в yyyy-mm-dd)

ПРАВИЛА:
1. Объединяй данные из всех сообщений в истории
2. Если данные есть в разных сообщениях - используй их
3. Если дата в формате дд.мм.гггг - конвертируй в yyyy-mm-dd
4. Если каких-то данных нет - оставляй пустую строку ""

Возвращай JSON в формате:
{
    "full_name": "string",
    "position": "string", 
    "phone": "string",
    "snils": "string",
    "inn": "string",
    "birth_date": "string"
}"""},
        {"role": "user", "content": f"Текущее сообщение: {order}"}
    ]
    
    if chat_history:
        messages_with_system.append({"role": "user", "content": f"История чата: {chat_history}"})

    response, used_client, used_model = await make_api_request_with_fallback(
            priority_list=ORDER_FORMAT_PRIORITY,
            messages=messages_with_system,
            temperature=0.1,
            task_name="Форматирование заказа"
        )
    if not response:
        print(f"❌ Не удалось сформировать формат заказа, возвращаем исходный заказ: {order}")
        return order
    result = response.choices[0].message.content.strip().strip('"').strip("'")
    print(f"📊 Использован: {used_client} / {used_model}")
    print(f"✅ Формат заказа сформирован: {order} → {result}")
    return result

async def validateOrder(order, chat_history):
    messages_with_system = [
        {"role": "system", "content": """Ты контроллер заказа. ВАЖНО: Это диалог с пользователем, который может вводить данные частями!

ПРАВИЛА АНАЛИЗА:
1. Собери ВСЕ данные из истории чата + текущего сообщения
2. Это ОДИН заказ, данные могут быть в разных сообщениях
3. Если в истории есть ФИО, а в текущем сообщении должность - это ОДИН человек!

ПРИМЕР:
- История: "Иванов Иван Иванович, СНИЛС: 123-456-789 01, 01.01.1990"
- Текущее: "Менеджер, +7-999-123-45-67"
- РЕЗУЛЬТАТ: Все данные найдены! (ФИО из истории + должность и телефон из текущего)

ПРИМЕР 2:
- История: "Егоров Андрей Федорович, СНИЛС: 199-010-000-00, +79631218121, Прораб"
- Текущее: "16.09.1994"
- РЕЗУЛЬТАТ: Все данные найдены! (ФИО, СНИЛС, телефон, должность из истории + дата из текущего)

ИЩИ В ВСЕХ СООБЩЕНИЯХ:
- ФИО (любой формат обязательно)
- Должность (любая профессия обязательно)
- Телефон (любой формат: +7, 8, без пробелов обязательно)
- СНИЛС (XXX-XXX-XXX XX или XXXXXXXXXX обязательно)
- Дата рождения (любой формат обязательно: 16.09.1994, 16/09/1994, 16-09-1994, 16.09.94 и т.д.)
- ИНН (не обязательно)

Если ВСЕ найдено - возвращай: {"success": true, "message": "Все данные найдены"}
Если чего-то нет - возвращай: {"error": "missing_data", "message": "Отсутствует: [что именно]"}"""},
        {"role": "user", "content": f"Текущее сообщение: {order}"},
        {"role": "user", "content": f"История чата: {chat_history}"}
    ]

    response, used_client, used_model = await make_api_request_with_fallback(
            priority_list=ORDER_FORMAT_PRIORITY,
            messages=messages_with_system,
            task_name="Проверка заказа"
        )
    if not response:
        print(f"❌ Не удалось проверить данные в заказе, возвращаем исходный заказ: {order}")
        return order
    result = response.choices[0].message.content.strip().strip('"').strip("'")
    print(f"📊 Использован: {used_client} / {used_model}")
    print(f"✅ Данные в заказе проверены: {order} → {result}")
    return result

