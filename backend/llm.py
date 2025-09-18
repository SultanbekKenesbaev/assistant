import sys, json, requests
from .config import cfg

def _messages_to_prompt(user, tags):
    sys_prompt = (
        "You are a classifier. Given a user query in Karakalpak/Kazakh/Russian, "
        "choose ONE best tag from the provided list. "
        "Answer with ONLY the tag string. If nothing fits, answer NONE."
    )
    tag_list = "\n".join(f"- {t}" for t in tags)
    prompt = f"[SYSTEM]\n{sys_prompt}\nAvailable tags:\n{tag_list}\n\n[USER]\n{user}\n[ASSISTANT]\n"
    return prompt

def _ollama_generate(prompt) -> str:
    base = cfg.OLLAMA_BASE_URL.rstrip("/")
    model = cfg.OLLAMA_MODEL
    url = f"{base}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.0}}
    r = requests.post(url, json=payload, timeout=60)
    try:
        data = r.json()
        resp = (data.get("response") or "").strip()
        if resp:
            return resp
    except Exception:
        # возможно NDJSON-стрим — соберём
        out = []
        for line in (r.text or "").splitlines():
            try:
                j = json.loads(line)
                if "response" in j and j["response"]:
                    out.append(j["response"])
            except Exception:
                pass
        if out:
            return "".join(out).strip()
    r.raise_for_status()
    return ""

def classify_to_tag(user_query: str, tags: list[str]) -> str:
    provider = (getattr(cfg, "LLM_PROVIDER", "ollama") or "ollama").strip().lower()
    if not tags:
        return "NONE"
    if provider == "ollama":
        try:
            prompt = _messages_to_prompt(user_query, tags)
            out = _ollama_generate(prompt)
            # берём только первое слово/строку
            tag = out.strip().splitlines()[0].strip()
            if tag in tags or tag == "NONE":
                return tag
        except Exception as e:
            print("[LLM] classify failed:", e, file=sys.stderr)
    # фолбэк — без LLM
    return "NONE"
