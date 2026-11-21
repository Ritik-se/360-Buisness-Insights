"""AI Business Analyst — answers natural-language questions about the uploaded
dataset. Uses Google Gemini's free tier (no cost, no credit card for the free
quota). The LLM never invents numbers: it can only call `run_calculation`,
which executes a small set of safe, whitelisted pandas aggregations against the
real dataframe server-side, and narrates whatever that returns. If no API key
is configured, this reports that plainly instead of faking a response."""

import base64
import os
import time
from typing import List, Optional

import pandas as pd

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _generate_with_retry(client, **kwargs):
    """Gemini's free tier occasionally returns a transient 503 'high demand' error —
    retry a few times with backoff before surfacing it as a real failure."""
    from google.genai.errors import ServerError

    delay = 2.0
    for attempt in range(4):
        try:
            return client.models.generate_content(**kwargs)
        except ServerError:
            if attempt == 3:
                raise
            time.sleep(delay)
            delay *= 2

SYSTEM_PROMPT = """You are a business data analyst. You answer questions about a dataset using ONLY
numbers you get back from the run_calculation tool — never state a number you haven't
received from a tool call. If a question needs a number, call the tool first.
Be concise and concrete. If the data can't answer the question, say so."""

CALC_TOOL_SCHEMA = {
    "name": "run_calculation",
    "description": "Compute a real aggregation over the dataset. Returns the actual numeric result.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["sum", "mean", "median", "min", "max", "count", "groupby_sum", "correlation"]},
            "column": {"type": "string", "description": "The numeric column to aggregate."},
            "group_by": {"type": "string", "description": "Optional column to group by (for groupby_sum)."},
            "column2": {"type": "string", "description": "Second column (for correlation)."},
        },
        "required": ["operation"],
    },
}


def _run_calculation(df: pd.DataFrame, args: dict) -> dict:
    op = args.get("operation")
    col = args.get("column")
    try:
        if op == "groupby_sum":
            group_by = args.get("group_by")
            if not col or not group_by or col not in df.columns or group_by not in df.columns:
                return {"error": "Unknown column(s)."}
            result = pd.to_numeric(df[col], errors="coerce").groupby(df[group_by]).sum().sort_values(ascending=False)
            return {"result": {str(k): round(float(v), 2) for k, v in result.head(10).items()}}
        if op == "correlation":
            col2 = args.get("column2")
            if not col or not col2 or col not in df.columns or col2 not in df.columns:
                return {"error": "Unknown column(s)."}
            r = pd.to_numeric(df[col], errors="coerce").corr(pd.to_numeric(df[col2], errors="coerce"))
            return {"result": round(float(r), 3) if pd.notna(r) else None}
        if op == "count":
            return {"result": int(len(df))}
        if not col or col not in df.columns:
            return {"error": "Unknown column."}
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        value = {"sum": series.sum, "mean": series.mean, "median": series.median,
                  "min": series.min, "max": series.max}[op]()
        return {"result": round(float(value), 2)}
    except Exception as exc:
        return {"error": str(exc)}


def is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))


def _client():
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _part_to_dict(part) -> dict:
    """Serializes an SDK Part to a JSON-safe dict for storage in the frontend's
    opaque `history` field. Gemini's newer models attach a `thought_signature` to
    function_call parts that MUST be echoed back verbatim on the next turn, or the
    API rejects the request — so it's preserved here (base64, since it's raw bytes)."""
    if getattr(part, "function_call", None) is not None:
        fc = part.function_call
        d = {"function_call": {"name": fc.name, "args": dict(fc.args or {})}}
    else:
        d = {"text": part.text or ""}
    sig = getattr(part, "thought_signature", None)
    if sig:
        d["thought_signature"] = base64.b64encode(sig).decode("ascii")
    return d


def _content_to_dict(content) -> dict:
    return {"role": content.role, "parts": [_part_to_dict(p) for p in content.parts]}


def _dict_to_part(d: dict, types):
    sig = d.get("thought_signature")
    sig_bytes = base64.b64decode(sig) if sig else None
    if "function_call" in d:
        fc = d["function_call"]
        return types.Part(function_call=types.FunctionCall(name=fc["name"], args=fc.get("args") or {}), thought_signature=sig_bytes)
    if "function_response" in d:
        fr = d["function_response"]
        return types.Part(function_response=types.FunctionResponse(name=fr["name"], response=fr.get("response") or {}))
    return types.Part(text=d.get("text", ""))


def _dict_to_content(d: dict, types):
    return types.Content(role=d["role"], parts=[_dict_to_part(p, types) for p in d["parts"]])


def ask(df: pd.DataFrame, tags: dict, question: str, history: Optional[List[dict]] = None) -> dict:
    if not is_configured():
        raise RuntimeError(
            "AI Analyst needs a free API key. Get one at https://aistudio.google.com/apikey, set the "
            "GEMINI_API_KEY environment variable on the backend, and restart it to enable natural-language questions."
        )

    try:
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "The 'google-genai' Python package isn't installed. Run: pip install google-genai"
        )

    client = _client()
    column_summary = ", ".join(f"{c} ({t['role']})" for c, t in tags.items())
    context = f"Dataset columns and detected roles: {column_summary}. Row count: {len(df)}."

    contents = [_dict_to_content(c, types) for c in (history or [])]
    contents.append(types.Content(role="user", parts=[types.Part(text=f"{context}\n\nQuestion: {question}")]))

    tool = types.Tool(function_declarations=[types.FunctionDeclaration(
        name=CALC_TOOL_SCHEMA["name"],
        description=CALC_TOOL_SCHEMA["description"],
        parameters=CALC_TOOL_SCHEMA["parameters"],
    )])
    config = types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, tools=[tool])

    for _ in range(12):  # hard cap on tool-use round-trips (the free-tier model sometimes
                          # calls tools one at a time instead of batching, needing more rounds)
        response = _generate_with_retry(client, model=GEMINI_MODEL, contents=contents, config=config)
        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None) is not None]

        # Reuse the SDK's own Part objects as-is (they already carry the correct
        # thought_signature) rather than round-tripping through dicts mid-loop.
        contents.append(types.Content(role="model", parts=list(parts)))

        if not function_calls:
            answer = "".join((p.text or "") for p in parts if getattr(p, "function_call", None) is None)
            return {"answer": answer, "history": [_content_to_dict(c) for c in contents]}

        response_parts = []
        for fc in function_calls:
            result = _run_calculation(df, dict(fc.args or {}))
            response_parts.append(types.Part(function_response=types.FunctionResponse(name=fc.name, response=result)))
        contents.append(types.Content(role="user", parts=response_parts))

    return {"answer": "I wasn't able to finish that calculation — try rephrasing the question.",
            "history": [_content_to_dict(c) for c in contents]}
