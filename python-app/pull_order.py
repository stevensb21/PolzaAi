import os
import json
import asyncio
import requests
from openai import AsyncOpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta
from get_jsonAPIai import call_external_api, sort_employee

# Инициализация клиента OpenAI с обработкой ошибок
try:
    client = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",
        api_key="ak_XfE3O425uoSp2I3xiLDJXmOX7xGLF3BZ1uXUImXxnpo"
    )
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать OpenAI клиент: {e}")
    client = None

BASE_URL = "http://80.87.193.89:8081"

chat_history = [
    {
        "role": "system",
        "content": (
            "Ты — вежливый и внимательный ассистент. Общайся как человек, "+
            "держи краткий и точный стиль."
        ),
    }
]

tools = [
    {
        "type": "function",
        "function": {
            "name": "call_external_api",
            "description": "Получает JSON со всеми сотрудниками",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "sort_employee",
            "description": "Выбирает сотрудников из JSON",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee": {"type": "string", "description": "Фильтр для выбора сотрудников"}
                },
                "required": ["employee"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "makeOrderFormat",
            "description": "Формирует заявку в JSON формате",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_name": {"type": "string", "description": "Имя сотрудника"},
                    "certificate_name": {"type": "array", "items": {"type": "string"}, "description": "Названия удостоверений"}
                },
                "required": ["employee_name", "certificate_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "clarification",
            "description": "Уточняет данные у пользователя",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_data": {"type": "object", "description": "Данные заказа для уточнения"}
                },
                "required": ["order_data"]
            }
        }
    }
]

async def makeOrderFormat(employee_name, certificate_name):
    """Форматирует заявку в JSON формате"""
    # Сначала получаем данные сотрудника
    json_people = await sort_employee(employee_name)
    
    print(f"DEBUG: sort_employee вернул: {type(json_people)}")
    print(f"DEBUG: Содержимое json_people: {json_people}")
    
    # Проверяем, нужно ли парсить JSON
    if isinstance(json_people, str):
        try:
            json_people = json.loads(json_people)
            print(f"DEBUG: После парсинга JSON: {type(json_people)}")
        except json.JSONDecodeError:
            print(f"❌ Ошибка парсинга JSON от sort_employee: {json_people}")
            return None
    
    # Проверяем на ошибку API
    if isinstance(json_people, dict) and 'error' in json_people:
        print(f"❌ Ошибка API: {json_people['error']}")
        return None
    
    # Initialize all fields to "null"
    employee_full_name = employee_name
    snils = "null"
    inn = "null"
    position = "null"
    birth_date = "null"
    phone = "null"
    

    
    if isinstance(json_people, dict) and 'data' in json_people:
        data = json_people['data']
        print(f"DEBUG: data type: {type(data)}, length: {len(data) if isinstance(data, list) else 'not list'}")
        if isinstance(data, list) and len(data) > 0:
            employee_full_name = data[0].get('full_name', employee_name)
            snils = data[0].get('snils', "null")
            inn = data[0].get('inn', "null")
            position = data[0].get('position', "null")
            birth_date = data[0].get('birth_date', "null")
            phone = data[0].get('phone', "null")
            print(f"DEBUG: Extracted from data[0]: {employee_full_name}, {snils}, {inn}")
    elif isinstance(json_people, dict) and 'full_name' in json_people:
        # json_people is a dict with employee data directly
        print(f"DEBUG: json_people is employee data dict")
        employee_full_name = json_people.get('full_name', employee_name)
        snils = json_people.get('snils', "null")
        inn = json_people.get('inn', "null")
        position = json_people.get('position', "null")
        birth_date = json_people.get('birth_date', "null")
        phone = json_people.get('phone', "null")
        print(f"DEBUG: Extracted from json_people: {employee_full_name}, {snils}, {inn}")
    elif isinstance(json_people, list) and len(json_people) > 0:
        print(f"DEBUG: json_people is list, length: {len(json_people)}")
        if isinstance(json_people[0], dict):
            employee_full_name = json_people[0].get('full_name', employee_name)
            snils = json_people[0].get('snils', "null")
            inn = json_people[0].get('inn', "null")
            position = json_people[0].get('position', "null")
            birth_date = json_people[0].get('birth_date', "null")
            phone = json_people[0].get('phone', "null")
            print(f"DEBUG: Extracted from json_people[0]: {employee_full_name}, {snils}, {inn}")
    else:
        print(f"DEBUG: No matching condition found")
    
    # Проверяем полноту данных
    required_fields = [snils, inn, position, birth_date, phone]
    has_missing_data = any(field is None or field == "null" for field in required_fields)
    
    # Определяем тип на основе полноты данных
    order_type = "clarification" if has_missing_data else "readyorder"
    
    # Формируем JSON объект
    order_json = {
        "type": order_type,
        "employee": {
            "full_name": employee_full_name,
            "snils": snils,
            "inn": inn,
            "position": position,
            "birth_date": birth_date,
            "phone": phone
        },
        "certificate": certificate_name,
        "status": "pending"
    }
    
    return order_json

async def clarification(messages, order_json):
    """Уточняет данные у пользователя"""
   
    response = await client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {"role": "system", "content": f"""Ты — помощник для уточнения данных у пользователя.
                    Вот данные для заказа: {json.dumps(order_json, indent=4, ensure_ascii=False)}

                    Твоя задача — уточнить данные у пользователя.
                    Проверь все ли данные в employee есть и если нет, уточни у пользователя запиши сообщение в поле message.
                    Если все данные есть, верни order_json, но измени в нем type на "readyorder".
                    Если данные неполные, верни order_json, но измени в нем type на "clarification".

                    ОБЯЗАТЕЛЬНО: возвращай только order_json, ничего больше и в формате JSON."""},
            {"role": "user", "content": f"Уточни данные у пользователя: {messages}"}
        ]
    )
    
    if not response.choices or not response.choices[0].message:
        return "❌ Ошибка: получен пустой ответ от OpenAI API clarification"
    
    msg = response.choices[0].message
    print(f"Ответ ИИ clarification: {msg.content}")
    
    return msg.content


def format_message(message):
    """Форматирует сообщение"""
    # Форматируем дату рождения
    birth_date = message.get("employee", {}).get("birth_date")
    if birth_date and birth_date != "null":
        try:
            # Если дата в формате ISO (1981-01-01T00:00:00.000000Z)
            if "T" in str(birth_date):
                from datetime import datetime
                date_obj = datetime.fromisoformat(str(birth_date).replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%d.%m.%Y")
            else:
                formatted_date = str(birth_date)
        except:
            formatted_date = str(birth_date)
    else:
        formatted_date = "не указана"
    
    return {
        "message": f""" Заказ оформлен и отправлен в базу данных \n для {message.get("employee", {}).get("full_name")} \n с удостоверением {message.get("certificate")}
        \n СНИЛС: {message.get("employee", {}).get("snils")} \n ИНН: {message.get("employee", {}).get("inn")} \n Должность: {message.get("employee", {}).get("position")} \n Дата рождения: {formatted_date} \n Телефон: {message.get("employee", {}).get("phone")} """
    }

async def run_dispatcher(messages):
    """Запускает диспетчер на основе истории чата"""
    try:
        if not client:
            return "❌ Ошибка: OpenAI клиент не инициализирован"
            
        print(f"🤖 Отправляю запрос к ИИ (сообщений: {len(messages)})")
        
        
        

        
        # Добавляем системное сообщение в начало истории
        messages_with_system = [
            {"role": "system", "content": """
            Ты — помощник для заказа удостоверений.

                У тебя есть 2 функции:
                1. clarification(order_data) — уточнение данных заказа
                2. makeOrderFormat(employee_name, certificate_name) — создание нового заказа

                Правила:
                - Если пользователь хочет СДЕЛАТЬ НОВЫЙ ЗАКАЗ → вызывай makeOrderFormat().
                • Обязательно верни JSON в формате:
                    {
                    \"employee_name\": \"ФИО сотрудника\",
                    \"certificate_name\": [\"Название удостоверения\"]
                    }
                • Всегда используй массив для certificate_name, даже если удостоверение одно.

                - Если пользователь уточняет детали уже существующего заказа (например: \"а ещё добавь ПБО\", \"не Егоров, а Егоров Иван\", \"нужно 2 удостоверения\") → вызывай clarification().
                • В clarification() всегда передавай:
                    - messages → текст уточнения пользователя
                    - order_data → JSON заказа, который нужно уточнить

                - Если сообщение НЕ относится к заказу и не содержит ни уточнения, ни создания → отвечай по контексту, но НЕ вызывай никакую функцию.

                Примеры:
                Пользователь: \"заказать Егорову ЭБ\"
                Ответ: makeOrderFormat({\"employee_name\": \"Егоров\", \"certificate_name\": [\"ЭБ\"]})

                Пользователь: \"и ещё добавь БСИЗ\"
                Ответ: clarification(messages=\"и ещё добавь БСИЗ\", order_data={\"employee_name\": \"Егоров\", \"certificate_name\": [\"ЭБ\"]})

                Пользователь: \"нужно заказать ВИТР для Иванова\"
                Ответ: makeOrderFormat({\"employee_name\": \"Иванов\", \"certificate_name\": [\"ВИТР\"]})

                Пользователь: \"не Егоров, а Егоров Иван Иванович\"
                Ответ: clarification(messages=\"не Егоров, а Егоров Иван Иванович\", order_data={\"employee_name\": \"Егоров\", \"certificate_name\": [\"ЭБ\"]})
            """}
        ]
        
        # Добавляем всю историю чата
        messages_with_system.extend(messages)
        
        print(f"DEBUG: Отправляю {len(messages_with_system)} сообщений в API")
        print(f"DEBUG: Первое сообщение: {messages_with_system[0]}")
        print(f"DEBUG: Последнее сообщение: {messages_with_system[-1]}")
        
        
        response = await client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=messages_with_system,
                tools=tools,
                tool_choice="auto"
            )
        

        if not response.choices or not response.choices[0].message:
            return "❌ Ошибка: получен пустой ответ от OpenAI API"

        msg = response.choices[0].message
        print(f"Ответ ИИ: {msg.content}")

        # Проверяем, хочет ли ИИ вызвать инструменты
        if msg.tool_calls:
            print(f"🔧 ИИ хочет вызвать инструменты: {len(msg.tool_calls)}")
            
            # Обрабатываем каждый tool call
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                print(f"🔧 Вызываю инструмент: {tool_name}")
                
                if tool_name == "call_external_api":
                    # Получаем всех сотрудников
                    result = call_external_api()
                    return f"📋 Список всех сотрудников:\n{result}"
                    
                elif tool_name == "sort_employee":
                    # Ищем конкретного сотрудника
                    try:
                        args = json.loads(tool_call.function.arguments)
                        employee_filter = args.get("employee", "")
                        if employee_filter:
                            result = await sort_employee(employee_filter)
                            return f"🔍 Результат поиска '{employee_filter}':\n{result}"
                        else:
                            return "❌ Ошибка: не указан параметр employee для поиска"
                    except json.JSONDecodeError:
                        return "❌ Ошибка: неверные аргументы для sort_employee"
                        
                elif tool_name == "makeOrderFormat":
                    # Сформируем заявку
                    try:
                        args = json.loads(tool_call.function.arguments)
                        employee_name = args.get("employee_name", "")
                        certificate_name = args.get("certificate_name", "")
                        print(f"DEBUG: employee_name: {employee_name}, certificate_name: {certificate_name}")
                        result = await makeOrderFormat(employee_name, certificate_name)
                        if result is None:
                            return "❌ Ошибка: не удалось сформировать заявку"
                        if result.get("type") == "clarification":
                            result = await clarification(messages, result)
                            if isinstance(result, str):
                                try:
                                    parsed_result = json.loads(result)
                                    if parsed_result.get("type") == "clarification":
                                        return parsed_result.get("message")
                                    else:
                                        return format_message(parsed_result).get("message")
                                except json.JSONDecodeError:
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"
                            else:
                                if result.get("type") == "clarification":
                                    return result.get("message")
                                else:
                                    return format_message(result).get("message")
                        else:
                            return f"🔍 Сформированная заявка:\n{result}"
                    except json.JSONDecodeError:
                        return "❌ Ошибка: неверные аргументы для makeOrderFormat"
                        
                elif tool_name == "clarification":
                    # Уточняем данные
                    try:
                        args = json.loads(tool_call.function.arguments)
                        order_data = args.get("order_data", {})
                        if order_data:
                            result = await clarification(messages, order_data)
                            # Парсим результат clarification если это строка
                            if isinstance(result, str):
                                try:
                                    parsed_result = json.loads(result)
                                    if parsed_result.get("type") == "clarification":
                                        return parsed_result.get("message")
                                    else:
                                        return format_message(parsed_result).get("message")
                                except json.JSONDecodeError:
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"
                            else:
                                if result.get("type") == "clarification":
                                    return result.get("message")
                                else:
                                    return format_message(result).get("message")
                        else:
                            return "❌ Ошибка: не указаны данные заказа для уточнения"
                    except json.JSONDecodeError:
                        return "❌ Ошибка: неверные аргументы для clarification"
                        
                else:
                    return f"❌ Неизвестный инструмент: {tool_name}"
        
        # Если не было вызова функций, возвращаем обычный ответ
        if not msg.content:
            return "❌ Ошибка: ИИ не предоставил ответ"
        
        try:
            # Парсим JSON ответ от ИИ
            response_data = json.loads(msg.content)
            
            # Проверяем, является ли это уточнением данных
            if response_data.get("type") == "clarification":
                # Это уточнение данных, возвращаем сообщение пользователю
                message = response_data.get("message")
                if not message and "employee" in response_data:
                    message = response_data["employee"].get("message", "Нужно уточнить данные")
                return message or "Нужно уточнить данные"
            elif response_data.get("type") == "readyorder":
                # Заказ готов, возвращаем форматированное сообщение
                return f"🔍 Сформированная заявка:\n{json.dumps(response_data, indent=4, ensure_ascii=False)}"
            
            # Если это не уточнение, проверяем на новый заказ
            employee_name = response_data.get("employee_name")
            certificate_name = response_data.get("certificate_name")
            
            if employee_name:
                json_people = await sort_employee(employee_name)
                
                # Парсим JSON если это строка
                if isinstance(json_people, str):
                    try:
                        json_people = json.loads(json_people)
                    except json.JSONDecodeError:
                        pass
                
                # Проверяем что есть данные сотрудника
                if not json_people or (isinstance(json_people, list) and len(json_people) == 0):
                    return f"❌ Сотрудник '{employee_name}' не найден в базе данных"
                
                order = await makeOrderFormat(employee_name, certificate_name)
                
                if order is None:
                    return "❌ Ошибка: не удалось сформировать заявку"
                
                # Если нужна уточнение данных, возвращаем сообщение пользователю
                if order.get("type") == "clarification":
                    clarification_result = await clarification(messages, order)
                    # Парсим результат clarification если это строка
                    if isinstance(clarification_result, str):
                        try:
                            parsed_result = json.loads(clarification_result)
                            return parsed_result.get("message", "Нужно уточнить данные")
                        except json.JSONDecodeError:
                            return f"❌ Ошибка парсинга JSON от clarification: {clarification_result}"
                    else:
                        return clarification_result.get("message", "Нужно уточнить данные")
                
                # Если заказ готов, возвращаем форматированное сообщение
                if order.get("type") == "readyorder":
                    return f"🔍 Сформированная заявка:\n{json.dumps(order, indent=4, ensure_ascii=False)}"
                else:
                    return order
            else:
                return "❌ Ошибка: не удалось извлечь ФИО сотрудника"
                
        except json.JSONDecodeError as e:
            return f"❌ Ошибка парсинга JSON: {str(e)}\nОтвет ИИ: {msg.content}"
        except Exception as e:
            return f"❌ Ошибка обработки данных: {str(e)}"
        
    except Exception as e:
        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в run_dispatcher: {str(e)}"
        print(error_msg)
        return error_msg


async def main() -> None:
    """Главная функция с надежной обработкой ошибок"""
    print("Контекстный чат запущен. Команды: /reset — очистить историю, /exit — выход.")
    
    global chat_history
    
    while True:
        try:
            user_input = input("👤 Вы: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ["/exit", "выход", "quit", "exit"]:
                print("До связи!")
                break

            if user_input.lower() in ["/reset", "reset"]:
                # Сохраняем только системное сообщение
                chat_history = chat_history[:1]
                print("История очищена.")
                continue

            # Добавляем сообщение пользователя в историю
            chat_history.append({"role": "user", "content": user_input})
            
            # Ограничиваем размер истории
            if len(chat_history) > 20:
                chat_history = [chat_history[0]] + chat_history[-19:]

            try:
                # Отправляем всю историю в диспетчер
                ai_text = await run_dispatcher(chat_history)
                
                # Добавляем ответ ассистента в историю
                chat_history.append({"role": "assistant", "content": ai_text})
                
                # Проверяем, является ли ответ JSON объектом
                if isinstance(ai_text, dict):
                    print("🤖 ИИ:\n" + json.dumps(ai_text, indent=4, ensure_ascii=False))
                else:
                    print("🤖 ИИ:\n" + ai_text)
            except Exception as e:
                error_msg = f"❌ Ошибка при обработке запроса: {str(e)}"
                print(error_msg)
                # Добавляем ошибку в историю, чтобы ИИ знал о проблеме
                chat_history.append({"role": "assistant", "content": error_msg})
                
        except KeyboardInterrupt:
            print("\n\n👋 Прерывание пользователем. До свидания!")
            break
        except Exception as e:
            print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в главном цикле: {str(e)}")
            # Пытаемся продолжить работу
            continue

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при запуске: {str(e)}")
