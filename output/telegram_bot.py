# ============================================================
#  output/telegram_bot.py
#  Telegram Alarm ve Bildirim Modülü:
#  Eşik değeri geçen hisseler için anlık sinyal mesajı gönderir.
#  Mesaj içinde "Neden bu hisse?" sorusuna yanıt verir.
# ============================================================

import logging
import urllib.request
import urllib.parse
import json
from datetime import datetime
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, OUTPUT
from engine.alpas import ALPASEngine

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramBot:
    """
    Telegram Bot API üzerinden sinyal mesajı gönderir.
    parse_mode=MarkdownV2 ile zengin formatlı mesajlar desteklenir.
    """

    def __init__(self):
        self.enabled = OUTPUT.get("telegram_enabled", True)
        self._base_url = TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN)

    # ----------------------------------------------------------
    # Ana Sinyal Gönderici
    # ----------------------------------------------------------

    def send_signal(self, ticker: str, score_data: dict,
                    weights: dict, gatekeeper_summary: dict) -> bool:
        """
        Balina sinyali tespit edildiğinde çağrılır.
        Parametreler:
          ticker           : Hisse sembolü (örn: "THYAO")
          score_data       : ALPAS sonucu (alpas_score, rank, weight_impact, ...)
          weights          : LOPCOW anlık ağırlıkları
          gatekeeper_summary: Filtre sonuçları özeti
        """
        if not self.enabled:
            logger.debug("[Telegram] Bildirimler kapalı.")
            return False

        message = self._build_message(ticker, score_data, weights, gatekeeper_summary)

        try:
            return self._send(message)
        except Exception as exc:
            logger.error(f"[Telegram] Gönderim hatası: {exc}")
            return False

    def send_signals_batch(self, signals: list) -> None:
        """
        Birden fazla sinyal hissesi varsa sırayla gönderir.
        signals: [{"ticker": ..., "score_data": ..., ...}, ...]
        """
        for item in signals:
            self.send_signal(
                ticker             = item["ticker"],
                score_data         = item["score_data"],
                weights            = item["weights"],
                gatekeeper_summary = item.get("gatekeeper_summary", {}),
            )

    # ----------------------------------------------------------
    # Mesaj Oluşturucu
    # ----------------------------------------------------------

    def _build_message(self, ticker: str, score_data: dict,
                        weights: dict, gk: dict) -> str:
        """
        Okunabilir, bilgi yüklü Telegram mesajı oluşturur.

        Örnek çıktı:
        ═══════════════════════
        🐋 BALINA TESPİTİ
        ═══════════════════════
        📌 Hisse : THYAO
        🏆 ALPAS Skor : 0.9200
        📊 Sıralama  : #1
        ...
        """
        alpas     = score_data.get("alpas_score", 0)
        rank      = score_data.get("rank", "?")
        d_plus    = score_data.get("d_plus", 0)
        d_minus   = score_data.get("d_minus", 0)
        now       = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        # Kriter etki dökümü
        explanation = ALPASEngine.build_explanation(ticker, score_data, weights)

        # Gatekeeper özeti
        anti_flip_ok  = gk.get("anti_flip_passed", True)
        sector_risk   = gk.get("sector_risk_level", "LOW")
        z_score       = gk.get("z_score", 0)
        manip_risk    = gk.get("manipulation_risk", False)

        flip_icon  = "✅" if anti_flip_ok else "⚠️"
        manip_icon = "🔴 RİSK" if manip_risk else "🟢 Temiz"

        message = (
            f"╔══════════════════════╗\n"
            f"║  🐋  BALINA TESPİTİ  ║\n"
            f"╚══════════════════════╝\n"
            f"\n"
            f"📌 *Hisse*     : `{ticker}`\n"
            f"🕐 *Saat*      : `{now}`\n"
            f"🏆 *ALPAS Skor*: `{alpas:.4f}`\n"
            f"📊 *Sıralama*  : `#{rank}`\n"
            f"📐 *d⁺*        : `{d_plus:.4f}`\n"
            f"📐 *d⁻*        : `{d_minus:.4f}`\n"
            f"\n"
            f"─────────────────────────\n"
            f"{explanation}\n"
            f"─────────────────────────\n"
            f"\n"
            f"🛡️ *Gatekeeper Sonuçları:*\n"
            f"  {flip_icon} Kurum Karakteri: "
            f"`{'Kalıcı Alıcı' if anti_flip_ok else 'Günlükçü Uyarısı'}`\n"
            f"  📡 Sektör Riski : `{sector_risk}`\n"
            f"  📊 Z-Score      : `{z_score:.2f}`\n"
            f"  🔍 Manipülasyon : {manip_icon}\n"
        )

        return message

    # ----------------------------------------------------------
    # HTTP Gönderici
    # ----------------------------------------------------------

    def _send(self, text: str) -> bool:
        """Telegram Bot API'ye HTTP POST isteği atar."""
        payload = {
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       text,
            "parse_mode": "Markdown",
        }
        data    = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(self._base_url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                logger.info(f"[Telegram] Mesaj gönderildi ✓")
                return True
            else:
                logger.warning(f"[Telegram] API hatası: {result}")
                return False

    # ----------------------------------------------------------
    # Test Mesajı
    # ----------------------------------------------------------

    def send_test(self) -> bool:
        """Bot bağlantısını test eder."""
        test_msg = (
            "🤖 *Whale Tracker* başlatıldı!\n"
            f"🕐 `{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}`\n"
            "✅ Sistem hazır, piyasa izleniyor..."
        )
        try:
            return self._send(test_msg)
        except Exception as exc:
            logger.error(f"[Telegram] Test mesajı gönderilemedi: {exc}")
            return False
