# llm_api.py
import requests

def ask_llama3(prompt: str, system_prompt: str = "", model: str = "llama3:8b") -> str:
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False
        }
    )
    return response.json()["message"]["content"].strip()
