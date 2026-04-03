"""Processing service: GPT meeting summary + optional Notion push."""

from __future__ import annotations

import os

from loguru import logger

from app.core.config import NOTION_API_KEY, OPENAI_API_KEY
from app.db.database import SessionLocal
from app.db.models import Recording

_SYSTEM_PROMPT = """A partir des informations fournies sur la réunion, précisées par la balise <INFOS> \
ainsi que de la transcription de la réunion <TRANSCRIPT>,
génère un compte rendu de la réunion en nettoyant le transcript,
mets en avant les principaux points abordés,
identifie les prochaines actions et les décisions prises.
Ne pas écrire la liste des participants.

Pour la restitution des actions préciser : Action - Responsable, et si possible un délai.
Regrouper les actions par Responsables.

Quelques termes qui peuvent être utilisés dans la conversation :
- FINAXYS
- Claude Code
- LCL
- SG pour Société Générale
- CA : Crédit Agricole
- CACIB
- BNP"""


def _get_openai_client():
    from openai import OpenAI
    key = OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=key)


def _get_notion_client():
    from notion_client import Client
    key = NOTION_API_KEY or os.environ.get("NOTION_API_KEY", "")
    if not key:
        raise RuntimeError("NOTION_API_KEY is not set")
    return Client(auth=key)


def _build_prompt(transcript: str, context: str = "") -> str:
    parts = [_SYSTEM_PROMPT, ""]
    if context:
        parts += ["<INFOS>", context, "</INFOS>", ""]
    parts += ["<TRANSCRIPT>", transcript, "</TRANSCRIPT>"]
    return "\n".join(parts)


def _text_to_notion_blocks(text: str) -> list[dict]:
    """Convert plain text to a list of Notion paragraph blocks."""
    blocks: list[dict] = []
    for line in text.splitlines():
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": line[:2000]}}]
            },
        })
    return blocks


def _append_to_notion(notion_page_id: str, text: str) -> str:
    """Append processed text as paragraph blocks to a Notion page. Returns the page URL."""
    client = _get_notion_client()
    blocks = _text_to_notion_blocks(text)

    # Notion API limit: 100 blocks per request
    chunk_size = 100
    for i in range(0, len(blocks), chunk_size):
        client.blocks.children.append(block_id=notion_page_id, children=blocks[i:i + chunk_size])

    page = client.pages.retrieve(page_id=notion_page_id)
    url: str = page.get("url", f"https://notion.so/{notion_page_id.replace('-', '')}")
    return url


def process_recording(recording_id: int, notion_page_id: str | None = None) -> None:
    """Background task: call GPT on the transcript, optionally push to Notion, update DB."""
    db = SessionLocal()
    try:
        rec = db.get(Recording, recording_id)
        if not rec:
            logger.error(f"process_recording: recording {recording_id} not found")
            return

        if not rec.transcript_text:
            raise ValueError("No transcript_text available")

        client = _get_openai_client()
        prompt = _build_prompt(rec.transcript_text)

        logger.info(f"Sending transcript to GPT for recording {recording_id} …")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        processed_text: str = response.choices[0].message.content or ""
        logger.info(f"GPT response received ({len(processed_text)} chars)")

        notion_url: str | None = None
        if notion_page_id:
            logger.info(f"Appending to Notion page {notion_page_id} …")
            notion_url = _append_to_notion(notion_page_id, processed_text)
            logger.info(f"Notion page updated: {notion_url}")

        rec.processed_text = processed_text
        rec.status = "processed"
        rec.error_message = None
        if notion_page_id:
            rec.notion_page_id = notion_page_id
        if notion_url:
            rec.notion_url = notion_url
        db.commit()
        logger.info(f"Processing done for recording {recording_id}")

    except Exception as e:
        logger.error(f"Processing failed for recording {recording_id}: {e}")
        try:
            rec = db.get(Recording, recording_id)
            if rec:
                rec.status = "error"
                rec.error_message = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
