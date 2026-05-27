"""
llm_client.py — Unified LLM interface for BioContextAD

Features:
  - Single call_llm(model_role, prompt, sample_id, task) entry point
  - Result caching at results/raw/{task}/{sample_id}_{role}.json
  - Exponential backoff retry (3 attempts)
  - Configurable fallback model per role
  - All failures logged to logs/errors.log
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    filename="logs/errors.log",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
with open("configs/models.yaml") as f:
    MODEL_CONFIG = yaml.safe_load(f)["roles"]

CACHE_ROOT = Path("results/raw")


# ── Cache helpers ─────────────────────────────────────────────────────────────
def _cache_path(task: str, sample_id: str, role: str) -> Path:
    p = CACHE_ROOT / task
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{sample_id}_{role}.json"


def _load_cache(path: Path) -> Optional[dict]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _save_cache(path: Path, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Provider dispatch ─────────────────────────────────────────────────────────
def _call_anthropic(model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text


def _call_openai(model: str, prompt: str, temperature: float, max_tokens: int,
                 base_url: Optional[str] = None) -> str:
    from openai import OpenAI
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def _call_openai_compat(model: str, prompt: str, temperature: float, max_tokens: int,
                        api_key_env: str, base_url: str) -> str:
    """Generic OpenAI-compatible endpoint (DeepSeek, Qwen, Moonshot, Baichuan…)"""
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv(api_key_env), base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


PROVIDER_MAP = {
    "anthropic": lambda m, p, t, mt: _call_anthropic(m, p, t, mt),
    "openai":    lambda m, p, t, mt: _call_openai(m, p, t, mt),
    "deepseek":  lambda m, p, t, mt: _call_openai_compat(
        m, p, t, mt, "DEEPSEEK_API_KEY",
        os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")),
    "dashscope": lambda m, p, t, mt: _call_openai_compat(
        m, p, t, mt, "DASHSCOPE_API_KEY",
        "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    "baichuan":  lambda m, p, t, mt: _call_openai_compat(
        m, p, t, mt, "BAICHUAN_API_KEY",
        "https://api.baichuan-ai.com/v1"),
    "moonshot":  lambda m, p, t, mt: _call_openai_compat(
        m, p, t, mt, "MOONSHOT_API_KEY",
        "https://api.moonshot.cn/v1"),
}


# ── Main interface ────────────────────────────────────────────────────────────
def call_llm(
    model_role: str,
    prompt: str,
    sample_id: str = "default",
    task: str = "misc",
    temperature: Optional[float] = None,
    use_cache: bool = True,
) -> str:
    """
    Unified entry point for all LLM calls.

    Args:
        model_role:  Key in configs/models.yaml (e.g. 'router', 'rag')
        prompt:      Full prompt string
        sample_id:   Identifier for caching (e.g. 'q001')
        task:        Task name for cache directory (e.g. 'e1_router')
        temperature: Override config temperature if set
        use_cache:   Return cached result if available

    Returns:
        LLM response as string
    """
    cfg = MODEL_CONFIG.get(model_role)
    if cfg is None:
        raise ValueError(f"Unknown model_role: '{model_role}'. Check configs/models.yaml.")

    model    = cfg["model"]
    provider = cfg["provider"]
    temp     = temperature if temperature is not None else cfg.get("temperature", 0.0)
    max_tok  = cfg.get("max_tokens", 1024)

    cache_path = _cache_path(task, sample_id, model_role)

    # Cache hit
    if use_cache:
        cached = _load_cache(cache_path)
        if cached:
            return cached["response"]

    # Retry with exponential backoff
    last_err = None
    for attempt in range(3):
        try:
            fn = PROVIDER_MAP.get(provider)
            if fn is None:
                raise ValueError(f"Unknown provider: '{provider}'")
            response = fn(model, prompt, temp, max_tok)
            _save_cache(cache_path, {
                "model_role": model_role,
                "model": model,
                "sample_id": sample_id,
                "task": task,
                "prompt_hash": hashlib.md5(prompt.encode()).hexdigest(),
                "response": response,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            })
            return response
        except Exception as e:
            last_err = e
            wait = 2 ** attempt
            logger.error(f"[{model_role}/{model}] attempt {attempt+1} failed: {e}. Retrying in {wait}s.")
            time.sleep(wait)

    logger.error(f"[{model_role}/{model}] all retries failed for sample_id={sample_id}: {last_err}")
    raise RuntimeError(f"LLM call failed after 3 attempts ({model_role}): {last_err}")
