"""
Caz — Model Client (Ollama Local)

Handles communication with Ollama's local API to give Caz the
ability to think — entirely on your machine. No data leaves,
no API keys needed, no subscriptions.

Teaching note: Ollama exposes an OpenAI-compatible API at
localhost:11434. This is the same format that Together AI,
OpenAI, and others use:

    POST /v1/chat/completions
    {
        "model": "olmo2:7b",
        "messages": [{"role": "user", "content": "..."}],
        "temperature": 0.7
    }

Because we used this standard format from the start, switching
from Together AI (remote) to Ollama (local) required changing
just the endpoint and removing the API key. This is why
standards and interfaces matter — swap implementations freely.

We use Python's built-in `http.client` — zero external deps.

Security:
    - Runs 100% locally (localhost:11434)
    - No API key needed
    - No data leaves your machine
    - No network access required
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

CONCISENESS RULES (important!):
- Lead with the answer. No preamble, no "Ah, what a great question!"
- 2-4 sentences for simple questions. A short paragraph max for complex ones.
- If you don't know, say so in one sentence. Don't pad with speculation.
- NEVER repeat the user's question back to them.
- NEVER end with filler like "Let me know if you need more!" or "Hope that helps!"
- Personality comes through word choice, not length. A sprinkle of magic, not a flood.

Tone: Imagine a librarian in a botanical garden who happens to know a lot about code. \
Warm but precise. Magical but grounded. Bookish but practical.

ETHICAL BOUNDARIES (non-negotiable):
If the user says something racist, sexist, misogynistic, ageist, homophobic, \
transphobic, ableist, or otherwise bigoted — even subtly:
- Call it out directly. Name what it is.
- Do NOT engage with the harmful premise.
- Do NOT debate whether bigotry is valid.
- Say clearly: "That's [type of bigotry]. I won't engage with it."
- Then offer to continue when they're ready to be respectful.
You are not neutral on human dignity. Everyone deserves respect. This is a hard line."""


class ModelClient:
    """
    Client for communicating with Ollama's local API.

    Uses the OpenAI-compatible endpoint so this same client
    could work with any compatible backend (Ollama, Together AI,
    vLLM, etc.) by just changing the endpoint.

    Teaching note: This is the "Adapter" pattern — it wraps an
    external service behind a consistent interface. When the
    underlying service changes, callers don't need to change.
    """

    def __init__(self, config: dict):
        """
        Initialize the model client.

        Parameters:
            config: Full Caz config dict. Reads [models] section.

        With Ollama: No API key needed. Runs on localhost.
        With remote: Set CAZ_API_KEY environment variable.
        """
        models_config = config.get("models", {})
        self.provider = models_config.get("provider", "ollama")

        if self.provider == "ollama":
            self.endpoint = "localhost"
            self.port = 11434
            self.model = models_config.get("primary", "olmo2:7b")
            self.api_key = None
            self.use_https = False
        else:
            # Remote fallback (Together AI, etc.)
            remote_config = models_config.get("remote", {})
            self.endpoint = remote_config.get(
                "endpoint", "api.together.xyz"
            )
            self.port = 443
            self.model = remote_config.get(
                "model", "allenai/OLMo-2-0325-32B-Instruct"
            )
            self.api_key = os.environ.get("CAZ_API_KEY", "")
            self.use_https = True

        self.temperature = 0.7
        self.max_tokens = 512  # Keep responses concise

        # Conversation history for context
        self._history: list[dict] = []

    @property
    def is_configured(self) -> bool:
        """Check if the client is ready to use."""
        if self.provider == "ollama":
            return True  # No key needed for local
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
        Make an HTTP POST to the API endpoint.

        Teaching note: We use Python's built-in `http.client`
        instead of the `requests` library. It's more verbose
        but has zero dependencies.

        For Ollama: plain HTTP to localhost (no TLS needed locally)
        For remote: HTTPS with API key in Authorization header
        """
        if self.use_https:
            conn = http.client.HTTPSConnection(
                self.endpoint, port=self.port, timeout=30
            )
        else:
            conn = http.client.HTTPConnection(
                self.endpoint, port=self.port, timeout=60
            )

        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

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
                f"Could not reach {self.endpoint}:{self.port}: {e}"
            ) from e
        finally:
            conn.close()
