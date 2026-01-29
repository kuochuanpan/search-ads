#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.core.config import settings

def check_openai():
    print("\n--- OpenAI ---")
    if not settings.openai_api_key:
        print("No API Key configured.")
        return

    try:
        import openai
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.models.list()
        # Raw dump of first 5
        print("First 5 raw models found:")
        for m in response.data[:5]:
            print(f"  - {m.id}")
            
        print("\nFiltered models (My Logic):")
        models = sorted([
            m.id for m in response.data 
            if ("gpt" in m.id or "o1-" in m.id or "o3-" in m.id) 
            and "audio" not in m.id 
            and "tts" not in m.id 
            and "realtime" not in m.id
        ])
        for m in models:
            print(f"  - {m}")
    except Exception as e:
        print(f"Error: {e}")

def check_gemini():
    print("\n--- Gemini ---")
    if not settings.gemini_api_key:
        print("No API Key configured.")
        return

    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.list()
        print("All models found (raw name):")
        for m in response:
            print(f"  - {m.name} (methods: {getattr(m, 'supported_generation_methods', 'unknown')})")
            
    except Exception as e:
        print(f"Error: {e}")

def check_ollama():
    print("\n--- Ollama ---")
    url = settings.ollama_base_url or "http://localhost:11434"
    print(f"URL: {url}")
    try:
        import requests
        resp = requests.get(f"{url.rstrip('/')}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            print("Raw response keys:", data.keys())
            if "models" in data:
                for m in data["models"]:
                    print(f"  - {m.get('name')}")
        else:
            print(f"Error: Status {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Loading settings from: {settings.model_config['env_file']}")
    check_openai()
    check_gemini()
    check_ollama()
