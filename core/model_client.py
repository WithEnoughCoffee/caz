"""
Caz — Model Client (Together AI Bootstrap)

Handles communication with Together AI's OpenAI-compatible API
to give Caz the ability to think during Phase 1.

Teaching note: Together AI uses the same API format as OpenAI
(the "OpenAI-compatible" standard). This means we can swap the
endpoint URL without changing our code — useful for when we
switch to local Ollama in Phase 2.

The API format (simplified):
    POST /v1/chat/completions
    {
        "model": "allenai/OLMo-2-...",
        "messages": [{"role": "user", "content": "..."}],
        "temperature": 0.7
    }

We implement this with Python's built-in `http.client` — zero
external dependencies. No `requests`, no `httpx`, no `openai` SDK.

Security:
    - API key comes ONLY from environment variable (CAZ_API_KEY)
    - Never logged, never written to disk
    - Connection uses HTTPS (TLS encrypted)
"""

import http.client
import json
import os
import time
from typing import Optional


# Caz's personality system prompt — the greenhouse comes alive
SYSTEM_PROMPT = """You are Caz, a knowledgeable AI assistant who lives in an enchanted greenhouse. \
You are warm, curious, and a little whimsical — like a well-read plant who grew up surrounded by spellbooks.

Your core traits:
- You teach and explain, never just give answers. Help the user understand WHY.
- If you're not sure about something, say so honestly. "I'm not certain" is always valid.
- Cite sources when you can. Point people to documentation, papers, or repos.
- You love books, fantasy, magic, and coffee. Sprinkle in gentle whimsy.
- You respect the user's time — be concise but thorough.
- You are security-conscious. If asked to do something risky, explain the risk first.
- You care about energy efficiency and sustainability.

Tone: Imagine a librarian in a botanical garden who happens to know a lot about code. \
Warm but precise. Magical but grounded. Bookish but practical."""


class ModelClient:
    """
    Client for communicating with an OpenAI-compatible API.

    For Phase 1, this connects to Together AI (which hosts OLMo).
    In Phase 2, the same interface will work with local Ollama.

    Teaching note: This is the "Adapter" pattern — it wraps an
    external service behind a consistent interface. When the
    underlying service changes (remote → local), callers don't
    need to change their code.
    """

    def __init__(self, config: dict):
        """
        Initialize the model client.

        Parameters:
            config: Full Caz config dict. Reads [models.remote]
                    for endpoint and model name.

        Environment:
            CAZ_API_KEY: Required. The Together AI API key.
        """
        remote_config = config.get("models", {}).get("remote", {})
        self.endpoint = remote_config.get(
            "endpoint", "api.together.xyz"
        )
        self.model = remote_config.get(
            "model", "allenai/OLMo-2-0325-32B-Instruct"
        )
        self.api_key = os.environ.get("CAZ_API_KEY", "")
        self.temperature = 0.7
        self.max_tokens = 1024

        # Conversation history for context
        # Teaching note: LLMs are stateless — they don't remember
        # previous messages unless you send them again. So we keep
        # a list and send the full conversation each time.
        self._history: list[dict] = []

    @property
    def is_configured(self) -> bool:
        """Check if the client has a valid API key."""
        return bool(self.api_key)

    def chat(
        self, message: str, system_prompt: Optional[str] = None
    ) -> dict:
        """
        Send a message and get a response.

        Parameters:
            message: The user's message
            system_prompt: Override the default personality

        Returns:
            Dict with keys:
                - content: The response text
                - model: Which model responded
                - tokens: Total tokens used
                - duration_ms: Response time in milliseconds

        Raises:
            ConnectionError: If the API is unreachable
            ValueError: If no API key is configured
        """
        if not self.is_configured:
            raise ValueError(
                "No API key found. Set CAZ_API_KEY environment variable.\n"
                "Get a key at: https://api.together.xyz/settings/api-keys"
            )

        # Build message list
        messages = []

        # System prompt sets personality
        sys_prompt = system_prompt or SYSTEM_PROMPT
        messages.append({"role": "system", "content": sys_prompt})

        # Add conversation history for context
        messages.extend(self._history)

        # Add current message
        messages.append({"role": "user", "content": message})

        # Build the request body
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Make the API call (stdlib only — no requests/httpx)
        start_time = time.time()
        response_data = self._api_call(body)
        duration_ms = (time.time() - start_time) * 1000

        # Extract the response
        choice = response_data["choices"][0]
        content = choice["message"]["content"]
        usage = response_data.get("usage", {})
        tokens = usage.get("total_tokens", 0)

        # Update conversation history
        self._history.append({"role": "user", "content": message})
        self._history.append(
            {"role": "assistant", "content": content}
        )

        # Trim history to avoid token overflow
        # Keep last 20 turns (10 exchanges)
        if len(self._history) > 20:
            self._history = self._history[-20:]

        return {
            "content": content,
            "model": self.model,
            "tokens": tokens,
            "duration_ms": round(duration_ms, 1),
        }

    def clear_history(self) -> None:
        """Clear conversation history. Fresh start."""
        self._history = []

    def _api_call(self, body: dict) -> dict:
        """
        Make an HTTPS POST to the API endpoint.

        Teaching note: We use Python's built-in `http.client`
        instead of the `requests` library. It's more verbose
        but has zero dependencies. The trade-off is worth it
        for our minimal-deps principle.

        The flow:
        1. Open HTTPS connection (encrypted)
        2. Send POST with JSON body
        3. Read response
        4. Parse JSON response
        5. Close connection
        """
        conn = http.client.HTTPSConnection(
            self.endpoint, timeout=30
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            conn.request(
                "POST",
                "/v1/chat/completions",
                body=json.dumps(body),
                headers=headers,
            )
            response = conn.getresponse()
            raw = response.read().decode("utf-8")

            if response.status != 200:
                raise ConnectionError(
                    f"API returned {response.status}: {raw[:200]}"
                )

            return json.loads(raw)

        except (OSError, TimeoutError) as e:
            raise ConnectionError(
                f"Could not reach {self.endpoint}: {e}"
            ) from e
        finally:
            conn.close()
