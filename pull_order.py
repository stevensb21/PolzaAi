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
    photo = "null"
    
    if isinstance(json_people, dict) and 'data' in json_people:
        data = json_people['data']
        debug(f"data type: {type(data)}, length: {len(data) if isinstance(data, list) else 'not list'}")
        if isinstance(data, list) and len(data) > 0:
            id_person = data[0].get('id', "null")
            employee_full_name = data[0].get('full_name', employee_name)
            snils = data[0].get('snils', "null")
            inn = data[0].get('inn', "null")
            position = data[0].get('position', "null")
            birth_date = data[0].get('birth_date', "null")
            phone = data[0].get('phone', "null")
            photo = data[0].get('photo', "null")
            debug(f"Extracted from data[0]: {employee_full_name}, {snils}, {inn}, photo: {photo}")

        elif isinstance(data, dict):
            # data is a dict with employee data directly
            id_person = data.get('id', "null")
            employee_full_name = data.get('full_name', employee_name)
            snils = data.get('snils', "null")
            inn = data.get('inn', "null")
            position = data.get('position', "null")
            birth_date = data.get('birth_date', "null")
            phone = data.get('phone', "null")
            photo = data.get('photo', "null")
            debug(f"Extracted from data dict: {employee_full_name}, {snils}, {inn}, photo: {photo}")

    elif isinstance(json_people, dict) and 'full_name' in json_people:
        # json_people is a dict with employee data directly
        debug("json_people is employee data dict")
        id_person = json_people.get('id', "null")
        employee_full_name = json_people.get('full_name', employee_name)
        snils = json_people.get('snils', "null")
        inn = json_people.get('inn', "null")
        position = json_people.get('position', "null")
        birth_date = json_people.get('birth_date', "null")
        phone = json_people.get('phone', "null")
        photo = json_people.get('photo', "null")
        debug(f"Extracted from json_people: {employee_full_name}, {snils}, {inn}, photo: {photo}")

    elif isinstance(json_people, list) and len(json_people) > 0:
        debug(f"json_people is list, length: {len(json_people)}")
        if isinstance(json_people[0], dict):
            id_person = json_people[0].get('id', "null")
            employee_full_name = json_people[0].get('full_name', employee_name)
            snils = json_people[0].get('snils', "null")
            inn = json_people[0].get('inn', "null")
            position = json_people[0].get('position', "null")
            birth_date = json_people[0].get('birth_date', "null")
            phone = json_people[0].get('phone', "null")
            photo = json_people[0].get('photo', "null")
            debug(f"Extracted from json_people[0]: {employee_full_name}, {snils}, {inn}, photo: {photo}")

    else:
        debug("No matching condition found")
    
    # Проверяем полноту данных
    # Для существующих сотрудников (id не null) фото не обязательно
    if id_person and id_person != "null":
        # Существующий сотрудник - проверяем только основные поля
        required_fields = [snils, inn, position, birth_date, phone]
        has_missing_data = any(field is None or field == "null" for field in required_fields)
    else:
        # Новый сотрудник - проверяем все поля включая фото
    required_fields = [snils, inn, position, birth_date, phone, photo]
    has_missing_data = any(field is None or field == "null" for field in required_fields)
    
    # Определяем тип на основе полноты данных
    order_type = "clarification" if has_missing_data else "readyorder"
    
    # Формируем JSON объект
    order_json = {
        "type": order_type,
        "employee": {
            "id": id_person,
            "full_name": employee_full_name,
            "snils": snils,
            "inn": inn,
            "position": position,
            "birth_date": birth_date,
            "phone": phone,
            "photo": photo
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
    
    # Проверяем, есть ли фото в последнем сообщении
    last_message = messages[-1] if messages else {}
    photo_url = last_message.get("photo")
    
    if photo_url:
        # Если есть фото, обновляем order_json
        employee = order_json.get("employee", {})
        employee["photo"] = photo_url
        order_json["employee"] = employee
        info(f"Добавлено фото в заказ: {photo_url}")
        info(f"Обновленный order_json: {json.dumps(order_json, indent=2, ensure_ascii=False)}")
    else:
        info(f"Фото не найдено в сообщении. Текущий order_json: {json.dumps(order_json, indent=2, ensure_ascii=False)}")
    
    response = await client.chat.completions.create(
        model="openai/gpt-4.1-mini",
        messages=[
            {"role": "system", "content": f"""Ты — помощник для уточнения данных у пользователя.
                    Вот данные для заказа: {json.dumps(order_json, indent=4, ensure_ascii=False)}

                    Твоя задача — уточнить данные у пользователя.
                    
                    ВАЖНО: Для существующих сотрудников (id не null) фото НЕ обязательно!
                    Для новых сотрудников (id = null) фото обязательно!
                    
                    Проверь данные в employee:
                    - Если сотрудник существующий (id не null): проверь только СНИЛС, ИНН, должность, дату рождения, телефон
                    - Если сотрудник новый (id = null): проверь все поля включая фото
                    
                    ВАЖНО: Если в employee есть поле "photo" и оно НЕ равно null, null, "null" или пустой строке, то фото ЕСТЬ!
                    
                    Если все необходимые данные есть, верни order_json, но измени в нем type на "readyorder".
                    Если данные неполные, верни order_json, но измени в нем type на "clarification".
                    
                    ВАЖНО для статуса:
                    - Если сотрудник новый (id = null) и есть все данные → status = "new_employee"
                    - Если сотрудник существующий (id есть) и есть все данные → status = "existing_employee_with_photo"
                    - Если данные неполные → status = "pending"
                    В конечном итоге у тебя должен получиться вот такоц JSON:
                         {{
                            "type": "clarification или readyorder",
                            "employee": {{
                                "id": "ID сотрудника",
                                "full_name": "ФИО сотрудника",
                                "snils": "СНИЛС сотрудника",
                                "inn": "ИНН сотрудника",
                                "position": "Должность сотрудника",
                                "birth_date": "Дата рождения сотрудника",
                                "phone": "Телефон сотрудника",
                                "photo": "URL фото сотрудника"
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

async def format_message(message):
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
            # Если дата в формате 000000Z (некорректная дата)
            elif str(birth_date).endswith("000000Z"):
                formatted_date = "не указана"
            # Если дата уже в формате дд.мм.гггг
            elif "." in str(birth_date) and len(str(birth_date).split(".")) == 3:
                formatted_date = str(birth_date)
            else:
                formatted_date = str(birth_date)
        except Exception as e:
            debug(f"Ошибка форматирования даты {birth_date}: {e}")
            # Если дата содержит только нули или некорректная
            if "000000" in str(birth_date) or str(birth_date).strip() == "":
                formatted_date = "не указана"
            else:
            formatted_date = str(birth_date)
    else:
        formatted_date = "не указана"
    
    # Получаем полную информацию о сертификатах
    certificate_names = message.get("certificate", [])
    existing_certificates = message.get("existing_certificates", [])
    info(f"Названия сертификатов для получения описаний: {certificate_names}")
    info(f"Существующие сертификаты: {existing_certificates}")

    # Формируем текст для новых сертификатов
    new_certificates_text = ""
    if certificate_names:
    try:
        from bot import get_certificate_details
        certificate_details = await get_certificate_details(certificate_names)
        info(f"Полученные детали сертификатов: {certificate_details}")
        
        # Формируем список сертификатов с описаниями
        for cert in certificate_details:
                new_certificates_text += f"• {cert['name']} - {cert['description']}\n"
    except Exception as e:
        error(f"Ошибка при получении описаний сертификатов: {e}")
            new_certificates_text = f"{certificate_names}"
    
    # Формируем текст для существующих сертификатов
    existing_certificates_text = ""
    if existing_certificates:
        try:
            from bot import get_certificate_details
            existing_certificate_details = await get_certificate_details(existing_certificates)
            info(f"Полученные детали существующих сертификатов: {existing_certificate_details}")
            
            # Формируем список существующих сертификатов
            existing_certificates_text = "\n\n⚠️ **Следующие сертификаты уже существуют у сотрудника и не были добавлены в заказ:**\n"
            for cert in existing_certificate_details:
                existing_certificates_text += f"• {cert['name']} - {cert['description']}\n"
        except Exception as e:
            error(f"Ошибка при получении описаний существующих сертификатов: {e}")
            existing_certificates_text = f"\n\n⚠️ **Следующие сертификаты уже существуют:** {existing_certificates}\n"
    
    return {
        "message": f""" Заказ оформлен и отправлен в базу данных \n для {message.get("employee", {}).get("full_name")} \n с удостоверениями:\n{new_certificates_text}{existing_certificates_text}
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
            - Фото (URL фотографии)
            
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
                        "phone": "найденный_телефон_или_null",
                        "photo": "найденный_url_фото_или_null"
                    }},
                    "certificate": {certificate_name},
                    "status": "new_employee",
                }}
                
                ВАЖНО для статуса:
                - Если сотрудник новый (id = null) → status = "new_employee"
                - Если сотрудник существующий (id есть) → status = "existing_employee_with_photo"
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

async def parsAllCertificates(certificate_names):
    """Парсит все сертификаты и возвращает массив ID"""
    log_function_entry("parsAllCertificates")
    
    try:
        import requests
        api_token = os.getenv("API_TOKEN")
        debug(f"API_TOKEN загружен: {api_token[:10] if api_token else 'НЕ НАЙДЕН'}...")
        debug(f"Полная длина токена: {len(api_token) if api_token else 0}")
        
        if not api_token:
            error("❌ КРИТИЧЕСКАЯ ОШИБКА: API_TOKEN не найден в переменных окружения!")
            return []
        
        resp = requests.get(
            f"{BASE_URL}/api/certificates", 
            timeout=30,  # Увеличиваем таймаут
            proxies={"http": None, "https": None},
            headers={
                'User-Agent': 'PolzaAI-Bot/1.0',
                'Authorization': f'Bearer {api_token}'
            }
        )

        if resp.status_code == 200:
            info(f"Парсинг всех сертификатов: {resp.json()}")
            messages = [ 
                {
                "role": "system",
                "content": f"""Ты — определяешь правильное название сертифката и возвращаешь его id.
            
                У тебя есть имена сертификата который ввел пользователь: {certificate_names}
                
                ВАЖНО: Названия сертификатов могут  написаны с ошибками или сокращенно!
                Ищи ПОХОЖИЕ названия в базе данных, не точные совпадения.
                
                Ищи в {json.dumps(resp.json(), indent=2, ensure_ascii=False)}:
                - Название сертификата и id
                
                ПРАВИЛА ПОИСКА:
                1. "БГ (46б 4г)" может соответствовать "БГ (46б 4г)" в базе
                2. "3 года вР (46в)" может соответствовать "вР (46в)" в базе  
                3. "ОПП ИТРб Высота(рабочая, 2гр)" может соответствовать "ОПП ИТР" и "Высота(рабочая, 2гр)" в базе
                4. Ищи по ключевым словам, не по точному совпадению
                3. Леса это Высота(рабочая, 2гр)
                
                Если информация найдена, заполни соответствующие поля.
                Если информации нет, оставь "null".
                
                ВАЖНО: верни JSON в формате {{"название_сертификата": id, "название_сертификата2": id2}}
                Не задавай лишние вопросы, только уточни данные.
                """
                },
                {
                    "role": "user", 
                    "content": f"Найди ID для сертификатов: {certificate_names}"
                }
            ]
            
            info(f"Отправляю запрос к ИИ для анализа истории чата")
            
            response = await client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=messages,
                temperature=0.1
            )
            
            # Парсим JSON ответ от ИИ
            ai_response = response.choices[0].message.content
            info(f"Ответ ИИ: {ai_response}")
            
            try:
                # Парсим JSON ответ
                parsed_response = json.loads(ai_response)
                # Извлекаем только ID значения
                certificate_ids = list(parsed_response.values())
                info(f"Извлеченные ID сертификатов: {certificate_ids}")
                log_function_exit("parsAllCertificates", result=certificate_ids)
                return certificate_ids
            except json.JSONDecodeError as e:
                error(f"Ошибка парсинга JSON от ИИ: {e}")
                log_function_exit("parsAllCertificates", error=f"Ошибка парсинга JSON: {e}")
                return []
        else:
            error(f"Ошибка API: {resp.status_code} - {resp.text}")
            log_function_exit("parsAllCertificates", error=f"Ошибка API: {resp.status_code} - {resp.text}")
            return []

    except Exception as e:
        error_msg = f"❌ Ошибка при парсинге всех сертификатов: {str(e)}"
        error(error_msg)
        log_function_exit("parsAllCertificates", error=error_msg)
        return []

async def updatePerson(order_json):
    """Обновляет данные сотрудника в базе данных"""
    log_function_entry("updatePerson", args=(order_json,))
    
    try:
        import requests
         
        # Извлекаем данные из заказа
        employee = order_json.get("employee", {})
        certificate = order_json.get("certificate", [])
        id_certificates = await parsAllCertificates(certificate)
        info(f"Парсим все сертификаты: {id_certificates}")

        # Отслеживаем успешно добавленные сертификаты
        added_certificates = []
        existing_certificates = []
        
        # Формируем данные для API
        for id_certificate in id_certificates:
            if id_certificate:
                api_data = {
                    "people_id": order_json.get("employee", {}).get("id", "null"),                    # ID человека (Иванов Иван Иванович)
                    "certificate_id": id_certificate,            # ID типа сертификата (например, "Пожарная безопасность")
                    "assigned_date": "2000-01-01",
                    "certificate_number": "В ожидании",    # Номер сертификата
                }
                # Очищаем пустые значения
                api_data = {k: v for k, v in api_data.items() if v and v != "null"}
                
                info(f"Отправляю данные в API: {json.dumps(api_data, indent=2, ensure_ascii=False)}")
                
                # Отправляем POST запрос
                api_token = os.getenv("API_TOKEN")
                response = requests.post(
                    f"{BASE_URL}/api/people-certificates",
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "PolzaAI-Bot/1.0",
                        "Authorization": f'Bearer {api_token}'
                    },
                    json=api_data,
                    timeout=30,  # Увеличиваем таймаут
                    proxies={"http": None, "https": None}
                )
                if response.status_code == 200 or response.status_code == 201:
                    success(f"Сертификат {id_certificate} успешно добавлен для сотрудника")
                    added_certificates.append(id_certificate)
                elif response.status_code == 422:
                    # Сертификат уже привязан к этому человеку
                    info(f"Сертификат {id_certificate} уже привязан к сотруднику - пропускаем")
                    existing_certificates.append(id_certificate)
                else:
                    error(f"Ошибка API для сертификата {id_certificate}: {response.status_code} - {response.text}")
        success(f"Все сертификаты обработаны для сотрудника {employee.get('full_name', 'Неизвестно')}")
        info(f"Добавлено новых сертификатов: {len(added_certificates)}, уже существующих: {len(existing_certificates)}")
        
        # Если есть новые сертификаты, формируем документ и отправляем уведомления
        if added_certificates:
            info(f"Есть новые сертификаты, формируем документ и отправляем уведомления")
            
            # Получаем названия новых сертификатов для документа
            new_certificate_names = []
            for i, cert_id in enumerate(id_certificates):
                if cert_id in added_certificates and i < len(certificate):
                    new_certificate_names.append(certificate[i])
            
            # Обновляем order_json только с новыми сертификатами
            updated_order_json = order_json.copy()
            updated_order_json["certificate"] = new_certificate_names
            
            # Добавляем информацию о существующих сертификатах
            if existing_certificates:
                existing_certificate_names = []
                for i, cert_id in enumerate(id_certificates):
                    if cert_id in existing_certificates and i < len(certificate):
                        existing_certificate_names.append(certificate[i])
                updated_order_json["existing_certificates"] = existing_certificate_names
            
            # Отправляем уведомления
        try:
            from bot import send_ready_order_notification
            # Используем существующий event loop или создаем новый
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Если loop уже запущен, создаем задачу
                        info("Event loop уже запущен, создаем задачу для отправки уведомлений")
                        asyncio.create_task(send_ready_order_notification(updated_order_json))
                else:
                    # Если loop не запущен, запускаем его
                        info("Event loop не запущен, запускаем его для отправки уведомлений")
                        loop.run_until_complete(send_ready_order_notification(updated_order_json))
            except RuntimeError:
                # Если нет активного loop, создаем новый
                    info("Создаем новый event loop для отправки уведомлений")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                        loop.run_until_complete(send_ready_order_notification(updated_order_json))
                finally:
                    loop.close()
                info("✅ Уведомления отправлены успешно")
        except Exception as e:
                error(f"❌ Ошибка при отправке уведомлений: {e}")
        
        elif existing_certificates:
            # Если все сертификаты уже существуют, отправляем уведомление об этом
            info(f"Все сертификаты уже существуют, отправляем уведомление об этом")
            
            # Получаем названия существующих сертификатов для уведомления
            existing_certificate_names = []
            for i, cert_id in enumerate(id_certificates):
                if cert_id in existing_certificates and i < len(certificate):
                    existing_certificate_names.append(certificate[i])
            
            # Создаем специальный order_json для уведомления о существующих сертификатах
            existing_order_json = order_json.copy()
            existing_order_json["certificate"] = existing_certificate_names
            existing_order_json["status"] = "existing_certificates"
            
            # Отправляем уведомления о существующих сертификатах
            try:
                from bot import send_existing_certificate_notification
                # Используем существующий event loop или создаем новый
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Если loop уже запущен, создаем задачу
                        info("Event loop уже запущен, создаем задачу для отправки уведомлений о существующих сертификатах")
                        asyncio.create_task(send_existing_certificate_notification(existing_order_json))
                    else:
                        # Если loop не запущен, запускаем его
                        info("Event loop не запущен, запускаем его для отправки уведомлений о существующих сертификатах")
                        loop.run_until_complete(send_existing_certificate_notification(existing_order_json))
                except RuntimeError:
                    # Если нет активного loop, создаем новый
                    info("Создаем новый event loop для отправки уведомлений о существующих сертификатах")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(send_existing_certificate_notification(existing_order_json))
                    finally:
                        loop.close()
                info("✅ Уведомления о существующих сертификатах отправлены успешно")
            except Exception as e:
                error(f"❌ Ошибка при отправке уведомлений о существующих сертификатах: {e}")
        
        else:
            info("Нет сертификатов для обработки")
        
        log_function_exit("updatePerson", result=f"✅ Сертификаты успешно добавлены для {employee.get('full_name', 'Неизвестно')}")
        return f"✅ Сертификаты успешно добавлены для {employee.get('full_name', 'Неизвестно')}"
            
    except Exception as e:
        error_msg = f"❌ Ошибка при отправке заказа в базу данных: {str(e)}"
        print(error_msg)
        log_function_exit("updatePerson", error=error_msg)
        return error_msg

async def updateEmployeeData(order_json):
    """Обновляет данные существующего сотрудника (включая фото)"""
    log_function_entry("updateEmployeeData", args=(order_json,))
    
    try:
        import requests
        
        employee = order_json.get("employee", {})
        employee_id = employee.get("id")
        
        if not employee_id:
            error("❌ Не указан ID сотрудника для обновления")
            log_function_exit("updateEmployeeData", error="Не указан ID сотрудника")
            return "❌ Ошибка: не указан ID сотрудника для обновления"
        
        # Формируем данные для обновления
        api_data = {
            "full_name": employee.get("full_name", ""),
            "position": employee.get("position", ""),
            "phone": employee.get("phone", ""),
            "snils": employee.get("snils", ""),
            "inn": employee.get("inn", ""),
            "birth_date": employee.get("birth_date", ""),
            "status": "В ожидании"
        }
        
        # Добавляем фото, если оно есть
        photo_url = employee.get("photo")
        if photo_url and photo_url != "null":
            info(f"Обновляем фото сотрудника: {photo_url}")
            # Для обновления фото используем multipart/form-data
            files = {}
            data = {
                "full_name": employee.get("full_name", ""),
                "position": employee.get("position", ""),
                "phone": employee.get("phone", ""),
                "snils": employee.get("snils", ""),
                "inn": employee.get("inn", ""),
                "birth_date": employee.get("birth_date", ""),
                "status": "В ожидании"
            }
            
            # Очищаем пустые значения
            data = {k: v for k, v in data.items() if v and v != "null"}
            
            # Скачиваем фото и добавляем как файл
            try:
                photo_response = requests.get(photo_url, timeout=10)
                if photo_response.status_code == 200:
                    files['photo'] = ('photo.jpg', photo_response.content, 'image/jpeg')
                    # Сохраняем полный URL фото в данных для API
                    data['photo'] = photo_url
                    info(f"Фото загружено для обновления: {len(photo_response.content)} байт")
                else:
                    error(f"Не удалось загрузить фото: {photo_response.status_code}")
                    files = None
            except Exception as e:
                error(f"Ошибка при загрузке фото: {e}")
                files = None
        else:
            # Если фото нет, используем обычный JSON
            files = None
            data = api_data
        
        info(f"Обновляю данные сотрудника ID {employee_id}: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Отправляем PUT запрос для обновления
        if files:
            # Отправляем с файлом
            response = requests.put(
                f"http://labor.tetrakom-crm-miniapp.ru/api/people/{employee_id}",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "PolzaAI-Bot/1.0",
                    "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
                },
                data=data,
                files=files,
                timeout=30,
                proxies={"http": None, "https": None}
            )
        else:
            # Отправляем обычный JSON
            response = requests.put(
                f"http://labor.tetrakom-crm-miniapp.ru/api/people/{employee_id}",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "PolzaAI-Bot/1.0",
                    "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
                },
                json=data,
                timeout=30,
                proxies={"http": None, "https": None}
            )
        
        if response.status_code == 200 or response.status_code == 201:
            success(f"✅ Данные сотрудника {employee.get('full_name')} успешно обновлены")
            log_function_exit("updateEmployeeData", result=f"✅ Данные сотрудника обновлены")
            return f"✅ Данные сотрудника {employee.get('full_name')} успешно обновлены"
        else:
            error(f"Ошибка API при обновлении: {response.status_code} - {response.text}")
            log_function_exit("updateEmployeeData", error=f"Ошибка API: {response.status_code}")
            return f"❌ Ошибка при обновлении данных: {response.status_code} - {response.text}"
            
    except Exception as e:
        error_msg = f"❌ Ошибка при обновлении данных сотрудника: {str(e)}"
        error(error_msg)
        log_function_exit("updateEmployeeData", error=error_msg)
        return error_msg

async def addToDatabase(order_json):
    """Добавляет заказ в базу данных"""
    log_function_entry("addToDatabase", args=(order_json,))
    info(f"🚀 ВХОД В addToDatabase для сотрудника: {order_json.get('employee', {}).get('full_name', 'Неизвестно')}")
    
    try:
        import requests
        
        # Извлекаем данные из заказа
        employee = order_json.get("employee", {})
        
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
        
        # Сначала создаем сотрудника без фото (используем JSON)
        info(f"Создаем сотрудника без фото: {api_data}")
        data = api_data
        files = None
        
        info(f"Отправляю данные в API: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Отправляем POST запрос
        if files:
            # Отправляем с файлом
            response = requests.post(
                "http://labor.tetrakom-crm-miniapp.ru/api/people",
                headers={
                    "Accept": "application/json",
                    "User-Agent": "PolzaAI-Bot/1.0",
                    "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
                },
                data=data,
                files=files,
                timeout=30,
                proxies={"http": None, "https": None}
            )
        else:
            # Отправляем обычный JSON
            response = requests.post(
                "http://labor.tetrakom-crm-miniapp.ru/api/people",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "PolzaAI-Bot/1.0",
                    "Authorization": f'Bearer {os.getenv("API_TOKEN")}'
                },
                json=data,
                timeout=30,
                proxies={"http": None, "https": None}
            )
        
        if response.status_code == 200 or response.status_code == 201:
            success("Заказ успешно добавлен в базу данных")
            people_json = response.json()
            
            # Извлекаем ID созданного сотрудника
            info(f"Полный ответ API при создании сотрудника: {people_json}")
            
            # Пробуем разные варианты получения ID
            created_employee_id = people_json.get("id") or people_json.get("data", {}).get("id") or people_json.get("employee", {}).get("id")
            info(f"Создан сотрудник с ID: {created_employee_id}")
            
            # Проверяем, что ID не пустой
            if created_employee_id and created_employee_id != "":
                # Формируем структуру для updatePerson
                order_with_id = {
                    "type": "readyorder",
                    "employee": {
                        "id": created_employee_id,  # Используем ID из ответа API
                        "full_name": employee.get("full_name", ""),
                        "snils": employee.get("snils", ""),
                        "inn": employee.get("inn", ""),
                        "position": employee.get("position", ""),
                        "birth_date": employee.get("birth_date", ""),
                        "phone": employee.get("phone", "")
                    },
                    "certificate": order_json.get("certificate", []),
                    "status": "new_employee"
                }
                
                info(f"order_with_id for updatePerson: {order_with_id}")
                
                # Если есть фото, обновляем сотрудника с фото
                photo_url = employee.get("photo")
                if photo_url and photo_url != "null":
                    info(f"Обновляем сотрудника с фото: {photo_url}")
                    # Добавляем фото в order_with_id
                    order_with_id["employee"]["photo"] = photo_url
                    
                    # Обновляем данные сотрудника с фото
                    await updateEmployeeData(order_with_id)
                
                # Вызываем updatePerson для добавления сертификатов
                await updatePerson(order_with_id)
            else:
                error(f"❌ Не удалось получить ID созданного сотрудника: {created_employee_id}")
                error(f"Ответ API: {people_json}")
            
            # Уведомления отправляются в updatePerson, поэтому здесь не отправляем
            
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

async def process_order_result(result):
    """Обрабатывает результат заказа и отправляет уведомления"""
    # Проверяем статус сотрудника
    if result.get("status") == "new_employee":
        # Новый сотрудник - добавляем в базу
        await addToDatabase(result)
    elif result.get("status") == "existing_employee_with_photo":
        # Существующий сотрудник с новым фото - обновляем данные и сертификаты
        await updateEmployeeData(result)
        await updatePerson(result)
    else:
        # Существующий сотрудник - только обновляем сертификаты
        await updatePerson(result)
    
    formatted_result = await format_message(result)
    return formatted_result

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
                - ВАЖНО: Если в истории чата есть уточнение от бота (например, "Пожалуйста, укажите...", "предоставьте фото...") и пользователь отправляет фото или текст → это ОБЯЗАТЕЛЬНО ответ на уточнение, вызывай clarification()
                - Если пользователь предоставляет ПОЛНЫЕ данные сотрудника (ФИО, СНИЛС, ИНН, телефон, дата рождения, должность) и просит удостоверение → вызывай makeOrderFormat()
                - Если пользователь отвечает на вопрос (например, "монтажник" на вопрос о должности) → вызывай clarification() с данными из предыдущего заказа
                - Если пользователь уточняет детали существующего заказа → вызывай clarification()
                - НИКОГДА не отвечай обычным текстом, ВСЕГДА используй функции!
                
                **ПРИОРИТЕТ:** Контекст истории чата ВАЖНЕЕ ключевых слов в последнем сообщении!
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
                                        # Проверяем статус сотрудника
                                        if parsed_result.get("status") == "new_employee":
                                            # Новый сотрудник - добавляем в базу
                                            await addToDatabase(parsed_result)
                                        elif parsed_result.get("status") == "existing_employee_with_photo":
                                            # Существующий сотрудник с новым фото - обновляем данные и сертификаты
                                            await updateEmployeeData(parsed_result)
                                            await updatePerson(parsed_result)
                                        else:
                                            # Существующий сотрудник - только обновляем сертификаты
                                            await updatePerson(parsed_result)
                                        
                                        formatted_result = await format_message(parsed_result)
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(formatted_result, ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=formatted_result.get("message"))
                                        return formatted_result.get("message")
                                        
                                except json.JSONDecodeError:
                                    log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON от clarification: {result}")
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"

                            else:
                                if result.get("type") == "clarification":
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=result.get("message"))
                                    return result.get("message")
                                else:
                                    # Проверяем статус сотрудника
                                    if result.get("status") == "new_employee":
                                        # Новый сотрудник - добавляем в базу
                                        await addToDatabase(result)
                                    elif result.get("status") == "existing_employee_with_photo":
                                        # Существующий сотрудник с новым фото - обновляем данные и сертификаты
                                        await updateEmployeeData(result)
                                        await updatePerson(result)
                                    else:
                                        # Существующий сотрудник - только обновляем сертификаты
                                        await updatePerson(result)
                                    
                                    formatted_result = await format_message(result)
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(formatted_result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=formatted_result.get("message"))
                                    return formatted_result.get("message")

                        else:
                            formatted_result = await process_order_result(result)
                            chat_history_order.append({"role": "assistant", "content": json.dumps(formatted_result, ensure_ascii=False)})
                            log_function_exit("order_dispatcher", result=formatted_result.get("message"))
                            return formatted_result.get("message")

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
                                        formatted_result = await process_order_result(parsed_result)
                                        chat_history_order.append({"role": "assistant", "content": json.dumps(formatted_result, ensure_ascii=False)})
                                        log_function_exit("order_dispatcher", result=formatted_result.get("message"))
                                        return formatted_result.get("message")
                                except json.JSONDecodeError:
                                    log_function_exit("order_dispatcher", error=f"Ошибка парсинга JSON от clarification: {result}")
                                    return f"❌ Ошибка парсинга JSON от clarification: {result}"
                            else:
                                if result.get("type") == "clarification":
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=result.get("message"))
                                    return result.get("message")
                                else:
                                    formatted_result = await process_order_result(result)
                                    chat_history_order.append({"role": "assistant", "content": json.dumps(formatted_result, ensure_ascii=False)})
                                    log_function_exit("order_dispatcher", result=formatted_result.get("message"))
                                    return formatted_result.get("message")
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
    if chat_history_order:
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

