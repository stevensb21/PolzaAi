# file: polza_agents.py
import asyncio
import httpx
from typing import List, Optional

class PolzaConfig:
    api_key: str = None
    base_url: str = "https://api.polza.ai/api/v1"

    @classmethod
    def configure(cls, api_key: str, base_url: str = None):
        cls.api_key = api_key
        if base_url:
            cls.base_url = base_url

class Agent:
    def __init__(self, name: str, model: str, instructions: str = "", tools: Optional[List] = None):
        self.name = name
        self.model = model
        self.instructions = instructions
        self.tools = tools or []

    def as_tool(self, tool_name: str, tool_description: str):
        return {"name": tool_name, "description": tool_description, "agent": self}


class Runner:
    @staticmethod
    async def run(agent: Agent, prompt: str) -> str:
        messages = []

        system_content = agent.instructions
        if agent.tools:
            tools_desc = "\n".join([f"- {t['name']}: {t['description']}" for t in agent.tools])
            system_content += "\nИнструменты агента:\n" + tools_desc

        messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {PolzaConfig.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": agent.model,
            "messages": messages,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{PolzaConfig.base_url}/chat/completions", json=payload, headers=headers)
            if resp.status_code not in (200, 201):
                raise Exception(f"Error {resp.status_code}: {resp.text}")
            data = resp.json()

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            return str(data)
