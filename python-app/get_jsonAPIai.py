import os
import json
import asyncio
import requests
from openai import AsyncOpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta

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
                    try:
                        if not isinstance(cert, dict):
                            continue
                            
                        assigned = cert.get("assigned_data")

                        # Явно отсутствует (нет assigned_data вообще)
                        if assigned is None and status_code == 1:
                            name = cert.get("name", "Неизвестно")
                            result.append((name, None))
                            continue

                        if not isinstance(assigned, dict):
                            continue

                        if assigned.get("status") == status_code:
                            name = cert.get("name", "Неизвестно")
                            assigned_date_str = assigned.get("assigned_date")
                            expiry_years = cert.get("expiry_date")  # допустим, в годах

                            expiry_str = "Неизвестно"
                            if assigned_date_str and expiry_years:
                                try:
                                    assigned_date = datetime.strptime(assigned_date_str, "%Y-%m-%d")
                                    expiry_date = assigned_date + relativedelta(years=int(expiry_years))
                                    expiry_str = expiry_date.strftime("%d.%m.%Y")
                                except ValueError as e:
                                    expiry_str = f"Неверный формат даты: {assigned_date_str}"
                                except TypeError as e:
                                    expiry_str = f"Неверный тип года: {expiry_years}"
                                except Exception as e:
                                    expiry_str = f"Ошибка расчета даты: {str(e)}"

                            result.append((name, expiry_str))
                    except Exception as e:
                        # Пропускаем проблемное удостоверение, но продолжаем обработку
                        continue
                        
                return result
            except Exception as e:
                return [("Ошибка фильтрации", f"Ошибка: {str(e)}")]

        categories = {
            4: "Действующие",
            3: "Скоро просрочатся",
            2: "Просроченные",
            1: "Отсутствующие"
        }

        for code, label in categories.items():
            try:
                certs = filter_certs(all_certs, code)
                lines.append(f"{label}:")
                if certs:
                    for name, expiry in certs:
                        if code == 4:
                            lines.append(f"✅ {name}: Действует до {expiry}")
                        elif code == 3:
                            lines.append(f"⚠ {name}: Скоро просрочится {expiry}")
                        elif code == 2:
                            lines.append(f"⭕ {name}: Просрочено с {expiry}")
                        else:
                            lines.append(f"❌ {name}")
                else:
                    lines.append("отсутствуют")
            except Exception as e:
                lines.append(f"❌ Ошибка обработки категории '{label}': {str(e)}")

        if not all_certs:
            lines.append("(У сотрудника вообще нет удостоверений)")

        return "\n".join(lines)
        
    except Exception as e:
        return f"❌ КРИТИЧЕСКАЯ ОШИБКА в format_employee_info: {str(e)}\nТип данных: {type(employee_json)}"

def call_external_api():
    """Забирает JSON сотрудников из твоего API с надежной обработкой ошибок"""
    try:
        print(f"🔍 Выполняю запрос к API: {BASE_URL}/api/people")
        resp = requests.get(f"{BASE_URL}/api/people", timeout=10)
        
        if resp.status_code != 200:
            return {
                "error": f"API вернул статус {resp.status_code}",
                "details": f"URL: {BASE_URL}/api/people, Ответ: {resp.text[:200]}..."
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
                Ты — выбиратель сотрудников.
                -вызови call_external_api
                    Структура JSON который ты получил по call_external_api:
                        "data": [
                            {
                            "id": 1,
                            "full_name": Полное имя сотрудника,
                            "phone": номер телефона сотрудника,
                            "snils": СНИЛС сотрудника,
                            "inn": ИНН сотрудника,
                            "position": Должность сотрудника,
                            "birth_date": Дата рождения сотрудника,
                            "address": Адрес сотрудника,
                            "passport_page_1": Первая страница паспорта сотрудника,
                            "passport_page_1_original_name": Оригинальное имя первой страницы паспорта сотрудника,
                            "passport_page_1_mime_type": MIME-тип первой страницы паспорта сотрудника,
                            "passport_page_1_size": Размер первой страницы паспорта сотрудника,
                            "passport_page_5": Пятая страница паспорта сотрудника,
                            "passport_page_5_original_name": Оригинальное имя пятой страницы паспорта сотрудника,
                            "passport_page_5_mime_type": MIME-тип пятой страницы паспорта сотрудника,
                            "passport_page_5_size": Размер пятой страницы паспорта сотрудника,
                            "photo": Фото сотрудника,
                            "photo_original_name": Оригинальное имя фото сотрудника,
                            "photo_mime_type": MIME-тип фото сотрудника,
                            "photo_size": Размер фото сотрудника,
                            "created_at": Дата создания сотрудника,
                            "updated_at": Дата обновления сотрудника,
                            "certificates_file": Файл с удостоверениями сотрудника,
                            "certificates_file_original_name": Оригинальное имя файла с удостоверениями сотрудника,
                            "certificates_file_mime_type": MIME-тип файла с удостоверениями сотрудника,
                            "certificates_file_size": Размер файла с удостоверениями сотрудника,
                            "status": Статус сотрудника,
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
        tools=tools
    )
        
    if not response.choices or not response.choices[0].message:
        return {
            "error": "Пустой ответ от OpenAI API",
            "message": "❌ Ошибка: получен пустой ответ от ИИ"
        }
    
    result = response.choices[0].message.content
    print(f"✅ Поиск сотрудников завершен")
    return result
        
    

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
    }
]

# ==== диспетчер ====

async def run_dispatcher(messages: list):
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
        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в run_dispatcher: {str(e)}"
        print(error_msg)
        return error_msg

# ==== пример запуска ====

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