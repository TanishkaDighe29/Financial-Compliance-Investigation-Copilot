"""
Pluggable LLM client for generating finding narratives.

Design goal: the orchestrator should work identically whether or not a local
LLM is available. `NullLLMClient` (the current default) returns None, which
tells the orchestrator to keep using its rule-based template -- this is what
ran in every test so far. `OllamaClient` talks to a local Ollama server
(http://localhost:11434, zero cost, no API key, nothing leaves the machine)
and is a drop-in replacement.

Nothing else in the codebase needs to change to enable it -- see
`get_llm_client()` at the bottom, and README.md's "Enabling the local LLM"
section for the one-line switch.
"""
import json
import urllib.request
import urllib.error


class LLMClient:
    def generate_finding_narrative(self, question: str, policy_text: str, evidence_texts: list[str]) -> str | None:
        raise NotImplementedError


class NullLLMClient(LLMClient):
    """No LLM available -- orchestrator falls back to its rule-based template.
    This is the safe default and what every existing test exercises."""
    def generate_finding_narrative(self, question, policy_text, evidence_texts):
        return None


class OllamaClient(LLMClient):
    """
    Talks to a local Ollama instance. Install: https://ollama.com (free,
    runs entirely on your machine, no API key, no data leaves your network).
        ollama pull llama3.1:8b
        ollama serve   # usually already running as a background service

    The prompt is deliberately constrained: the model is instructed to only
    describe what's in the provided evidence and never invent a citation,
    a control ID, or a number that isn't in the evidence text. Output is
    still run through `citation_guard.validate_finding()` afterwards --
    the prompt constraint is a hint to the model, not a safety guarantee.
    """
    def __init__(self, host="http://localhost:11434", model="llama3.1:8b", timeout=30):
        self.host = host
        self.model = model
        self.timeout = timeout

    def _available(self) -> bool:
        try:
            urllib.request.urlopen(f"{self.host}/api/tags", timeout=2)
            return True
        except Exception:
            return False

    def generate_finding_narrative(self, question, policy_text, evidence_texts):
        if not self._available():
            return None

        evidence_block = "\n".join(f"- {t}" for t in evidence_texts) or "(no evidence rows)"
        prompt = f"""You are a compliance analyst assistant. Write ONE short paragraph
(max 3 sentences) summarizing whether the evidence below satisfies the policy
requirement. Only state facts that appear in the evidence or policy text below.
Do not invent dates, names, control IDs, or numbers. If the evidence is
insufficient or contradictory, say so plainly.

Question: {question}

Policy requirement: {policy_text}

Evidence:
{evidence_block}

Summary paragraph:"""

        payload = json.dumps({"model": self.model, "prompt": prompt, "stream": False}).encode()
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip() or None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None


def get_llm_client() -> LLMClient:
    """Single switch point. Change this to OllamaClient() to enable the
    local LLM once it's installed and running -- everything else (citation
    validation, fallback-on-failure) is already wired up in orchestrator.py."""
    return NullLLMClient()
