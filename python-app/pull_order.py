import os
import json
import asyncio
import requests
from openai import AsyncOpenAI
from datetime import datetime
from dateutil.relativedelta import relativedelta
from get_jsonAPIai import call_external_api, sort_employee

from dotenv import load_dotenv
from logger import order, debug, info, error, critical, success, log_function_entry, log_function_exit

load_dotenv()

# Инициализация клиента OpenAI с обработкой ошибок
try:
    client = AsyncOpenAI(
        base_url="https://api.polza.ai/api/v1",

        api_key=os.getenv("POLZA_AI_TOKEN")
    )
except Exception as e:

    critical(f"Не удалось инициализировать OpenAI клиент: {e}")
    client = None

BASE_URL = "http://labor.tetrakom-crm-miniapp.ru"


chat_history_order = []

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

async def makeOrderFormat(messages, employee_name, certificate_name):
    """Форматирует заявку в JSON формате"""
    log_function_entry("makeOrderFormat", args=(messages, employee_name, certificate_name))
    # Сначала получаем данные сотрудника
    json_people = await sort_employee(employee_name)
    
    debug(f"sort_employee вернул: {type(json_people)}")
    debug(f"Содержимое json_people: {json_people}")
    
    # Проверяем, нужно ли парсить JSON
    if isinstance(json_people, str):
        try:
            json_people = json.loads(json_people)
            debug(f"После парсинга JSON: {type(json_people)}")
        except json.JSONDecodeError:
            error(f"Ошибка парсинга JSON от sort_employee: {json_people}")
            log_function_exit("makeOrderFormat", error="Ошибка парсинга JSON от sort_employee")
            return None
    
    # Проверяем на ошибку API
    if isinstance(json_people, dict) and 'error' in json_people:
        error(f"Ошибка API: {json_people['error']}")
        log_function_exit("makeOrderFormat", error=f"Ошибка API: {json_people['error']}")
        return None
    
    # Проверяем, есть ли данные сотрудника
    has_employee_data = False
    if isinstance(json_people, dict):
        if 'data' in json_people and json_people['data']:
            has_employee_data = True
        elif 'full_name' in json_people:
            has_employee_data = True
    elif isinstance(json_people, list) and len(json_people) > 0:
        has_employee_data = True
    
    if not has_employee_data:
        info(f"Сотрудник '{employee_name}' не найден, создаем нового")
        log_function_exit("makeOrderFormat", result={"type": "clarification", "message": f"Сотрудник '{employee_name}' не найден, создаем нового"})
        return await createNewEmployee(employee_name, certificate_name, messages)
    
    # Initialize all fields to "null"
    employee_full_name = employee_name
    snils = "null"
    inn = "null"
    position = "null"
    birth_date = "null"
    phone = "null"
    
    if isinstance(json_people, dict) and 'data' in json_people:
        data = json_people['data']
        debug(f"data type: {type(data)}, length: {len(data) if isinstance(data, list) else 'not list'}")
        if isinstance(data, list) and len(data) > 0:
            employee_full_name = data[0].get('full_name', employee_name)
            snils = data[0].get('snils', "null")
            inn = data[0].get('inn', "null")
            position = data[0].get('position', "null")
            birth_date = data[0].get('birth_date', "null")
            phone = data[0].get('phone', "null")
            debug(f"Extracted from data[0]: {employee_full_name}, {snils}, {inn}")
        elif isinstance(data, dict):
            # data is a dict with employee data directly
            employee_full_name = data.get('full_name', employee_name)
            snils = data.get('snils', "null")
            inn = data.get('inn', "null")
            position = data.get('position', "null")
            birth_date = data.get('birth_date', "null")
            phone = data.get('phone', "null")
            debug(f"Extracted from data dict: {employee_full_name}, {snils}, {inn}")
    elif isinstance(json_people, dict) and 'full_name' in json_people:
        # json_people is a dict with employee data directly
        debug("json_people is employee data dict")
        employee_full_name = json_people.get('full_name', employee_name)
        snils = json_people.get('snils', "null")
        inn = json_people.get('inn', "null")
        position = json_people.get('position', "null")
        birth_date = json_people.get('birth_date', "null")
        phone = json_people.get('phone', "null")
        debug(f"Extracted from json_people: {employee_full_name}, {snils}, {inn}")
    elif isinstance(json_people, list) and len(json_people) > 0:
        debug(f"json_people is list, length: {len(json_people)}")
        if isinstance(json_people[0], dict):
            employee_full_name = json_people[0].get('full_name', employee_name)
            snils = json_people[0].get('snils', "null")
            inn = json_people[0].get('inn', "null")
            position = json_people[0].get('position', "null")
            birth_date = json_people[0].get('birth_date', "null")
            phone = json_people[0].get('phone', "null")
            debug(f"Extracted from json_people[0]: {employee_full_name}, {snils}, {inn}")
    else:
        debug("No matching condition found")
    
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
    
    debug(f"Сформированный order_json: {order_json}")
    log_function_exit("makeOrderFormat", result=order_json)
    return order_json

async def clarification(messages, order_json):
    """Уточняет данные у пользователя"""
    log_function_entry("clarification", args=(messages, order_json))
    response = await client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {"role": "system", "content": f"""Ты — помощник для уточнения данных у пользователя.
                    Вот данные для заказа: {json.dumps(order_json, indent=4, ensure_ascii=False)}

                    Твоя задача — уточнить данные у пользователя.
                    Проверь все ли данные в employee есть и если нет, уточни у пользователя запиши сообщение в поле message.
                    Если все данные есть, верни order_json, но измени в нем type на "readyorder".
                    Если данные неполные, верни order_json, но измени в нем type на "clarification".
                    В конечном итоге у тебя должен получиться вот такоц JSON:
                         {{
                            "type": "clarification или readyorder",
                            "employee": {{
                                "full_name": "ФИО сотрудника",
                                "snils": "СНИЛС сотрудника",
                                "inn": "ИНН сотрудника",
                                "position": "Должность сотрудника",
                                "birth_date": "Дата рождения сотрудника",
                                "phone": "Телефон сотрудника"
                            }},
                            "certificate": [
                                "Название удостоверения"
                            ],
                            "status": "new_employee",
                            "message": "Сообщение для уточнения данных, если они неполные"
                        }}
                    ОБЯЗАТЕЛЬНО: возвращай только order_json, ничего больше и в формате JSON."""},
            {"role": "user", "content": f"Уточни данные у пользователя: {messages}"}
        ]
    )
    
    if not response.choices or not response.choices[0].message:
        log_function_exit("clarification", error="Получен пустой ответ от OpenAI API clarification")
        return "❌ Ошибка: получен пустой ответ от OpenAI API clarification"
    
    msg = response.choices[0].message
    info(f"Ответ ИИ clarification: {msg.content}")
    
    log_function_exit("clarification", result=msg.content)
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

async def createNewEmployee(employee_name, certificate_name, messages):
    """Создает нового сотрудника, анализируя историю чата с помощью ИИ"""
    log_function_entry("createNewEmployee", args=(employee_name, certificate_name, messages))
    try:
        info(f"Анализирую историю чата для создания нового сотрудника: {employee_name}")
        
        # Системное сообщение для ИИ
        system_message = {
            "role": "system",
            "content": f"""Ты — помощник для создания нового сотрудника.
            
            Анализируй историю чата и извлекай информацию о сотруднике '{employee_name}'.
            
            Ищи в сообщениях:
            - СНИЛС 
            - ИНН 
            - Должность
            - Дата рождения 
            - Телефон 
            
            Если информация найдена, заполни соответствующие поля.
            Если информации нет, оставь "null".
            
            ВАЖНО: возвращай только JSON в таком формате:
            {{
                "type": "clarification",
                "employee": {{
                    "full_name": "{employee_name}",
                    "snils": "найденный_снилс_или_null",
                    "inn": "найденный_инн_или_null",
                    "position": "найденная_должность_или_null",
                    "birth_date": "найденная_дата_или_null",
                    "phone": "найденный_телефон_или_null"
                }},
                "certificate": {certificate_name},
                "status": "new_employee",
            }}

            Не задавай лишние вопросы, только уточни данные.
            """
        }
        
        # Добавляем системное сообщение к истории
        messages_with_system = [system_message] + messages
        
        info(f"Отправляю запрос к ИИ для анализа истории чата")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=messages_with_system,
            temperature=0.1
        )
        
        if not response.choices or not response.choices[0].message:
            log_function_exit("createNewEmployee", error="Получен пустой ответ от OpenAI API createNewEmployee")
            return None
        
        ai_response = response.choices[0].message.content
        info(f"Ответ ИИ для создания сотрудника: {ai_response}")
        
        try:
            # Парсим ответ ИИ
            new_employee = json.loads(ai_response)
            
            # Проверяем, что все обязательные поля есть
            if "type" in new_employee and "employee" in new_employee:
                success(f"Новый сотрудник создан с помощью ИИ: {json.dumps(new_employee, indent=2, ensure_ascii=False)}")
                log_function_exit("createNewEmployee", result=new_employee)
                return new_employee
            else:
                error("ИИ вернул неполную структуру")
                log_function_exit("createNewEmployee", error="ИИ вернул неполную структуру")
                return None
                
        except json.JSONDecodeError as e:
            error(f"Ошибка парсинга JSON от ИИ: {e}")
            log_function_exit("createNewEmployee", error=f"Ошибка парсинга JSON от ИИ: {e}")
            return None
        
    except Exception as e:
        error_msg = f"❌ Ошибка при создании нового сотрудника: {str(e)}"
        error(error_msg)
        log_function_exit("createNewEmployee", error=error_msg)
        return None

async def parsAllCertificates(certificate_name):
    """Парсит все сертификаты"""
    log_function_entry("parsAllCertificates")
    try:
        import requests
        resp = requests.get(
            f"{BASE_URL}/api/certificates", 
            timeout=30,  # Увеличиваем таймаут
            proxies={"http": None, "https": None},
            headers={'User-Agent': 'PolzaAI-Bot/1.0'}
        )

        

        if resp.status_code == 200:
            info(f"Парсинг всех сертификатов: {resp.json()}")
            system_message = {
            "role": "system",
            "content": f"""Ты — определяешь правильное название сертифката и возвращаешь его id.
            
                У тебя есть имена сертификата который ввел пользоват '{certificate_name}'.
                
                Ищи в {json.dumps(resp.json(), indent=2, ensure_ascii=False)}:
                - Название сертификата и id
                
                Если информация найдена, заполни соответствующие поля.
                Если информации нет, оставь "null".
                
                ВАЖНО: верни id сертификата или сертификатов: {certificate_name}

                Не задавай лишние вопросы, только уточни данные.
                """
            }
            
            info(f"Отправляю запрос к ИИ для анализа истории чата")
            
            response = await client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=system_message,
                temperature=0.1
            )
            return response.choices[0].message.content
        else:
            error(f"Ошибка API: {resp.status_code} - {resp.text}")
            log_function_exit("parsAllCertificates", error=f"Ошибка API: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        error_msg = f"❌ Ошибка при парсинге всех сертификатов: {str(e)}"
        error(error_msg)
        log_function_exit("parsAllCertificates", error=error_msg)
        return None

def updatePerson(order_json):
    """Обновляет данные сотрудника в базе данных"""
    log_function_entry("updatePerson", args=(order_json,))
    try:
        import requests
         
        # Извлекаем данные из заказа
        employee = order_json.get("employee", {})
        certificate = order_json.get("certificate", [])
        id_certificate = parsAllCertificates(certificate)
        info(f"Парсим все сертификаты: {id_certificate}")


        
        # Формируем данные для API
        # api_data = {
        #     "people_id": 1,                    # ID человека (Иванов Иван Иванович)
        #     "certificate_id": 2,               # ID типа сертификата (например, "Пожарная безопасность")
        #     "assigned_date": "2025-01-15",     # Дата выдачи
        #     "certificate_number": "ПБ-001",    # Номер сертификата
        #     "notes": "Новый сертификат"        # Примечания
        # }
        
        # # Очищаем пустые значения
        # api_data = {k: v for k, v in api_data.items() if v and v != "null"}
        
        # info(f"Отправляю данные в API: {json.dumps(api_data, indent=2, ensure_ascii=False)}")
        
        # # Отправляем POST запрос
        # response = requests.post(
        #     "http://labor.tetrakom-crm-miniapp.ru/api/people",
        #     headers={
        #         "Content-Type": "application/json",
        #         "Accept": "application/json",
        #         "User-Agent": "PolzaAI-Bot/1.0"
        #     },
        #     json=api_data,
        #     timeout=30,  # Увеличиваем таймаут
        #     proxies={"http": None, "https": None}
        # )
        
        # if response.status_code == 200 or response.status_code == 201:
        #     success("Заказ успешно добавлен в базу данных")
        #     log_function_exit("addToDatabase", result=f"✅ Заказ для {employee.get('full_name')} успешно добавлен в базу данных со статусом 'В ожидании'")
        #     return f"✅ Заказ для {employee.get('full_name')} успешно измене в базе данных со статусом 'В ожидании'"
        # else:
        #     error(f"Ошибка API: {response.status_code} - {response.text}")
        #     log_function_exit("addToDatabase", error=f"Ошибка API: {response.status_code} - {response.text}")
            # return f"❌ Ошибка при добавлении заказа: {response.status_code} - {response.text}"
            
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке заказа в базу данных: {str(e)}"
        print(error_msg)
        log_function_exit("addToDatabase", error=error_msg)
        return error_msg

def addToDatabase(order_json):
    """Добавляет заказ в базу данных"""
    log_function_entry("addToDatabase", args=(order_json,))
    try:
        import requests
        
        # Извлекаем данные из заказа
        employee = order_json.get("employee", {})
        certificate = order_json.get("certificate", [])
        
        # Формируем данные для API
        api_data = {
            "full_name": employee.get("full_name", ""),
            "position": employee.get("position", ""),
            "phone": employee.get("phone", ""),
            "snils": employee.get("snils", ""),
            "inn": employee.get("inn", ""),
            "birth_date": employee.get("birth_date", ""),
            "status": "В ожидании"
            # "photo": "@https://us1.api.pro-talk.ru/get_image/fa165d7a-2322-4081-9068-c12ce86a8bf5.jpg"
        }
        
        # Очищаем пустые значения
        api_data = {k: v for k, v in api_data.items() if v and v != "null"}
        
        info(f"Отправляю данные в API: {json.dumps(api_data, indent=2, ensure_ascii=False)}")
        
        # Отправляем POST запрос
        response = requests.post(
            "http://labor.tetrakom-crm-miniapp.ru/api/people",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "PolzaAI-Bot/1.0"
            },
            json=api_data,
            timeout=30,  # Увеличиваем таймаут
            proxies={"http": None, "https": None}
        )
        
        if response.status_code == 200 or response.status_code == 201:
            success("Заказ успешно добавлен в базу данных")
            log_function_exit("addToDatabase", result=f"✅ Заказ для {employee.get('full_name')} успешно добавлен в базу данных со статусом 'В ожидании'")
            return f"✅ Заказ для {employee.get('full_name')} успешно добавлен в базу данных со статусом 'В ожидании'"
        else:
            error(f"Ошибка API: {response.status_code} - {response.text}")
            log_function_exit("addToDatabase", error=f"Ошибка API: {response.status_code} - {response.text}")
            return f"❌ Ошибка при добавлении заказа: {response.status_code} - {response.text}"
            
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке заказа в базу данных: {str(e)}"
        print(error_msg)
        log_function_exit("addToDatabase", error=error_msg)
        return error_msg

async def order_dispatcher(messages, chat_history):
    """Запускает диспетчер на основе истории чата"""
    log_function_entry("order_dispatcher", args=(messages, chat_history))

    debug(f"chat_history: {chat_history_order} messages: {messages}")
    try:
        if not client:
            log_function_exit("order_dispatcher", error="OpenAI клиент не инициализирован")
            return "❌ Ошибка: OpenAI клиент не инициализирован"
            


        info(f"Отправляю запрос к ИИ (сообщений: {len(messages)})")
        global order_chat_history
        # Добавляем системное сообщение в начало истории
        messages_with_system = [
            {"role": "system", "content": f"""
                Ты — помощник для заказа удостоверений.

                ВАЖНО: Ты ДОЛЖЕН вызывать функции, а не просто отвечать текстом!
                У тебя есть история чата: {json.dumps(chat_history, ensure_ascii=False)}. 
                Пользователь отвечает: '{messages[-1]['content']}'. 
                Тебе нужно понять из истории, какой заказ уточняется, и передать его в order_data.

                У тебя есть 2 функции:
                1. makeOrderFormat(employee_name, certificate_name) — создание нового заказа
                2. clarification(order_data) — уточнение данных заказа

                ПРАВИЛА:
                - Если пользователь предоставляет ПОЛНЫЕ данные сотрудника (ФИО, СНИЛС, ИНН, телефон, дата рождения, должность) и просит удостоверение → вызывай makeOrderFormat()
                - Если пользователь отвечает на вопрос (например, "монтажник" на вопрос о должности) → вызывай clarification() с данными из предыдущего заказа
                - Если пользователь уточняет детали существующего заказа → вызывай clarification()
                - НИКОГДА не отвечай обычным текстом, ВСЕГДА используй функции!

                - Если пользователь хочет СДЕЛАТЬ НОВЫЙ ЗАКАЗ → вызывай makeOrderFormat().
                    • Обязательно верни JSON в формате:
                        {{
                        "employee_name": "ФИО сотрудника",
                        "certificate_name": ["Название удостоверения"]
                        }}
                    • Всегда используй массив для certificate_name, даже если удостоверение одно.

                    - Если пользователь уточняет детали уже существующего заказа (например: "а ещё добавь ПБО", "не Егоров, а Егоров Иван", "нужно 2 удостоверения") → вызывай clarification().
                    • В clarification() всегда передавай:
                        - messages → текст уточнения пользователя
                        - order_data → JSON заказа, который нужно уточнить (по истории чата в chat_history тебе нужно понять какой заказ нужно уточнить) Тебе обязательно нужно передавать этот аргумент в функцию
                        заказ выглядит в виде json примерно вот так {{'type': 'ПРИМЕР', 'employee': {{'full_name': 'ПРИМЕР', 'snils': 'ПРИМЕР', 'inn': 'ПРИМЕР', 'position': None, 'birth_date': 'ПРИМЕР', 'phone': 'ПРИМЕР'}}, 'certificate': ['ПРИМЕР'], 'status': 'ПРИМЕР', 'message': 'ПРИМЕР'}}
                - ЖЕСТКОЕ ПРАВИЛО: отвечай только JSON в формате:

                - Если пользователь хочет СДЕЛАТЬ НОВЫЙ ЗАКАЗ → вызывай makeOrderFormat().
                Примеры:
                Пользователь: "Сабиров Рустем, СНИЛС 195-071-028-66, нужно удостоверение высоты"
                Ответ: makeOrderFormat({{"employee_name": "Сабиров Рустем Рафисович", "certificate_name": ["удостоверение высоты"]}})

                Пользователь: "заказать Егорову ЭБ"
                Ответ: makeOrderFormat({{"employee_name": "Егоров", "certificate_name": ["ЭБ"]}})

                Пользователь: "и ещё добавь БСИЗ"
                Ответ: clarification(messages="и ещё добавь БСИЗ", order_data={{"employee_name": "Егоров", "certificate_name": ["ЭБ"]}})

                Пользователь: "монтажник" (ответ на вопрос о должности)
                Ответ: clarification(messages="монтажник", order_data={{"employee_name": "Сабиров Рустем Рафисович", "certificate_name": ["обучение для работы на лесах"]}})

                ВАЖНО: Всегда используй массив для certificate_name, даже если удостоверение одно!
                """}
        ]
        
        # Добавляем всю историю чата
        messages_with_system.extend(messages)
        
        debug(f"Отправляю {len(messages_with_system)} сообщений в API")
        debug(f"Первое сообщение: {messages_with_system[0]}")
        debug(f"Последнее сообщение: {messages_with_system[-1]}")
        
        response = await client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=messages_with_system,
            tools=tools,
            tool_choice="auto"
        )
        
        if not response.choices or not response.choices[0].message:
            log_function_exit("order_dispatcher", error="Получен пустой ответ от OpenAI API")
            return "❌ Ошибка: получен пустой ответ от OpenAI API"

        msg = response.choices[0].message
        info(f"Ответ ИИ: {msg.content}")

        # Проверяем, хочет ли ИИ вызвать инструменты
        if msg.tool_calls:
            info(f"ИИ хочет вызвать инструменты: {len(msg.tool_calls)}")
            
            # Обрабатываем каждый tool call
            for tool_call in msg.tool_calls:
                tool_name = tool_call.function.name
                info(f"Вызываю инструмент: {tool_name}")
                
                
                        
                if tool_name == "makeOrderFormat":
                    # Сформируем заявку
                    try:
                        args = json.loads(tool_call.function.arguments)
                        employee_name = args.get("employee_name", "")
                        certificate_name = args.get("certificate_name", "")
                        debug(f"employee_name: {employee_name}, certificate_name: {certificate_name}")
                        result = await makeOrderFormat(messages, employee_name, certificate_name)
                        debug(f"result makeOrderFormat from order_dispatcher: {result}")
                        if result is None:
                            log_function_exit("order_dispatcher", error="Не удалось сформировать заявку")
                            return "❌ Ошибка: не удалось сформировать заявку"
                        if result.get("type") == "clarification":
                            result = await clarification(messages, result)
                            if isinstance(result, str):
                                try:
                                    parsed_result = json.loads(result)
                                    if parsed_result.get("type") == "clarification":
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(parsed_result, ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=parsed_result.get("message"))
                                        return parsed_result.get("message")
                                    else:
                                        addToDatabase(parsed_result)
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(format_message(parsed_result), ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=format_message(parsed_result).get("message"))
                                        return format_message(parsed_result).get("message")
                                        
                                except json.JSONDecodeError:
                                    log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON от clarification: {result}")
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"
                            else:
                                if result.get("type") == "clarification":
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=result.get("message"))
                                    return result.get("message")
                                else:
                                    addToDatabase(result)
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(format_message(result), ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=format_message(result).get("message"))
                                    return format_message(result).get("message")
                        else:
                            addToDatabase(result)
                            updatePerson(result)
                            chat_history_order.append({"role": "assistant", "content": json.dumps(format_message(result), ensure_ascii=False)})
                            log_function_exit("order_dispatcher", result=format_message(result).get("message"))
                            return format_message(result).get("message")
                    except json.JSONDecodeError:
                        log_function_exit("order_dispatcher", error="Неверные аргументы для makeOrderFormat")
                        return "❌ Ошибка: неверные аргументы для makeOrderFormat"
                        
                elif tool_name == "clarification":
                    # Уточняем данные
                    try:
                        info(f"Аргументы для clarification: {tool_call.function}")
                        args = json.loads(tool_call.function.arguments)
                        order_data = args.get("order_data", {})
                        
                        if order_data:
                            result = await clarification(messages, order_data)
                            # Парсим результат clarification если это строка
                            if isinstance(result, str):
                                try:
                                    parsed_result = json.loads(result)
                                    if parsed_result.get("type") == "clarification":
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(parsed_result, ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=parsed_result.get("message"))
                                        return parsed_result.get("message")
                                    else:
                                        addToDatabase(parsed_result)
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(parsed_result, ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=format_message(parsed_result).get("message"))
                                        return format_message(parsed_result).get("message")
                                except json.JSONDecodeError:
                                    log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON от clarification: {result}")
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"
                            else:
                                if result.get("type") == "clarification":
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=result.get("message"))
                                    return result.get("message")
                                else:
                                    addToDatabase(result)
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=format_message(result).get("message"))
                                    return format_message(result).get("message")
                        else:
                        
                            log_function_exit("order_dispatcher", error="Не указаны данные заказа для уточнения")
                            return "❌ Ошибка: не указаны данные заказа для уточнения"
                    except json.JSONDecodeError:
                        log_function_exit("order_dispatcher", error="Неверные аргументы для clarification")
                        return "❌ Ошибка: неверные аргументы для clarification"
                        
                else:
                    log_function_exit("order_dispatcher", error=f"Неизвестный инструмент: {tool_name}")
                    return f"❌ Неизвестный инструмент: {tool_name}"
        
        # Если не было вызова функций, возвращаем обычный ответ
        if not msg.content:
            log_function_exit("order_dispatcher", error="ИИ не предоставил ответ")
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
                chat_history_order.append({"role": "assistant", "content": json.dumps(response_data, ensure_ascii=False)})
                log_function_exit("order_dispatcher", result=message or "Нужно уточнить данные")
                return message or "Нужно уточнить данные"
            elif response_data.get("type") == "readyorder":
                # Заказ готов, возвращаем форматированное сообщение
                chat_history_order.append({"role": "assistant", "content": json.dumps(response_data, ensure_ascii=False)})
                log_function_exit("order_dispatcher", result=f"🔍 Сформированная заявка:\n{json.dumps(response_data, indent=4, ensure_ascii=False)}")
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
                    chat_history_order.append({"role": "assistant", "content": f"❌ Сотрудник '{employee_name}' не найден в базе данных"})
                    log_function_exit("order_dispatcher", result=f"❌ Сотрудник '{employee_name}' не найден в базе данных")
                    return f"❌ Сотрудник '{employee_name}' не найден в базе данных"
                
                order = await makeOrderFormat(messages, employee_name, certificate_name)
                
                if order is None:
                    chat_history_order.append({"role": "assistant", "content": "❌ Ошибка: не удалось сформировать заявку"})
                    log_function_exit("order_dispatcher", error="Не удалось сформировать заявку")
                    return "❌ Ошибка: не удалось сформировать заявку"
                
                # Если нужна уточнение данных, возвращаем сообщение пользователю
                if order.get("type") == "clarification":
                    clarification_result = await clarification(messages, order)
                    # Парсим результат clarification если это строка
                    if isinstance(clarification_result, str):
                        try:
                            parsed_result = json.loads(clarification_result)
                            log_function_exit("order_dispatcher", result=parsed_result.get("message", "Нужно уточнить данные"))
                            return parsed_result.get("message", "Нужно уточнить данные")
                        except json.JSONDecodeError:
                            log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON от clarification: {clarification_result}")
                            return f"❌ Ошибка парсинга JSON от clarification: {clarification_result}"
                    else:
                        log_function_exit("order_dispatcher", result=clarification_result.get("message", "Нужно уточнить данные"))
                        return clarification_result.get("message", "Нужно уточнить данные")
                
                # Если заказ готов, возвращаем форматированное сообщение
                if order.get("type") == "readyorder":
                    log_function_exit("order_dispatcher", result=f"�� Сформированная заявка:\n{json.dumps(order, indent=4, ensure_ascii=False)}")
                    return f"🔍 Сформированная заявка:\n{json.dumps(order, indent=4, ensure_ascii=False)}"
                else:
                    log_function_exit("order_dispatcher", result=order)
                    return order
            else:
                log_function_exit("order_dispatcher", error="Не удалось извлечь ФИО сотрудника")
                return "❌ Ошибка: не удалось извлечь ФИО сотрудника"
                
        except json.JSONDecodeError as e:
            log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON: {str(e)}\nОтвет ИИ: {msg.content}")
            return f"❌ Ошибка парсинга JSON: {str(e)}\nОтвет ИИ: {msg.content}"
    except Exception as e:

        error_msg = f"❌ КРИТИЧЕСКАЯ ОШИБКА в order_dispatcher: {str(e)}"
        error(error_msg)
        log_function_exit("order_dispatcher", error=error_msg)
        return error_msg

async def connect_dispatcher(messages, ceo_chat_history):
    """Запускает диспетчер на основе истории чата"""
    log_function_entry("connect_dispatcher", args=(messages, ceo_chat_history))
    global chat_history_order
    chat_history_order = []
    chat_history = ceo_chat_history.copy() if isinstance(ceo_chat_history, list) else []
    chat_history.extend(chat_history_order)
    result = await order_dispatcher(messages, chat_history)
    
    # Анализируем результат и определяем тип
    if isinstance(result, str):
        # Если результат - строка, проверяем содержимое
        if "Заказ оформлен" in result or "успешно добавлен" in result:
            log_function_exit("connect_dispatcher", result={"type": "orderready", "message": result, "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)})
            return {
                "type": "orderready",
                "message": result,
                "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)
            }
        else:
            log_function_exit("connect_dispatcher", result={"type": "orderclar", "message": result, "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)})
            return {
                "type": "orderclar",
                "message": result,
                "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)
            }
    elif isinstance(result, dict):
        # Если результат - словарь, проверяем поле type
        if result.get("type") == "readyorder":
            log_function_exit("connect_dispatcher", result={"type": "orderready", "message": result.get("message", str(result)), "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)})
            return {
                "type": "orderready",
                "message": result.get("message", str(result)),
                "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)
            }
        else:
            log_function_exit("connect_dispatcher", result={"type": "orderclar", "message": result.get("message", str(result)), "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)})
            return {
                "type": "orderclar",
                "message": result.get("message", str(result)),
                "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)
            }
    else:
        # По умолчанию считаем, что нужна уточнение
        log_function_exit("connect_dispatcher", result={"type": "orderclar", "message": str(result), "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)})
        return {
            "type": "orderclar",
            "message": str(result),
            "chat_history_order": json.dumps(chat_history_order, indent=4, ensure_ascii=False)
        }

