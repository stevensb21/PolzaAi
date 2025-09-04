import os
import json
import asyncio
import requests
from openai import AsyncOpenAI
from dotenv import load_dotenv
from datetime import datetime
from dateutil.relativedelta import relativedelta

load_dotenv()




# Инициализация клиента OpenAI с обработкой ошибок
try:
    client = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",
        api_key=os.getenv("POLZA_AI_TOKEN")
    )
except Exception as e:
    print(f"❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось инициализировать OpenAI клиент: {e}")
    client = None

BASE_URL = "http://80.87.193.89:8081"


# Базовый контекст — сюда можно добавлять справочные данные/переменные
# CONTEXT = {
#     "users": {
#         "лариса": {
#             "telegram_id": "8316311496",
#             "alias": ["лариса", "лариса из отдела", "лариса менеджер"],
#         }
#     },
#     "endpoints": {
#         "people_list": "http://80.87.193.89:8081/api/people",
#         "people_data": "http://80.87.193.89:8001/data"
#     },
#     "instructions": [
#         "Отвечай по-русски.",
#         "Помни контекст диалога и ранее упомянутые факты.",
#         "Если собеседник говорит о Ларисе, знай, что это telegram-пользователь с id:8316311496.",
#         "Если просит что-то повторить или уточнить — делай это кратко и по делу.",
#     ]
# }

# История чата — для сохранения контекста
chat_history = [
    {
        "role": "system",
        "content": (
            "Ты — вежливый и внимательный ассистент. Общайся как человек, "+
            "держи краткий и точный стиль. У тебя есть вспомогательный контекст: "
            # + json.dumps(CONTEXT, ensure_ascii=False)
        ),
    }
]

def format_employee_info(employee_json):
    """Форматирует информацию о сотруднике с надежной обработкой ошибок"""
    try:
        # если пришла строка — пробуем распарсить
        if isinstance(employee_json, str):
            try:
                employee_json = json.loads(employee_json)
            except json.JSONDecodeError as e:
                return f"❌ Ошибка парсинга JSON в format_employee_info: {str(e)}\nПолученная строка: {employee_json[:100]}..."

        # если есть корневой ключ data → работаем с ним
        if isinstance(employee_json, dict) and "data" in employee_json:
            employee_json = employee_json["data"]

        # Если список сотрудников
        if isinstance(employee_json, list):
            if not employee_json:
                return "⚠ Нет сотрудников по запросу"
            try:
                return "\n\n".join(format_employee_info(emp) for emp in employee_json)
            except Exception as e:
                return f"❌ Ошибка обработки списка сотрудников в format_employee_info: {str(e)}"

        # Если это сообщение вместо списка
        if isinstance(employee_json, dict) and "message" in employee_json:
            return employee_json.get("message", "нет сотрудников")

        # Один сотрудник
        if not isinstance(employee_json, dict):
            return f"❌ Неверный формат данных сотрудника в format_employee_info: ожидался dict, получен {type(employee_json)}"
        
        emp = employee_json
        all_certs = emp.get("all_certificates", [])

        lines = [
            f"Вот информация по {emp.get('full_name', 'Неизвестно')}:",
            f"Должность: {emp.get('position', 'Неизвестно')}",
            "Удостоверения:"
        ]

        def filter_certs(certs, status_code):
            """Фильтрует удостоверения по статусу с надежной обработкой ошибок"""
            try:
                result = []
                if not isinstance(certs, list):
                    return result
                    
                for cert in certs:
                    if isinstance(cert, dict):
                        assigned_data = cert.get("assigned_data")
                        # Если assigned_data is None, значит удостоверение не выдано (статус 1 - отсутствует)
                        if assigned_data is None and status_code == 1:
                            result.append(cert)
                        elif isinstance(assigned_data, dict):
                            status = assigned_data.get("status")
                            if status == status_code:
                                result.append(cert)
                return result
            except Exception as e:
                print(f"❌ Ошибка фильтрации удостоверений: {str(e)}")
                return []

        def format_cert_with_date(cert, status_code):
            """Форматирует удостоверение с датой"""
            try:
                cert_name = cert.get('name', 'Неизвестно')
                assigned_data = cert.get("assigned_data")
                
                if assigned_data is None:
                    return f"❌ {cert_name}"
                
                if isinstance(assigned_data, dict):
                    # Пытаемся получить дату из assigned_data
                    assigned_date = assigned_data.get("assigned_date")
                    
                    if assigned_date:
                        try:
                            # Парсим дату
                            from datetime import datetime
                            if isinstance(assigned_date, str):
                                if "T" in assigned_date:
                                    date_obj = datetime.fromisoformat(assigned_date.replace("Z", "+00:00"))
                                else:
                                    date_obj = datetime.strptime(assigned_date, "%Y-%m-%d")
                            else:
                                date_obj = datetime.fromtimestamp(assigned_date)
                            
                            formatted_date = date_obj.strftime("%d.%m.%Y")
                            
                            if status_code == 4:  # Действует
                                return f"✅ {cert_name}: Действует до {formatted_date}"
                            elif status_code == 2:  # Просрочен
                                return f"⭕ {cert_name}: Просрочено с {formatted_date}"
                            elif status_code == 3:  # Скоро просрочится
                                return f"🟡 {cert_name}: Истекает {formatted_date}"
                            else:
                                return f"❌ {cert_name}"
                        except:
                            # Если не удалось распарсить дату, возвращаем без неё
                            if status_code == 4:
                                return f"✅ {cert_name}"
                            elif status_code == 2:
                                return f"⭕ {cert_name}"
                            elif status_code == 3:
                                return f"🟡 {cert_name}"
                            else:
                                return f"❌ {cert_name}"
                    else:
                        # Если нет дат, возвращаем без них
                        if status_code == 4:
                            return f"✅ {cert_name}"
                        elif status_code == 2:
                            return f"⭕ {cert_name}"
                        elif status_code == 3:
                            return f"🟡 {cert_name}"
                        else:
                            return f"❌ {cert_name}"
                else:
                    return f"❌ {cert_name}"
            except Exception as e:
                print(f"❌ Ошибка форматирования удостоверения: {str(e)}")
                return f"❌ {cert.get('name', 'Неизвестно')}"

        # Фильтруем удостоверения по статусам
        missing_certs = filter_certs(all_certs, 1)  # Отсутствует
        expired_certs = filter_certs(all_certs, 2)  # Просрочен
        soon_expired_certs = filter_certs(all_certs, 3)  # Скоро просрочится
        active_certs = filter_certs(all_certs, 4)  # Действует

        # Добавляем информацию об удостоверениях
        lines.append("Действующие:")
        if active_certs:
            for cert in active_certs:
                lines.append(f"  • {format_cert_with_date(cert, 4)}")
        else:
            lines.append("отсутствуют")
            
        lines.append("Скоро просрочатся:")
        if soon_expired_certs:
            for cert in soon_expired_certs:
                lines.append(f"  • {format_cert_with_date(cert, 3)}")
        else:
            lines.append("отсутствуют")
            
        lines.append("Просроченные:")
        if expired_certs:
            for cert in expired_certs:
                lines.append(f"  • {format_cert_with_date(cert, 2)}")
        else:
            lines.append("отсутствуют")
            
        lines.append("Отсутствующие:")
        if missing_certs:
            for cert in missing_certs:
                lines.append(f"  • {format_cert_with_date(cert, 1)}")
        else:
            lines.append("отсутствуют")
        print(f"✅ Форматированная информация о сотруднике: {lines}")
        return "\n".join(lines)

    except Exception as e:
        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в format_employee_info: {str(e)}"
        print(error_msg)
        return error_msg

def call_external_api():

    """Вызывает внешний API с надежной обработкой ошибок"""
    try:
        print(f"🔍 Выполняю запрос к API: {BASE_URL}/api/people")
        resp = requests.get(f"{BASE_URL}/api/people", timeout=10, proxies={"http": None, "https": None})
        
        if resp.status_code != 200:
            return {
                "error": f"API вернул статус {resp.status_code}",
                "details": f"URL: {BASE_URL}/api/people"
            }
        
        try:
            data = resp.json()
            print(f"✅ API запрос успешен, получено {len(str(data))} символов")
            return data
        except json.JSONDecodeError as e:
            return {
                "error": f"Неверный JSON от API: {str(e)}",
                "details": f"Полученный ответ: {resp.text[:200]}..."
            }
            
    except requests.exceptions.Timeout:
        return {
            "error": "Таймаут запроса к API (10 секунд)",
            "details": f"URL: {BASE_URL}/api/people"
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "error": f"Ошибка подключения к API: {str(e)}",
            "details": f"URL: {BASE_URL}/api/people"
        }
    except requests.exceptions.RequestException as e:
        return {
            "error": f"Ошибка HTTP запроса: {str(e)}",
            "details": f"URL: {BASE_URL}/api/people"
        }
    except Exception as e:
        return {
            "error": f"Неизвестная ошибка в call_external_api: {str(e)}",
            "details": f"URL: {BASE_URL}/api/people"
        }

async def sort_employee(employee):

    """Выбирает сотрудников из JSON с надежной обработкой ошибок"""
    if not client:
        return {
            "error": "OpenAI клиент не инициализирован",
            "message": "❌ Ошибка: OpenAI клиент недоступен"
        }
    
    if not employee:
        return {
            "error": "Пустой фильтр сотрудника",
            "message": "❌ Ошибка: не указан фильтр для поиска сотрудника"
        }
    
    print(f"🔍 Ищу сотрудников по фильтру: '{employee}'")
    
    # Получаем данные сотрудников
    json_employee = call_external_api()

    
    # Проверяем на ошибки API
    if isinstance(json_employee, dict) and "error" in json_employee:
        return json_employee
        
    response = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[
            {"role": "system", "content": """

                Ты — выбиратель сотрудников. Анализируй данные и возвращай только нужную информацию.
                
                Анализируй JSON с сотрудниками и возвращай только тех, кто соответствует фильтру.
                
                ВАЖНО: возвращай только JSON в таком формате:
                {
                    "data": [
                        {
                            "id": "ID_сотрудника",
                            "full_name": "ФИО сотрудника",
                            "position": "Должность",
                            "phone": "Телефон",
                            "snils": "СНИЛС",
                            "inn": "ИНН",
                            "birth_date": "Дата рождения",
                            "all_certificates": [
                                {
                                "id": 2,
                                "name": "ВИТР (ОТ)",
                                "description": Описание удостоверения,
                                "expiry_date": Дата окончания удостоверения,
                                "created_at": Дата создания удостоверения,
                                "updated_at": Дата обновления удостоверения,
                                "is_assigned": true - если удостоверение выдано, false - если не выдано,
                                "assigned_data": {
                                    "assigned_date": Дата выдачи удостоверения,
                                    "certificate_number": Номер удостоверения,
                                    "status": Статус удостоверения, 1 - Отсутствует, 2 - Просрочен, 3 - Скоро просрочится, 4 - Действует
                                    "notes": Примечания к удостоверению
                                }
                                },
                                {... и так далее}
                            }
                    }}
                    -жесткое правило:
                        - не смешивай удостоверения разных сотрудников
                        - JSON который я описал выше просто показывает и объясняет что это такое, не используй его для выбора сотрудников и в ответе
                -выбери сотрудников или сотрудника из JSON по фильтру, сотрудников по фильтру может быть несколько или один
                - если сотрудников несколько, верни список сотрудников, если один, верни объект сотрудника
                -верни полный JSON сотрудников или сотрудника, ничего не обрезай, если нет сотрудников, верни пустой JSON с сообщением "нет сотрудников"
            """},
            {"role": "user", "content": employee},
            {"role": "assistant", "content": json.dumps(json_employee)}
        ],

        max_tokens=1000000,
        temperature=0.1
    )
        
    if not response.choices or not response.choices[0].message:
        return {
            "error": "Пустой ответ от OpenAI API",
            "message": "❌ Ошибка: получен пустой ответ от ИИ"
        }
    
    result = response.choices[0].message.content
    print(f"✅ Результат поиска сотрудников: {result}")
    print(f"✅ Поиск сотрудников завершен")
    return result
        
    

tools = [

    # {
    #     "type": "function",
    #     "function": {
    #         "name": "call_external_api",
    #         "description": "Получает JSON со всеми сотрудниками",
    #         "parameters": {"type": "object", "properties": {}, "required": []}
    #     }
    # },
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
    }
]

# ==== диспетчер ====


async def search_dispatcher(messages: list):
    """Основной диспетчер с максимально надежной обработкой ошибок"""
    try:
        if not client:
            return "❌ КРИТИЧЕСКАЯ ОШИБКА: OpenAI клиент не инициализирован"
        
        if not messages or not isinstance(messages, list):
            return "❌ Ошибка: неверный формат сообщений для диспетчера"
        
        print(f"🤖 Отправляю запрос к ИИ (сообщений: {len(messages)})")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=messages,
            tools=tools
        )

        if not response.choices or not response.choices[0].message:
            return "❌ Ошибка: получен пустой ответ от OpenAI API"

        msg = response.choices[0].message

        # Если модель решила вызвать tool
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                try:
                    func_name = tool_call.function.name
                    print(f"🔧 ИИ вызывает функцию: {func_name}")         
                    # Безопасный парсинг аргументов
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError as e:
                        return f"❌ Ошибка парсинга аргументов функции {func_name}: {str(e)}"

                    if func_name == "call_external_api":
                        print("📡 Выполняю call_external_api")
                        result = call_external_api()
                        response_text = format_employee_info(result)
                    elif func_name == "sort_employee":
                        print(f"🔍 Выполняю sort_employee с аргументом: {args.get('employee', 'НЕ УКАЗАН')}")
                        result = await sort_employee(args.get("employee", ""))
                        response_text = format_employee_info(result)
                    else:
                        response_text = f"❌ Неизвестная функция: {func_name}"
                    
                    print(f"✅ Функция {func_name} выполнена успешно")
                    return response_text
                                
                except Exception as e:
                    error_msg = f"❌ Ошибка выполнения функции {func_name}: {str(e)}"
                    print(error_msg)
                    return error_msg

        # Если не было вызова функций, возвращаем обычный ответ
        if not msg.content:
            return "❌ Ошибка: ИИ не предоставил ответ"
            
        print("✅ ИИ ответил без вызова функций")
        return msg.content

    except Exception as e:
        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в search_dispatcher: {str(e)}"
        print(error_msg)
        return error_msg

async def connect_search_dispatcher(messages):
    """Запускает диспетчер на основе истории чата"""
    result = await search_dispatcher(messages)
    print(f"✅ Результат поиска сотрудников connect_search_dispatcher: {result}")
    # Анализируем результат и определяем тип
    if isinstance(result, str):
        # Если результат - строка, проверяем содержимое
        if "Вот информация" in result or "⚠ Нет сотрудников по запросу" in result:
            return {
                "type": "searchready",
                "message": result
            }
        else:
            return {
                "type": "searchclar",
                "message": result
            }
    elif isinstance(result, dict):
        # Если результат - словарь, проверяем поле type
        if result.get("type") == "searchready":
            return {
                "type": "searchready",
                "message": result.get("message", str(result))
            }
        else:
            return {
                "type": "searchclar",
                "message": result.get("message", str(result))
            }
    else:
        # По умолчанию считаем, что нужна уточнение
        return {
            "type": "searchclar",
            "message": str(result)
        }

# ==== пример запуска ====

# async def main() -> None:
#     """Главная функция с надежной обработкой ошибок"""
#     print("Контекстный чат запущен. Команды: /reset — очистить историю, /exit — выход.")
    
#     global chat_history
    
#     while True:
#         try:
#             user_input = input("👤 Вы: ").strip()
#             if not user_input:
#                 continue

#             if user_input.lower() in ["/exit", "выход", "quit", "exit"]:
#                 print("До связи!")
#                 break

#             if user_input.lower() in ["/reset", "reset"]:
#                 # Сохраняем только системное сообщение
#                 chat_history = chat_history[:1]
#                 print("История очищена.")
#                 continue

#             # Добавляем сообщение пользователя в историю
#             chat_history.append({"role": "user", "content": user_input})

#             # Ограничиваем размер истории
#             if len(chat_history) > 20:
#                 chat_history = [chat_history[0]] + chat_history[-19:]

#             try:
#                 # Отправляем всю историю в диспетчер
#                 ai_text = await search_dispatcher(chat_history)
                
#                 # Добавляем ответ ассистента в историю
#                 chat_history.append({"role": "assistant", "content": ai_text})
                
#                 print("🤖 ИИ:\n" + ai_text)
#             except Exception as e:
#                 error_msg = f"❌ Ошибка при обработке запроса: {str(e)}"
#                 print(error_msg)
#                 # Добавляем ошибку в историю, чтобы ИИ знал о проблеме
#                 chat_history.append({"role": "assistant", "content": error_msg})
                
#         except KeyboardInterrupt:
#             print("\n\n👋 Прерывание пользователем. До свидания!")
#             break
#         except Exception as e:
#             print(f"❌ КРИТИЧЕСКАЯ ОШИБКА в главном цикле: {str(e)}")
#             # Пытаемся продолжить работу
#             continue

# if __name__ == "__main__":
#     try:
#         asyncio.run(main())
#     except Exception as e:
#         print(f"❌ КРИТИЧЕСКАЯ ОШИБКА при запуске: {str(e)}")