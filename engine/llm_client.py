import os
import re
import json
import time
import random
import requests
from google import genai
from google.genai import types


class OllamaClient:
    def __init__(self, base_url="http://localhost:11434/api/generate", model="qwen3:8b",
                 timeout=600, max_retries=5, num_ctx=8192, think=None):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.num_ctx = num_ctx
        self.think = think  # None=모델 기본값, False=thinking 비활성화(qwen3용)
        self.usage = {"input": 0, "output": 0, "calls": 0}

    def generate(self, prompt, system_prompt=None, json_mode=False):
        options = {"temperature": 0.2, "num_ctx": self.num_ctx}
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        # Ollama 0.24.0+: think는 options 안이 아닌 최상위 필드로 전달해야 함
        if self.think is not None:
            payload["think"] = self.think
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["format"] = "json"

        for attempt in range(self.max_retries):
            try:
                response = requests.post(self.base_url, json=payload, timeout=120)
                response.raise_for_status()
                body = response.json()
                self.usage["input"]  += body.get("prompt_eval_count", 0)
                self.usage["output"] += body.get("eval_count", 0)
                self.usage["calls"]  += 1
                text = body.get('response', '')
                if json_mode:
                    return self._parse_json(text, attempt)
                return text
            except Exception as e:
                print(f"Warning: Ollama failed (Attempt {attempt+1}): {str(e)}")
                time.sleep(2 * (attempt + 1))
        return {"error": "MAX_RETRIES_EXCEEDED"}

    def _parse_json(self, text, attempt):
        # qwen3가 think=False에도 불구하고 <think>...</think> 블록을 출력하는 경우 제거
        clean = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        # Escape invalid backslashes (LaTeX)
        clean = clean.replace("\\\\", "__DBL_BS__")
        clean = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', clean)
        clean = clean.replace("__DBL_BS__", "\\\\")

        for candidate in (clean, text):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', candidate, re.DOTALL)
            if json_match:
                try: return json.loads(json_match.group(1))
                except: pass

            brace_match = re.search(r'(\{.*\})', candidate, re.DOTALL)
            if brace_match:
                try: return json.loads(brace_match.group(1))
                except: pass

        print(f"Warning: JSON regex failed, attempting LLM fallback extraction (Attempt {attempt+1})")
        extraction_prompt = f"""You are a JSON data extractor. Read the following evaluation text and output ONLY a valid JSON object representing the results. 
Format required:
{{
  "checklist": {{"C1-1": {{"answer": "YES or NO", "basis": "..."}}, "C1-2": ...}},
  "level": "A/B/C/D/E",
  "comment": "..."
}}
If the text implies all criteria are NO, set them to NO. If it is impossible to determine, do your best guess or set NO.
Text to parse:
{text}"""
        try:
            gemini = GeminiClient(model="gemini-2.5-flash", max_retries=1)
            fixed_data = gemini.generate(extraction_prompt, json_mode=True)
            if isinstance(fixed_data, dict) and "error" not in fixed_data:
                print("LLM fallback extraction successful!")
                return fixed_data
        except Exception as e:
            print(f"LLM fallback failed: {e}")

        print(f"Warning: JSON parse failed completely (Attempt {attempt+1})")
        print(f"  raw output preview: {text[:200]!r}")
        return {"error": "JSON_PARSE_FAILED", "raw_text": text, "total": 0,
                "reason": "Parsing Error", "deductions": [], "bonus": []}


class GeminiClient:
    def __init__(self, model="gemini-2.5-flash", max_tokens=16384, max_retries=6):
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.usage = {"input": 0, "output": 0, "calls": 0}

    def generate(self, prompt, system_prompt=None, json_mode=False):
        config_kwargs = {
            "temperature": 0.2,
            "max_output_tokens": self.max_tokens,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt
        if json_mode:
            config_kwargs["response_mime_type"] = "application/json"

        config = types.GenerateContentConfig(**config_kwargs)

        for attempt in range(self.max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                if response.usage_metadata:
                    self.usage["input"]  += response.usage_metadata.prompt_token_count or 0
                    self.usage["output"] += response.usage_metadata.candidates_token_count or 0
                self.usage["calls"] += 1
                text = response.text
                if json_mode:
                    parsed = self._parse_json(text, attempt)
                    if isinstance(parsed, dict) and "error" in parsed:
                        raise ValueError(f"JSON parsing error: {parsed.get('error')}")
                    return parsed
                return text
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    # 지수 백오프 + jitter: 서버 부하 해소 후 재시도
                    wait = min(5 * (2 ** attempt), 120) + random.uniform(0, 5)
                else:
                    wait = 5 * (attempt + 1)
                print(f"Warning: Gemini API failed (Attempt {attempt+1}): {err_str[:100]}, waiting {wait:.0f}s...")
                time.sleep(wait)
        return {"error": "MAX_RETRIES_EXCEEDED"}

    def _parse_json(self, text, attempt):
        # Escape invalid backslashes (LaTeX)
        clean = text.replace("\\\\", "__DBL_BS__")
        clean = re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', clean)
        clean = clean.replace("__DBL_BS__", "\\\\")
        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            print(f"Warning: JSONDecodeError: {e}")
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', clean, re.DOTALL)
            if json_match:
                try: return json.loads(json_match.group(1))
                except: pass

            brace_match = re.search(r'(\{.*\})', clean, re.DOTALL)
            if brace_match:
                try: return json.loads(brace_match.group(1))
                except: pass

        print(f"Warning: Gemini JSON parse failed (Attempt {attempt+1})")
        print(f"  raw text was: {text}")
        return {"error": "JSON_PARSE_FAILED", "raw_text": text}


class AnthropicClient:
    def __init__(self, model="claude-haiku-4-5-20251001", max_tokens=4096, max_retries=3):
        self.client = anthropic.Anthropic()
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def generate(self, prompt, system_prompt=None, json_mode=False):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(**kwargs)
                text = response.content[0].text
                if json_mode:
                    return self._parse_json(text, attempt)
                return text
            except anthropic.RateLimitError:
                wait = 15 * (attempt + 1)
                print(f"Warning: Anthropic rate limit (Attempt {attempt+1}), waiting {wait}s...")
                time.sleep(wait)
            except Exception as e:
                print(f"Warning: Anthropic API failed (Attempt {attempt+1}): {str(e)}")
                time.sleep(2 * (attempt + 1))
        return {"error": "MAX_RETRIES_EXCEEDED"}

    def _parse_json(self, text, attempt):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
            if json_match:
                try: return json.loads(json_match.group(1))
                except: pass

            brace_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if brace_match:
                try: return json.loads(brace_match.group(1))
                except: pass

        print(f"Warning: Anthropic JSON parse failed (Attempt {attempt+1})")
        return {"error": "JSON_PARSE_FAILED", "raw_text": text}


# Backward compatibility
LLMClient = OllamaClient
