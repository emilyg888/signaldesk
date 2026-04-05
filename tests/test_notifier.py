"""
Unit tests for pipeline/notifier.py
"""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.notifier import _bias_emoji, _format_message, _vix_label, send_whatsapp_summary


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_result(ticker, score, bias="Bullish", suggested_action="Buy", vix=18.5, us10y=4.2):
    return {
        "ticker": ticker,
        "aggregate_score": score,
        "analysis": {
            "bias": bias,
            "conviction": "High",
            "suggested_action": suggested_action,
        },
        "macro": {
            "vix": vix,
            "us10y": us10y,
            "composite_score": 62,
        },
    }


MULTI_RESULTS = [
    make_result("AAPL",    72, bias="Bullish",  suggested_action="Buy dips"),
    make_result("BTC-USD", 38, bias="Bearish",  suggested_action="Avoid"),
    make_result("TSLA",    55, bias="Neutral",  suggested_action="Hold"),
]


# ── _bias_emoji ───────────────────────────────────────────────────────────────

class TestBiasEmoji:
    def test_bullish_score_returns_green(self):
        assert _bias_emoji(60) == "🟢"

    def test_high_bull_score_returns_green(self):
        assert _bias_emoji(85) == "🟢"

    def test_bearish_score_returns_red(self):
        assert _bias_emoji(40) == "🔴"

    def test_low_bear_score_returns_red(self):
        assert _bias_emoji(10) == "🔴"

    def test_neutral_score_returns_white(self):
        assert _bias_emoji(50) == "⚪"

    def test_boundary_60_is_bull(self):
        assert _bias_emoji(60) == "🟢"

    def test_boundary_40_is_bear(self):
        assert _bias_emoji(40) == "🔴"

    def test_boundary_41_is_neutral(self):
        assert _bias_emoji(41) == "⚪"

    def test_boundary_59_is_neutral(self):
        assert _bias_emoji(59) == "⚪"


# ── _vix_label ────────────────────────────────────────────────────────────────

class TestVixLabel:
    def test_low_vix_returns_low_fear(self):
        assert _vix_label(15) == "Low Fear"

    def test_boundary_vix_under_20_is_low_fear(self):
        assert _vix_label(19.9) == "Low Fear"

    def test_moderate_vix(self):
        assert _vix_label(25) == "Moderate"

    def test_elevated_vix(self):
        assert _vix_label(35) == "Elevated"

    def test_none_vix_returns_dash(self):
        assert _vix_label(None) == "—"


# ── _format_message ───────────────────────────────────────────────────────────

class TestFormatMessage:
    def test_header_contains_signaldesk(self):
        msg = _format_message(MULTI_RESULTS)
        assert "📊 SignalDesk" in msg

    def test_all_tickers_present(self):
        msg = _format_message(MULTI_RESULTS)
        assert "AAPL" in msg
        assert "BTC-USD" in msg
        assert "TSLA" in msg

    def test_tickers_sorted_by_score_descending(self):
        msg = _format_message(MULTI_RESULTS)
        pos_aapl = msg.index("AAPL")      # score 72 — should be first
        pos_tsla = msg.index("TSLA")      # score 55 — should be second
        pos_btc  = msg.index("BTC-USD")   # score 38 — should be last
        assert pos_aapl < pos_tsla < pos_btc

    def test_top_signal_shows_highest_score_ticker(self):
        msg = _format_message(MULTI_RESULTS)
        assert "Top signal: AAPL" in msg

    def test_top_signal_includes_suggested_action(self):
        msg = _format_message(MULTI_RESULTS)
        assert "Buy dips" in msg

    def test_macro_vix_present(self):
        msg = _format_message(MULTI_RESULTS)
        assert "VIX 18.5" in msg

    def test_macro_10y_present(self):
        msg = _format_message(MULTI_RESULTS)
        assert "10Y 4.2%" in msg

    def test_vix_label_in_macro(self):
        msg = _format_message(MULTI_RESULTS)
        assert "Low Fear" in msg

    def test_dashboard_url_present(self):
        msg = _format_message(MULTI_RESULTS)
        assert "http://localhost:8000" in msg

    def test_bull_emoji_for_high_score(self):
        msg = _format_message(MULTI_RESULTS)
        # AAPL has score 72 — should show green circle
        assert "🟢" in msg

    def test_bear_emoji_for_low_score(self):
        msg = _format_message(MULTI_RESULTS)
        # BTC-USD has score 38 — should show red circle
        assert "🔴" in msg

    def test_neutral_emoji_for_mid_score(self):
        msg = _format_message(MULTI_RESULTS)
        # TSLA has score 55 — should show white circle
        assert "⚪" in msg

    def test_single_ticker_no_crash(self):
        msg = _format_message([make_result("NVDA", 70)])
        assert "NVDA" in msg
        assert "Top signal: NVDA" in msg

    def test_missing_vix_shows_dash(self):
        r = make_result("AAPL", 70)
        r["macro"].pop("vix")
        msg = _format_message([r])
        assert "VIX —" in msg

    def test_missing_us10y_shows_dash(self):
        r = make_result("AAPL", 70)
        r["macro"].pop("us10y")
        msg = _format_message([r])
        assert "10Y —" in msg

    def test_no_suggested_action_still_formats(self):
        r = make_result("AAPL", 70)
        r["analysis"].pop("suggested_action")
        msg = _format_message([r])
        assert "Top signal: AAPL" in msg


# ── send_whatsapp_summary ─────────────────────────────────────────────────────

VALID_KEYS = {
    "twilio_account_sid": "ACtest123",
    "twilio_auth_token":  "authtokentest",
    "twilio_from":        "whatsapp:+14155238886",
    "whatsapp_to":        "whatsapp:+61400000000",
}


class TestSendWhatsappSummary:
    def test_skips_when_sid_not_configured(self, caplog):
        keys = {**VALID_KEYS, "twilio_account_sid": "YOUR_TWILIO_ACCOUNT_SID"}
        with patch("pipeline.config.API_KEYS", keys):
            with caplog.at_level(logging.WARNING, logger="pipeline.notifier"):
                send_whatsapp_summary(MULTI_RESULTS)
        assert any("not configured" in r.message for r in caplog.records)

    def test_skips_when_token_not_configured(self, caplog):
        keys = {**VALID_KEYS, "twilio_auth_token": "YOUR_TWILIO_AUTH_TOKEN"}
        with patch("pipeline.config.API_KEYS", keys):
            with caplog.at_level(logging.WARNING, logger="pipeline.notifier"):
                send_whatsapp_summary(MULTI_RESULTS)
        assert any("not configured" in r.message for r in caplog.records)

    def test_skips_when_to_not_configured(self, caplog):
        keys = {**VALID_KEYS, "whatsapp_to": "whatsapp:+YOUR_MOBILE_NUMBER"}
        with patch("pipeline.config.API_KEYS", keys):
            with caplog.at_level(logging.WARNING, logger="pipeline.notifier"):
                send_whatsapp_summary(MULTI_RESULTS)
        assert any("not configured" in r.message for r in caplog.records)

    def test_skips_when_results_empty(self, caplog):
        with patch("pipeline.config.API_KEYS", VALID_KEYS):
            with caplog.at_level(logging.WARNING, logger="pipeline.notifier"):
                send_whatsapp_summary([])
        assert any("No pipeline results" in r.message for r in caplog.records)

    def test_sends_when_credentials_valid(self):
        mock_client = MagicMock()
        mock_cls    = MagicMock(return_value=mock_client)
        with patch("pipeline.config.API_KEYS", VALID_KEYS), \
             patch("pipeline.notifier.TwilioClient", mock_cls):
            send_whatsapp_summary(MULTI_RESULTS)
        mock_cls.assert_called_once_with(
            VALID_KEYS["twilio_account_sid"], VALID_KEYS["twilio_auth_token"]
        )
        mock_client.messages.create.assert_called_once()

    def test_skips_gracefully_when_twilio_raises(self, caplog):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("Network error")
        mock_cls = MagicMock(return_value=mock_client)
        with patch("pipeline.config.API_KEYS", VALID_KEYS), \
             patch("pipeline.notifier.TwilioClient", mock_cls):
            with caplog.at_level(logging.WARNING, logger="pipeline.notifier"):
                send_whatsapp_summary(MULTI_RESULTS)
        assert any("notification failed" in r.message for r in caplog.records)

    def test_pipeline_does_not_crash_on_twilio_exception(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("Twilio down")
        mock_cls = MagicMock(return_value=mock_client)
        with patch("pipeline.config.API_KEYS", VALID_KEYS), \
             patch("pipeline.notifier.TwilioClient", mock_cls):
            send_whatsapp_summary(MULTI_RESULTS)  # must not raise
