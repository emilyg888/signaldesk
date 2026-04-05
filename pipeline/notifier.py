"""
WhatsApp notifications via Twilio sandbox.
Sends a daily summary after the pipeline completes.
"""

import logging
from datetime import datetime

try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None  # type: ignore[assignment,misc]

log = logging.getLogger(__name__)


def send_whatsapp_summary(results: list) -> None:
    """
    Send a WhatsApp summary of pipeline results via Twilio.
    Skips gracefully if credentials are not configured or send fails.
    """
    from pipeline.config import API_KEYS

    sid   = API_KEYS.get("twilio_account_sid", "")
    token = API_KEYS.get("twilio_auth_token", "")
    from_ = API_KEYS.get("twilio_from", "whatsapp:+14155238886")
    to    = API_KEYS.get("whatsapp_to", "") or API_KEYS.get("twilio_to", "")

    if (
        not sid   or sid.startswith("YOUR_")
        or not token or token.startswith("YOUR_")
        or not to  or "YOUR_" in to
    ):
        log.warning("Twilio credentials not configured — skipping WhatsApp notification")
        return

    if not results:
        log.warning("No pipeline results to summarise — skipping WhatsApp notification")
        return

    msg = _format_message(results)

    try:
        if TwilioClient is None:
            raise ImportError("twilio package not installed")
        client = TwilioClient(sid, token)
        client.messages.create(body=msg, from_=from_, to=to)
        log.info(f"WhatsApp summary sent to {to}")
    except Exception as e:
        log.warning(f"WhatsApp notification failed — {e}")


def _format_message(results: list) -> str:
    now  = datetime.now()
    day  = now.strftime("%A")
    date = now.strftime("%d %b %Y")

    sorted_results = sorted(
        results, key=lambda r: r.get("aggregate_score", 0), reverse=True
    )

    lines = [f"📊 SignalDesk — {day} {date}", ""]

    for r in sorted_results:
        ticker = r.get("ticker", "?")
        score  = r.get("aggregate_score", 0)
        bias   = r.get("analysis", {}).get("bias", "Neutral")
        emoji  = _bias_emoji(score)
        lines.append(f"{ticker}  {score} {emoji} {bias}")

    lines.append("")

    top        = sorted_results[0]
    top_ticker = top.get("ticker", "?")
    top_action = top.get("analysis", {}).get("suggested_action", "")
    top_line   = f"Top signal: {top_ticker} — {top_action}" if top_action else f"Top signal: {top_ticker}"
    lines.append(top_line)

    macro     = results[0].get("macro", {})
    vix       = macro.get("vix")
    us10y     = macro.get("us10y")
    vix_str   = f"VIX {vix} ({_vix_label(vix)})" if vix   is not None else "VIX —"
    yield_str = f"10Y {us10y}%"                   if us10y is not None else "10Y —"
    lines.append(f"Macro: {vix_str}, {yield_str}")

    lines.append("")
    lines.append("Full dashboard → http://localhost:8000")

    return "\n".join(lines)


def _bias_emoji(score: int) -> str:
    if score >= 60:
        return "🟢"
    if score <= 40:
        return "🔴"
    return "⚪"


def _vix_label(vix) -> str:
    if vix is None:
        return "—"
    if vix < 20:
        return "Low Fear"
    if vix < 30:
        return "Moderate"
    return "Elevated"
