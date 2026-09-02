# """
# REQUIRE-X Unified LLM Provider
# Supports Google Gemini, OpenAI, Ollama, and a built-in deterministic Semantic / Rule-based Fallback Engine.
# """

# import os
# import json
# import re
# from typing import Dict, Any, Optional, List

# try:
#     from dotenv import load_dotenv
#     load_dotenv()
# except ImportError:
#     pass


# class LLMProvider:
#     """Manages LLM completions across providers with an offline fallback engine."""

#     _cached_gemini_model: Optional[str] = None
#     _gemini_disabled: bool = False

#     def __init__(
#         self,
#         provider: str = "gemini",
#         api_key: Optional[str] = None,
#         model_name: Optional[str] = None,
#         temperature: float = 0.2
#     ):
#         self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
#         self.temperature = temperature
#         self.provider = self._resolve_provider(provider)
#         self.model_name = model_name or self._default_model_for_provider(self.provider)

#     def _resolve_provider(self, requested: str) -> str:
#         req = requested.lower()
#         if req in ["gemini", "google"]:
#             return "gemini"
#         if req == "openai":
#             return "openai"
#         if req == "ollama":
#             return "ollama"
#         if req in ["offline", "builtin", "rule"]:
#             return "offline"

#         if os.environ.get("GEMINI_API_KEY"):
#             return "gemini"
#         elif os.environ.get("OPENAI_API_KEY"):
#             return "openai"
#         else:
#             return "offline"

#     def _default_model_for_provider(self, provider: str) -> str:
#         if provider == "gemini":
#             return "gemini-3.6-flash"
#         elif provider == "openai":
#             return "gpt-4o-mini"
#         elif provider == "ollama":
#             return "llama3.2"
#         return "offline-rule-engine"

#     def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
#         """Executes LLM call or routes to fallback engine."""
#         if self.provider == "gemini" and not LLMProvider._gemini_disabled:
#             try:
#                 result = self._call_gemini(system_prompt, user_prompt, json_mode)
#                 if result:
#                     return result
#             except Exception as e:
#                 print(f"[LLMProvider] Gemini call failed: {e}. Falling back to offline engine.")
#                 return ""

#         elif self.provider == "openai":
#             try:
#                 return self._call_openai(system_prompt, user_prompt, json_mode)
#             except Exception as e:
#                 print(f"[LLMProvider] OpenAI call failed: {e}. Falling back to offline engine.")
#                 return ""

#         elif self.provider == "ollama":
#             try:
#                 return self._call_ollama(system_prompt, user_prompt, json_mode)
#             except Exception as e:
#                 print(f"[LLMProvider] Ollama call failed: {e}. Falling back to offline engine.")
#                 return ""
        
#         return ""

#     def _call_gemini(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
#         """Invokes Gemini API with fast cached model resolution."""
#         if not self.api_key:
#             return ""

#         try:
#             import google.generativeai as genai
#             genai.configure(api_key=self.api_key)

#             # If we already identified a working model in a previous call, use it directly (1-2 sec)
#             if LLMProvider._cached_gemini_model:
#                 model = genai.GenerativeModel(
#                     model_name=LLMProvider._cached_gemini_model,
#                     system_instruction=system_prompt
#                 )
#                 generation_config = {"temperature": self.temperature}
#                 if json_mode:
#                     generation_config["response_mime_type"] = "application/json"
                
#                 response = model.generate_content(user_prompt, generation_config=generation_config)
#                 if response and response.text:
#                     return response.text

#             # Initial discovery: find the available models on user's key
#             candidate_models = []
#             try:
#                 discovered = [
#                     m.name.replace("models/", "") for m in genai.list_models()
#                     if "generateContent" in getattr(m, "supported_generation_methods", [])
#                 ]
#                 if discovered:
#                     candidate_models.extend(discovered)
#             except Exception:
#                 pass

#             if not candidate_models:
#                 candidate_models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]

#             for clean_name in candidate_models[:3]:
#                 try:
#                     model = genai.GenerativeModel(
#                         model_name=clean_name,
#                         system_instruction=system_prompt
#                     )
#                     generation_config = {"temperature": self.temperature}
#                     if json_mode:
#                         generation_config["response_mime_type"] = "application/json"

#                     response = model.generate_content(user_prompt, generation_config=generation_config)
#                     if response and response.text:
#                         LLMProvider._cached_gemini_model = clean_name
#                         return response.text
#                 except Exception as e_mod:
#                     if "API_KEY_INVALID" in str(e_mod):
#                         LLMProvider._gemini_disabled = True
#                         print(f"[LLMProvider] Invalid API key detected. Disabling cloud calls.")
#                         return ""
#                     continue

#         except Exception as e_sdk:
#             print(f"[LLMProvider] Gemini SDK invocation error: {e_sdk}")

#         return ""

#     def _call_openai(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
#         """Invokes OpenAI API."""
#         from openai import OpenAI
#         client = OpenAI(api_key=self.api_key)
#         kwargs = {}
#         if json_mode:
#             kwargs["response_format"] = {"type": "json_object"}

#         response = client.chat.completions.create(
#             model=self.model_name or "gpt-4o-mini",
#             messages=[
#                 {"role": "system", "content": system_prompt},
#                 {"role": "user", "content": user_prompt}
#             ],
#             temperature=self.temperature,
#             **kwargs
#         )
#         return response.choices[0].message.content or ""

#     def _call_ollama(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
#         """Invokes local Ollama server."""
#         import requests
#         url = os.environ.get("OLLAMA_HOST", "http://localhost:11434/api/generate")
#         payload = {
#             "model": self.model_name or "llama3.2",
#             "prompt": f"{system_prompt}\n\nUser:\n{user_prompt}",
#             "stream": False,
#             "options": {"temperature": self.temperature}
#         }
#         if json_mode:
#             payload["format"] = "json"
#         res = requests.post(url, json=payload, timeout=45)
#         res.raise_for_status()
#         return res.json().get("response", "")

#     @staticmethod
#     def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
#         """Safely extracts JSON object or array from LLM response."""
#         if not text:
#             return None
#         text = text.strip()
#         # Remove Markdown code fences if present
#         if text.startswith("```json"):
#             text = text[7:]
#         elif text.startswith("```"):
#             text = text[3:]
#         if text.endswith("```"):
#             text = text[:-3]
#         text = text.strip()

#         try:
#             return json.loads(text)
#         except Exception:
#             # Regex search for outermost { ... } or [ ... ]
#             json_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
#             if json_match:
#                 try:
#                     return json.loads(json_match.group(1))
#                 except Exception:
#                     pass
#         return None





"""
REQUIRE-X Unified LLM Provider
Supports Google Gemini, OpenAI, Ollama, and a built-in deterministic Semantic / Rule-based Fallback Engine.
"""

import os
import json
import re
from typing import Dict, Any, Optional, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class LLMProvider:
    """Manages LLM completions across providers with an offline fallback engine."""

    _cached_gemini_model: Optional[str] = None
    _gemini_disabled: bool = False

    def __init__(
        self,
        provider: str = "gemini",
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: float = 0.2
    ):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        self.temperature = temperature
        self.provider = self._resolve_provider(provider)
        self.model_name = model_name or self._default_model_for_provider(self.provider)

    def _resolve_provider(self, requested: str) -> str:
        req = requested.lower()
        if req in ["gemini", "google"]:
            return "gemini"
        if req == "openai":
            return "openai"
        if req == "ollama":
            return "ollama"
        if req in ["offline", "builtin", "rule"]:
            return "offline"

        if os.environ.get("GEMINI_API_KEY"):
            return "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            return "openai"
        else:
            return "offline"

    def _default_model_for_provider(self, provider: str) -> str:
        if provider == "gemini":
            return "gemini-3.6-flash"
        elif provider == "openai":
            return "gpt-4o-mini"
        elif provider == "ollama":
            return "llama3.2"
        return "offline-rule-engine"

    def generate(self, system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
        """Executes LLM call or routes to fallback engine."""
        if self.provider == "gemini" and not LLMProvider._gemini_disabled:
            try:
                result = self._call_gemini(system_prompt, user_prompt, json_mode)
                if result:
                    return result
            except Exception as e:
                print(f"[LLMProvider] Gemini call failed: {e}. Falling back to offline engine.")
                return ""

        elif self.provider == "openai":
            try:
                return self._call_openai(system_prompt, user_prompt, json_mode)
            except Exception as e:
                print(f"[LLMProvider] OpenAI call failed: {e}. Falling back to offline engine.")
                return ""

        elif self.provider == "ollama":
            try:
                return self._call_ollama(system_prompt, user_prompt, json_mode)
            except Exception as e:
                print(f"[LLMProvider] Ollama call failed: {e}. Falling back to offline engine.")
                return ""
        
        return ""

    def _call_gemini(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
        """Invokes Gemini API with fast cached model resolution."""
        if not self.api_key:
            return ""

        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)

            # If we already identified a working model in a previous call, use it directly (1-2 sec)
            if LLMProvider._cached_gemini_model:
                model = genai.GenerativeModel(
                    model_name=LLMProvider._cached_gemini_model,
                    system_instruction=system_prompt
                )
                generation_config = {"temperature": self.temperature}
                if json_mode:
                    generation_config["response_mime_type"] = "application/json"
                
                response = model.generate_content(user_prompt, generation_config=generation_config)
                if response and response.text:
                    return response.text

            # Initial discovery: find the available models on user's key
            discovered = []
            try:
                discovered = [
                    m.name.replace("models/", "") for m in genai.list_models()
                    if "generateContent" in getattr(m, "supported_generation_methods", [])
                ]
            except Exception:
                pass

            # Always try the configured/default model first (e.g. gemini-3.6-flash),
            # since it reflects the current recommended model rather than arbitrary
            # discovery order (which can surface deprecated models first).
            candidate_models = []
            if self.model_name:
                candidate_models.append(self.model_name)
            for name in discovered:
                if name not in candidate_models:
                    candidate_models.append(name)
            if not candidate_models:
                candidate_models = ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]

            for clean_name in candidate_models[:4]:
                try:
                    model = genai.GenerativeModel(
                        model_name=clean_name,
                        system_instruction=system_prompt
                    )
                    generation_config = {"temperature": self.temperature}
                    if json_mode:
                        generation_config["response_mime_type"] = "application/json"

                    response = model.generate_content(user_prompt, generation_config=generation_config)
                    if response and response.text:
                        LLMProvider._cached_gemini_model = clean_name
                        return response.text
                except Exception as e_mod:
                    if "API_KEY_INVALID" in str(e_mod):
                        LLMProvider._gemini_disabled = True
                        print(f"[LLMProvider] Invalid API key detected. Disabling cloud calls.")
                        return ""
                    continue

        except Exception as e_sdk:
            print(f"[LLMProvider] Gemini SDK invocation error: {e_sdk}")

        return ""

    def _call_openai(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
        """Invokes OpenAI API."""
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = client.chat.completions.create(
            model=self.model_name or "gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=self.temperature,
            **kwargs
        )
        return response.choices[0].message.content or ""

    def _call_ollama(self, system_prompt: str, user_prompt: str, json_mode: bool) -> str:
        """Invokes local Ollama server."""
        import requests
        url = os.environ.get("OLLAMA_HOST", "http://localhost:11434/api/generate")
        payload = {
            "model": self.model_name or "llama3.2",
            "prompt": f"{system_prompt}\n\nUser:\n{user_prompt}",
            "stream": False,
            "options": {"temperature": self.temperature}
        }
        if json_mode:
            payload["format"] = "json"
        res = requests.post(url, json=payload, timeout=45)
        res.raise_for_status()
        return res.json().get("response", "")

    @staticmethod
    def extract_json_block(text: str) -> Optional[Dict[str, Any]]:
        """Safely extracts JSON object or array from LLM response."""
        if not text:
            return None
        text = text.strip()
        # Remove Markdown code fences if present
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            # Regex search for outermost { ... } or [ ... ]
            json_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except Exception:
                    pass
        return None
