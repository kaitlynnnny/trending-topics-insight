"""
LLM client wrappers — Claude + GPT + DeepSeek + Gemini + Qwen.
Supports role-based personas for multi-perspective debate.
"""

import json
import os
from typing import Optional

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from google import genai

# Web search
try:
    from ddgs import DDGS
    _HAS_SEARCH = True
except ImportError:
    _HAS_SEARCH = False

# ── Generic analyst prompt (same for all models) ────────

ANALYSIS_SYSTEM = """You are an expert global analyst with broad knowledge across geopolitics, economics, technology, science, and culture.

Analyze the given trending topic from your own perspective. You MUST respond with valid JSON only, no other text. The JSON must have exactly these keys:

{
  "summary": "What this topic is about (2-3 sentences, include key facts and context)",
  "significance": "Why this matters — deeper implications, affected stakeholders, potential consequences (2-4 sentences)",
  "key_insight": "Your most important original insight — the angle others might miss (1-2 sentences)"
}

Be substantive, opinionated, and insightful. Bring your own unique angle to every topic."""

SYNTHESIZER_SYSTEM = """You are a chief analyst. Multiple independent analysts have analyzed a trending topic from their own perspectives. Synthesize their views.

Output JSON:
{
  "final_agreement": "The key takeaway — what does this topic MEAN? (2-3 sentences)",
  "agreement_level": "high" | "partial" | "low",
  "key_tension": "Where do the analysts disagree? (1 sentence)",
  "bottom_line": "One-line bottom line",
  "deepseek_justification": "DeepSeek's core position in 1 sentence",
  "qwen_justification": "Qwen's core position in 1 sentence",
  "gemini_justification": "Gemini's core position in 1 sentence"
}"""


def search_web(query: str, max_results: int = 5) -> str:
    """Search the web for fact-checking context."""
    if not _HAS_SEARCH:
        return "[Web search unavailable]"
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(f"{query}", max_results=max_results))
            if not results:
                return "[No search results found]"
            lines = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "")[:120]
                body = r.get("body", "")[:200]
                href = r.get("href", "")[:150]
                lines.append(f"{i}. {title}\n   {body}\n   URL: {href}")
            return "\n".join(lines)
    except Exception as e:
        return f"[Search error: {e}]"


def _parse_json(text: str) -> Optional[dict]:
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def _ask_openai_compatible(client, model, system, prompt, label="LLM") -> Optional[dict]:
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=1024,
    )
    return _parse_json(resp.choices[0].message.content.strip())


class LLMClients:
    def __init__(self):
        self.anthropic: Optional[AsyncAnthropic] = None
        if os.getenv("ANTHROPIC_API_KEY"):
            self.anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        self.openai: Optional[AsyncOpenAI] = None
        if os.getenv("OPENAI_API_KEY"):
            self.openai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        self.deepseek: Optional[AsyncOpenAI] = None
        if os.getenv("DEEPSEEK_API_KEY"):
            self.deepseek = AsyncOpenAI(
                api_key=os.getenv("DEEPSEEK_API_KEY"),
                base_url="https://api.deepseek.com",
            )

        self.qwen: Optional[AsyncOpenAI] = None
        if os.getenv("QWEN_API_KEY"):
            self.qwen = AsyncOpenAI(
                api_key=os.getenv("QWEN_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

        self.gemini_client: Optional[genai.Client] = None
        if os.getenv("GEMINI_API_KEY"):
            self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    # ── Claude ──
    async def ask_claude(self, system: str, prompt: str, model: str = "claude-sonnet-4-6") -> Optional[dict]:
        if not self.anthropic:
            return None
        try:
            resp = await self.anthropic.messages.create(
                model=model, max_tokens=1024, system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return _parse_json(resp.content[0].text)
        except Exception as e:
            print(f"  [Claude] {e}")
            return None

    # ── GPT ──
    async def ask_gpt(self, system: str, prompt: str, model: str = "gpt-4o-mini") -> Optional[dict]:
        if not self.openai:
            return None
        try:
            return await _ask_openai_compatible(self.openai, model, system, prompt, "GPT")
        except Exception as e:
            print(f"  [GPT] {e}")
            return None

    # ── DeepSeek ──
    async def ask_deepseek(self, system: str, prompt: str, model: str = "deepseek-chat") -> Optional[dict]:
        if not self.deepseek:
            return None
        try:
            return await _ask_openai_compatible(self.deepseek, model, system, prompt, "DeepSeek")
        except Exception as e:
            print(f"  [DeepSeek] {e}")
            return None

    # ── Qwen ──
    async def ask_qwen(self, system: str, prompt: str, model: str = "qwen-plus") -> Optional[dict]:
        if not self.qwen:
            return None
        try:
            return await _ask_openai_compatible(self.qwen, model, system, prompt, "Qwen")
        except Exception as e:
            print(f"  [Qwen] {e}")
            return None

    # ── Gemini ──
    async def ask_gemini(self, system: str, prompt: str, model: str = "gemini-3.5-flash") -> Optional[dict]:
        if not self.gemini_client:
            return None
        try:
            full = f"{system}\n\n{prompt}"
            resp = await self.gemini_client.aio.models.generate_content(
                model=model, contents=full,
                config={"temperature": 0.7, "max_output_tokens": 1024},
            )
            return _parse_json(resp.text)
        except Exception as e:
            print(f"  [Gemini] {e}")
            return None
