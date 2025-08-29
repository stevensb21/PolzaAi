import asyncio
import requests
from polza_SDK import PolzaConfig, Agent, Runner

PolzaConfig.configure(api_key="ak_XfE3O425uoSp2I3xiLDJXmOX7xGLF3BZ1uXUImXxnpo")

def handle_tool_call(tool_name, arguments):
    import requests
    if tool_name == "call_people_api":
        query = arguments.get("query")
        response = requests.get("http://80.87.193.89:8081/api/people")
        data = response.json()
        
        return data
    else:
        return {"error": "Unknown tool"}


search_agent = Agent(
    name="search_agent",
    model="openai/gpt-4o-mini",   # твой прокси
    instructions="""
        Ты — агент поиска сотрудников.
        Твоя задача: по запросу пользователя найти нужных людей в JSON,
        получаемый по http://80.87.193.89:8081/api/people.
        - Ищи по ФИО, должности или частичному совпадению.
        - Если несколько → верни список.
        - Если один → верни только его.
        - Если никого → верни пусто.
    """,
    tools=[
        {
            "name": "call_people_api",
            "description": "Запросить список сотрудников по API. Параметр: query=строка для поиска",
            "parameters": {
                "query": "строка с ФИО или должностью"
            }
        }
    ],
)

# 📋 Агент вывода
output_agent = Agent(
    name="output_agent",
    model="openai/gpt-4.1-mini",
    instructions="""
        выведи все что тебе приходит
    """,
    tools=[],
)

# 📝 Агент заявок
request_agent = Agent(
    name="request_agent",
    model="openai/gpt-4.1-mini",
    instructions="""
        Ты — агент оформления заявок.
        Задача: собрать у пользователя все необходимые данные (ФИО, дата рождения, СНИЛС, ИНН, телефон, фото).
        - Если сотрудник найден → предложи выбрать удостоверения (просроченные, скоро просрочатся, отсутствующие).
        - Если сотрудника нет → собери все данные.
        - Когда всё готово → сформируй заявку и передай её агенту сообщений.
    """,
    tools=[],
)

# 📩 Агент сообщений
message_agent = Agent(
    name="message_agent",
    model="openai/gpt-4.1-mini",
    instructions="""
        Ты — агент отправки сообщений.
        Задача: взять готовую заявку и отправить её Ларисе через tool send_message.
    """,
    tools=[],
)

# ==== главный агент (диспетчер) ====

async def main():
    dispatcher_agent = Agent(
        name="dispatcher_agent",
        model="openai/gpt-4.1-mini",
        instructions="""
            Ты — диспетчер.
            Задача: понять запрос пользователя и вызвать нужного агента.

            Правила:
            - Если запрос связан с поиском сотрудников или "покажи", "найди", "выведи" → вызови search_agent, потом output_agent.
            - Если запрос = "создать заявку" → вызови search_agent, потом request_agent, потом message_agent.
            - Если пользователь пишет что-то другое → уточни, что именно нужно.
        """,
        tools=[
            search_agent.as_tool(tool_name="search_agent", tool_description="Поиск сотрудников"),
            output_agent.as_tool(tool_name="output_agent", tool_description="Форматирование сотрудника"),
            request_agent.as_tool(tool_name="request_agent", tool_description="Создание заявки"),
            message_agent.as_tool(tool_name="message_agent", tool_description="Отправка сообщения")
        ],
    )

async def main():
    result = await Runner.run(search_agent, "Покажи всех Егорова")
    print(result)

asyncio.run(main())
