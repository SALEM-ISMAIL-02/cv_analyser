"""CV extraction via Ollama — single pass, GPU-first."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from schemas.cv_schema import CvDocument

SYSTEM_PROMPT = """You are a precise CV/resume parser. Extract ONLY information explicitly present in the CV text.
Rules:
- Do not invent or guess missing data.
- Omit optional fields when information is absent.
- Convert dates to YYYY-MM when month is known, or YYYY when only year is known.
- Order work and education most recent first.
- skills = flat list of strings.
- Return valid JSON matching the FreeCV schema."""

FULL_SCHEMA_PROMPT = """Return one JSON object with this structure (omit empty sections as []):
{
  "basics": {"name": "", "label": "", "email": "", "phone": "", "location": "", "summary": "", "url": "", "profiles": []},
  "work": [{"company": "", "position": "", "location": "", "startDate": "", "endDate": "", "current": false, "highlights": []}],
  "education": [{"institution": "", "degree": "", "field": "", "startDate": "", "endDate": ""}],
  "skills": [],
  "languages": [{"language": "", "fluency": ""}],
  "certificates": [{"name": "", "issuer": "", "date": ""}],
  "projects": [],
  "publications": [],
  "awards": [],
  "volunteer": [],
  "interests": [],
  "references": []
}"""


class OllamaConnectionError(Exception):
    pass


class OllamaModelNotFoundError(Exception):
    pass


def _parse_num_gpu() -> int:
    # Ollama: num_gpu=0 means CPU ONLY. -1 = max layers on GPU.
    return int(os.getenv("OLLAMA_NUM_GPU", "-1"))


def _parse_num_ctx() -> int:
    return int(os.getenv("OLLAMA_NUM_CTX", "4096"))


class CvExtractor:
    def __init__(
        self,
        model_name: str | None = None,
        api_url: str | None = None,
        timeout: int = 300,
        num_gpu: int | None = None,
    ):
        # llama3.2:3b fits fully on GTX 1650 4GB; 7b always spills to CPU
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "llama3.2:3b-gpu")
        self.api_url = api_url or os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/chat")
        self.timeout = timeout
        self.num_gpu = num_gpu if num_gpu is not None else _parse_num_gpu()
        self.num_ctx = _parse_num_ctx()

    def warmup(self) -> None:
        """Load model into GPU VRAM before first request."""
        base = self.api_url.replace("/api/chat", "")
        requests.post(
            f"{base}/api/chat",
            json={
                "model": self.model_name,
                "messages": [{"role": "user", "content": "hi"}],
                "stream": False,
                "keep_alive": "30m",
                "options": self._ollama_options(),
            },
            timeout=120,
        )

    def process_cv(self, cv_text: str, hints: dict | None = None) -> CvDocument:
        hints = hints or {}
        hints_block = ""
        if any(hints.get(k) for k in ("email", "phone", "website", "profiles")):
            hints_block = f"\nDetected hints:\n{json.dumps(hints)}\n"

        text = cv_text[:12000]  # cap context for speed on 4GB VRAM

        prompt = f"""{FULL_SCHEMA_PROMPT}
{hints_block}
CV TEXT:
---
{text}
---"""

        data = self._chat_json(prompt)

        payload = {
            "$schema": "https://freecv.org/schema/cv/v1.json",
            "basics": data.get("basics") or {},
            "work": data.get("work") or [],
            "education": data.get("education") or [],
            "skills": data.get("skills") or [],
            "languages": data.get("languages") or [],
            "certificates": data.get("certificates") or [],
            "projects": data.get("projects") or [],
            "publications": data.get("publications") or [],
            "awards": data.get("awards") or [],
            "volunteer": data.get("volunteer") or [],
            "interests": data.get("interests") or [],
            "references": data.get("references") or [],
            "meta": CvDocument.build_meta().model_dump(),
        }

        if not payload["basics"].get("name"):
            payload["basics"]["name"] = self._fallback_name(cv_text)

        return CvDocument.model_validate(payload)

    def _fallback_name(self, cv_text: str) -> str:
        for line in cv_text.splitlines():
            line = line.strip()
            if line and len(line) < 80 and "@" not in line:
                return line
        return "Unknown"

    def _ollama_options(self) -> dict[str, int]:
        return {
            "num_gpu": self.num_gpu,
            "num_ctx": self.num_ctx,
            "num_thread": 4,
        }

    def _chat_json(self, user_prompt: str) -> dict[str, Any]:
        body = {
            "model": self.model_name,
            "format": "json",
            "stream": False,
            "keep_alive": "30m",
            "options": self._ollama_options(),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        try:
            response = requests.post(self.api_url, json=body, timeout=self.timeout)
        except requests.ConnectionError as exc:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.api_url}. "
                "Run: .\\scripts\\setup_ollama_gpu.ps1"
            ) from exc
        except requests.Timeout as exc:
            raise RuntimeError(
                f"Ollama timed out after {self.timeout}s. "
                "Use llama3.2:3b-gpu (not 7b) on GTX 1650."
            ) from exc

        if response.status_code == 404 or "not found" in response.text.lower():
            raise OllamaModelNotFoundError(
                f"Model '{self.model_name}' not installed. "
                f"Run: .\\scripts\\setup_ollama_gpu.ps1"
            )
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")

        content = response.json().get("message", {}).get("content", "")
        if not content:
            return {}

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            cleaned = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            return json.loads(cleaned)

    def health_check(self) -> dict:
        base = self.api_url.replace("/api/chat", "")
        try:
            r = requests.get(f"{base}/api/tags", timeout=5)
            if r.status_code != 200:
                return {"status": "error", "detail": r.text}
            models = [m.get("name", "") for m in r.json().get("models", [])]
            model_available = any(
                m == self.model_name or m.startswith(f"{self.model_name}:")
                for m in models
            )
            return {
                "status": "ok" if model_available else "model_missing",
                "ollama": "reachable",
                "configured_model": self.model_name,
                "num_gpu": self.num_gpu,
                "num_ctx": self.num_ctx,
                "gpu_mode": "max_vram" if self.num_gpu == -1 else f"{self.num_gpu}_layers",
                "available_models": models,
            }
        except requests.ConnectionError:
            return {
                "status": "error",
                "ollama": "unreachable",
                "configured_model": self.model_name,
                "num_gpu": self.num_gpu,
            }
