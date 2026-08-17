"""Fast per-hour transcript summaries via DeepSeek (OpenAI-compatible API)."""
import os

from openai import OpenAI

_client = None

SYSTEM_PROMPT = (
    "You summarize one hour of ambient, auto-transcribed conversation. Be concise: 2-5 short "
    "bullet points covering what was actually discussed or decided. Skip filler and small talk "
    "unless it's literally all there is. If the hour is mostly noise/fragments with no real "
    "content, say that in one line instead of padding it out."
)


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com")
    return _client


def summarize(transcript_text: str) -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript_text},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
