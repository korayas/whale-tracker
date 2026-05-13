# ============================================================
#  pipeline/data_feed.py
#  Matriks IQ Python API bağlantısı ve veri akışı yöneticisi
# ============================================================

import time
import logging
from typing import Optional
from config import MATRIKS_API_KEY, MATRIKS_HOST, MATRIKS_PORT, WATCHLIST

logger = logging.getLogger(__name__)


class MatriksDataFeed:
    """
    Matriks IQ API ile sürekli veri akışı sağlar.
    Gerçek API mevcut değilse mock veri üretir (geliştirme modu).
    """

    def __init__(self, mock: bool = False):
        self.mock   = mock
        self.client = None
        self._connected = False

    # ----------------------------------------------------------
    # Bağlantı Yönetimi
    # ----------------------------------------------------------

    def connect(self) -> bool:
        """API bağlantısını başlatır. Başarıda True döner."""
        if self.mock:
            logger.info("[DataFeed] MOCK modu aktif — gerçek API kullanılmıyor.")
            self._connected = True
            return True

        try:
            # Gerçek Matriks IQ bağlantısı (IQAlgo modülü kuruluysa aktif olur)
            import MatriksIQ as miq  # type: ignore
            self.client = miq.MatriksIQ(
                api_key = MATRIKS_API_KEY,
                host    = MATRIKS_HOST,
                port    = MATRIKS_PORT,
            )
            self.client.connect()
            self._connected = True
            logger.info("[DataFeed] Matriks IQ bağlantısı başarılı.")
            return True

        except ImportError:
            logger.warning("[DataFeed] MatriksIQ modülü bulunamadı. Mock moduna geçiliyor.")
            self.mock = True
            self._connected = True
            return True

        except Exception as exc:
            logger.error(f"[DataFeed] Bağlantı hatası: {exc}")
            self._connected = False
            return False

    def disconnect(self):
        """API bağlantısını kapatır."""
        if self.client:
            try:
                self.client.disconnect()
            except Exception:
                pass
        self._connected = False
        logger.info("[DataFeed] Bağlantı kapatıldı.")

    # ----------------------------------------------------------
    # Ana Veri Çekme Metodu
    # ----------------------------------------------------------

    def fetch_all(self, tickers: Optional[list] = None) -> dict:
        """
        Tüm hisseler için ham veri paketini döner.

        Dönen yapı:
        {
            "THYAO": {
                "price":         float,
                "volume":        float,  # Lot cinsinden
                "bid_depth":     list,   # [(fiyat, lot), ...]
                "ask_depth":     list,
                "float_lots":    float,  # Fiili dolaşım
                "akd":           dict,   # AKD ham verisi
                "index_perf":    float,  # Endeks % değişimi
            },
            ...
        }
        """
        if not self._connected:
            logger.error("[DataFeed] Bağlı değil. fetch_all() çağrılamaz.")
            return {}

        tickers = tickers or WATCHLIST

        if self.mock:
            return self._mock_data(tickers)

        raw = {}
        for ticker in tickers:
            try:
                raw[ticker] = self._fetch_single(ticker)
            except Exception as exc:
                logger.warning(f"[DataFeed] {ticker} verisi alınamadı: {exc}")

        return raw

    # ----------------------------------------------------------
    # Gerçek API Çağrısı (Tekli Hisse)
    # ----------------------------------------------------------

    def _fetch_single(self, ticker: str) -> dict:
        """Tek hisse için Matriks IQ API'sinden veri çeker."""
        quote  = self.client.get_quote(ticker)
        depth  = self.client.get_depth(ticker)
        akd    = self.client.get_akd(ticker)
        floats = self.client.get_float(ticker)

        return {
            "price":      float(quote.get("last_price", 0)),
            "volume":     float(quote.get("volume_lot", 0)),
            "bid_depth":  [(d["price"], d["lot"]) for d in depth.get("bids", [])],
            "ask_depth":  [(d["price"], d["lot"]) for d in depth.get("asks", [])],
            "float_lots": float(floats.get("float_lot", 1)),
            "akd":        akd,
            "index_perf": float(quote.get("index_change_pct", 0)),
        }

    # ----------------------------------------------------------
    # Mock Veri Üreteci (Geliştirme / Test Modu)
    # ----------------------------------------------------------

    def _mock_data(self, tickers: list) -> dict:
        """
        Gerçekçi rastgele mock veri üretir.
        Gerçek API olmadan modülleri test etmek için kullanılır.
        """
        import random

        mock_result = {}
        for ticker in tickers:
            price      = round(random.uniform(10, 500), 2)
            volume     = random.randint(100_000, 5_000_000)
            float_lots = random.randint(1_000_000, 20_000_000)
            net_lot    = random.randint(-200_000, 500_000)
            cost_basis = round(price * random.uniform(0.85, 1.05), 2)

            mock_result[ticker] = {
                "price":      price,
                "volume":     float(volume),
                "bid_depth":  [(round(price - i * 0.1, 2), random.randint(1000, 50000)) for i in range(1, 6)],
                "ask_depth":  [(round(price + i * 0.1, 2), random.randint(1000, 50000)) for i in range(1, 6)],
                "float_lots": float(float_lots),
                "akd": {
                    "net_lot":    net_lot,
                    "cost_basis": cost_basis,
                    "buyer_institutions":  [f"KURUM_{j}" for j in range(1, random.randint(2, 6))],
                    "seller_institutions": [f"KURUM_{j}" for j in range(6, random.randint(7, 10))],
                },
                "index_perf": round(random.uniform(-3.0, 3.0), 2),
            }

        logger.debug(f"[DataFeed] Mock veri üretildi: {list(mock_result.keys())}")
        return mock_result
