import json
import os
import time
import urllib.request
from dataclasses import dataclass

from .tasks import TASK_MAP

@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    latency: float
def _temperature():
    t = os.getenv("LLM_TEMPERATURE", "").strip()
    return float(t) if t else None
class BaseLLM:
    provider = "base"
    model = ""
    def generate(self, system: str, prompt: str, meta: dict | None = None) -> LLMResult:
        raise NotImplementedError
class AnthropicLLM(BaseLLM):
    provider = "anthropic"
    def __init__(self, model=None):
        import anthropic
        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
    def generate(self, system, prompt, meta=None):
        kwargs = dict(model=self.model, max_tokens=1500, system=system,
                      messages=[{"role": "user", "content": prompt}])
        if _temperature() is not None:
            kwargs["temperature"] = _temperature()
        t0 = time.perf_counter()
        r = self.client.messages.create(**kwargs)
        dt = time.perf_counter() - t0
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        return LLMResult(text, r.usage.input_tokens, r.usage.output_tokens, dt)


class OpenAILLM(BaseLLM):
    provider = "openai"

    def __init__(self, model=None):
        from openai import OpenAI
        self.client = OpenAI()  # reads OPENAI_API_KEY
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    def generate(self, system, prompt, meta=None):
        kwargs = dict(model=self.model,
                      messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}])
        if _temperature() is not None:
            kwargs["temperature"] = _temperature()
        t0 = time.perf_counter()
        r = self.client.chat.completions.create(**kwargs)
        dt = time.perf_counter() - t0
        return LLMResult(r.choices[0].message.content or "", r.usage.prompt_tokens, r.usage.completion_tokens, dt)


class OllamaLLM(BaseLLM):
    provider = "ollama"

    def __init__(self, model=None):
        self.url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

    def generate(self, system, prompt, meta=None):
        body = {"model": self.model, "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        if _temperature() is not None:
            body["options"] = {"temperature": _temperature()}
        req = urllib.request.Request(f"{self.url}/api/chat", json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        t0 = time.perf_counter()
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = json.loads(resp.read())
        dt = time.perf_counter() - t0
        return LLMResult(data["message"]["content"], data.get("prompt_eval_count", 0), data.get("eval_count", 0), dt)


# Which (strategy -> tasks) the MOCK model gets wrong, so the demo shows realistic differences.
MOCK_FAILS = {
    "zero_shot": {"is_prime", "factorial", "find_largest"},
    "few_shot": {"find_largest", "is_prime"},
    "cot": {"find_largest"},
    "role_based": {"factorial"},
    "iterative": {"is_prime", "factorial", "find_largest"},  # only on attempt 1
}


class MockLLM(BaseLLM):
    """Offline stand-in so the whole pipeline runs without an API key. Results are SYNTHETIC."""
    provider = "mock"
    model = "mock-coder-v1"

    def generate(self, system, prompt, meta=None):
        meta = meta or {}
        task = TASK_MAP[meta["task_id"]]
        strategy, attempt = meta["strategy"], meta.get("attempt", 1)
        wrong = task["id"] in MOCK_FAILS.get(strategy, set()) and not (strategy == "iterative" and attempt > 1)
        code = task["buggy"] if wrong else task["reference"]
        text = f"```python\n{code}```"
        if strategy == "cot":
            text = ("1. Restate the requirement.\n2. List edge cases: empty input, negatives, single element.\n"
                    "3. Outline a simple loop-based algorithm.\n\n") + text
        time.sleep(0.05)
        return LLMResult(text, len(system + prompt) // 4, len(text) // 4, 0.05 + len(text) / 4000)


def available_providers():
    return {
        "mock": True,
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "ollama": True,  # assumed local; fails at run time if the server is down
    }


def get_llm(provider: str | None = None, model: str | None = None) -> BaseLLM:
    provider = (provider or os.getenv("LLM_PROVIDER", "mock")).lower()
    if provider == "mock":
        return MockLLM()
    if provider == "anthropic":
        return AnthropicLLM(model)
    if provider == "openai":
        return OpenAILLM(model)
    if provider == "ollama":
        return OllamaLLM(model)
    raise ValueError(f"Unknown provider: {provider}")
