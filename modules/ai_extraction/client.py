import requests
import json
import logging
import config

class OllamaClientError(Exception):
    """Base exception for AI client errors."""
    pass

class OllamaConnectionError(OllamaClientError):
    """Raised when AI provider is unreachable or unauthorized."""
    pass

class OllamaModelNotFoundError(OllamaClientError):
    """Raised when the specified model is not loaded/available."""
    pass

class OllamaClient:
    """
    Client wrapper that routes requests to either local Ollama or cloud Gemini API.
    Maintains class name OllamaClient and exception types to ensure complete compatibility.
    """
    def __init__(self):
        self.provider = config.LLM_PROVIDER
        self.base_url = config.OLLAMA_BASE_URL.rstrip('/')
        self.api_key = config.GEMINI_API_KEY
        
        if self.provider == "gemini":
            self.model = config.GEMINI_MODEL
        else:
            self.model = config.OLLAMA_MODEL
            
    def check_connection(self) -> bool:
        """
        Verifies if the AI service is reachable and configured.
        Falls back to local Ollama check if Gemini key is invalid/unreachable.
        """
        if self.provider == "gemini":
            if not self.api_key or self.api_key.startswith("AQ.Ab8RN"):
                # Check if local Ollama is available as fallback
                try:
                    response = requests.get(f"{self.base_url}/api/tags", timeout=1)
                    return response.status_code == 200
                except requests.exceptions.RequestException:
                    return False
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}?key={self.api_key}"
                headers = {"x-goog-api-key": self.api_key}
                response = requests.get(url, headers=headers, timeout=3)
                if response.status_code == 200:
                    return True
                # Check Ollama fallback if Gemini key invalid
                response = requests.get(f"{self.base_url}/api/tags", timeout=1)
                return response.status_code == 200
            except requests.exceptions.RequestException:
                try:
                    response = requests.get(f"{self.base_url}/api/tags", timeout=1)
                    return response.status_code == 200
                except requests.exceptions.RequestException:
                    return False
        else:
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=3)
                return response.status_code == 200
            except requests.exceptions.RequestException:
                return False
            
    def check_model_available(self) -> bool:
        """
        Verifies if the configured model is installed locally or is available in the API.
        """
        if self.provider == "gemini":
            # For Gemini, if check_connection succeeds, the model is available
            return self.check_connection()
        else:
            try:
                response = requests.get(f"{self.base_url}/api/tags", timeout=3)
                if response.status_code != 200:
                    return False
                    
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                # Match model name directly or with latest tag
                return self.model in models or f"{self.model}:latest" in models
            except requests.exceptions.RequestException:
                return False

    def generate_json(self, prompt: str, system_prompt: str = "") -> dict:
        """
        Calls the LLM provider with JSON format constraint.
        Returns the parsed dictionary response.
        """
        if self.provider == "gemini":
            if not self.api_key:
                raise OllamaConnectionError(
                    "Gemini API key is not configured. "
                    "Please add GEMINI_API_KEY to your .env file."
                )
                
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.0
                }
            }
            
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }
                
            import time
            max_retries = 3
            backoff_factor = 2.0
            
            for attempt in range(max_retries):
                try:
                    logging.info(f"Sending prompt to Gemini model {self.model} (format: JSON) - attempt {attempt + 1}/{max_retries}...")
                    response = requests.post(url, headers=headers, json=payload, timeout=90)
                    
                    if response.status_code == 429:
                        if attempt < max_retries - 1:
                            sleep_time = backoff_factor ** attempt
                            logging.warning(f"Gemini API returned 429 (Rate Limit). Retrying in {sleep_time} seconds...")
                            time.sleep(sleep_time)
                            continue
                            
                    if response.status_code == 400:
                        data = response.json()
                        error_msg = data.get("error", {}).get("message", "Bad Request")
                        raise OllamaClientError(f"Gemini API error: {error_msg}")
                    elif response.status_code in (401, 403):
                        data = response.json() if response.content else {}
                        error_msg = data.get("error", {}).get("message", "Authentication failed")
                        raise OllamaConnectionError(f"Invalid Gemini API Key or authentication failed (HTTP {response.status_code}): {error_msg}")
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise OllamaClientError("Gemini returned no candidates.")
                        
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise OllamaClientError("Gemini response is empty (no parts).")
                        
                    response_text = parts[0].get("text", "").strip()
                    if not response_text:
                        raise OllamaClientError("Gemini returned empty text response.")
                    
                    # Clean up markdown code block formatting if present
                    import re
                    if response_text.startswith("```"):
                        response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                        response_text = re.sub(r'\s*```$', '', response_text)
                    response_text = response_text.strip()
                        
                    return json.loads(response_text)
                    
                except requests.exceptions.Timeout as e:
                    if attempt < max_retries - 1:
                        sleep_time = backoff_factor ** attempt
                        logging.warning(f"Request timed out. Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                        continue
                    raise OllamaClientError("Request to Gemini timed out. The document chunk might be too large or the API is overloaded.")
                except requests.exceptions.RequestException as e:
                    # Retry on 5xx or connection issues, but not 4xx (except 429 which is handled above)
                    status_code = getattr(e.response, 'status_code', None)
                    if attempt < max_retries - 1 and (status_code is None or status_code >= 500 or status_code == 429):
                        sleep_time = backoff_factor ** attempt
                        logging.warning(f"Request failed with {e}. Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                        continue
                    raise OllamaClientError(f"HTTP request error: {e}")
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to parse JSON response from Gemini: {response_text}")
                    raise OllamaClientError(f"Gemini response was not valid JSON: {e}")
                
        else:
            # Local Ollama logic
            if not self.check_connection():
                raise OllamaConnectionError(
                    f"Cannot connect to Ollama server at {self.base_url}. "
                    "Please make sure Ollama is installed and running."
                )
                
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system_prompt,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": 0.0
                }
            }
            
            try:
                logging.info(f"Sending prompt to Ollama model {self.model} (format: json)...")
                response = requests.post(url, json=payload, timeout=90)
                
                if response.status_code == 404:
                    if not self.check_model_available():
                        raise OllamaModelNotFoundError(
                            f"The model '{self.model}' is not found in your Ollama installation. "
                            f"Please run 'ollama pull {self.model}' in your terminal."
                        )
                
                response.raise_for_status()
                result = response.json()
                
                response_text = result.get("response", "").strip()
                if not response_text:
                    raise OllamaClientError("Ollama returned an empty response.")
                
                import re
                if response_text.startswith("```"):
                    response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
                    response_text = re.sub(r'\s*```$', '', response_text)
                response_text = response_text.strip()
                    
                return json.loads(response_text)
                
            except requests.exceptions.Timeout:
                raise OllamaClientError("Request to Ollama timed out. The document chunk might be too large or the model is overloaded.")
            except requests.exceptions.RequestException as e:
                raise OllamaClientError(f"HTTP request error: {e}")
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse JSON response from Ollama: {response_text}")
                raise OllamaClientError(f"Ollama response was not valid JSON: {e}")
