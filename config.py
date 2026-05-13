# ============================================================
#  🐋 Whale Tracker — Konfigürasyon Dosyası
#  Tüm sabit değerler, API anahtarları ve eşik değerleri
# ============================================================

# -----------------------------------------------------------
# Matriks IQ API Ayarları
# -----------------------------------------------------------
MATRIKS_API_KEY = "YOUR_MATRIKS_API_KEY"   # Matriks IQ API anahtarınızı buraya girin
MATRIKS_HOST    = "localhost"               # IQAlgo host adresi
MATRIKS_PORT    = 11223                     # IQAlgo varsayılan port

# -----------------------------------------------------------
# Telegram Bot Ayarları
# -----------------------------------------------------------
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID   = "YOUR_CHAT_ID"

# -----------------------------------------------------------
# Tarama Parametreleri
# -----------------------------------------------------------
LOOP_INTERVAL_SECONDS = 10          # Her döngü arası bekleme süresi (saniye)

# Takip edilecek hisseler (boş bırakılırsa tüm BIST hisseleri)
WATCHLIST = [
    "THYAO", "ASELS", "GARAN", "AKBNK", "SISE",
    "EREGL", "KCHOL", "TOASO", "ARCLK", "BIMAS"
]

# -----------------------------------------------------------
# Sektör → Endeks Eşleştirmesi
# -----------------------------------------------------------
SECTOR_INDEX_MAP = {
    "THYAO": "XULAŞ",
    "ASELS": "XSAVS",
    "GARAN": "XBANK",
    "AKBNK": "XBANK",
    "SISE":  "XKMY",
    "EREGL": "XMANA",
    "KCHOL": "XHOLD",
    "TOASO": "XMESY",
    "ARCLK": "XELKT",
    "BIMAS": "XGIDA",
}

# -----------------------------------------------------------
# LOPCOW Motoru Parametreleri
# -----------------------------------------------------------
LOPCOW_EPSILON = 1e-6       # Log(0) hatasını önlemek için küçük sabit

# Normalizasyon kriterleri yönü: True=Yüksek iyi, False=Düşük iyi
CRITERIA_DIRECTION = {
    "volume":              True,   # Yüksek hacim → iyi
    "net_lot":             True,   # Yüksek net alım lotu → iyi
    "float_ratio":         True,   # Yüksek tahta hakimiyeti → iyi
    "absorption_velocity": True,   # Yüksek emir hızı → iyi
    "cost_basis_gap":      True,   # Maliyet/Fiyat farkı → iyi
    "index_performance":   True,   # Endeks desteği → iyi
}

# -----------------------------------------------------------
# ALPAS Motoru Parametreleri
# -----------------------------------------------------------
ALPAS_SIGNAL_THRESHOLD = 0.85   # Bu değerin üzerindeki hisseler alarm üretir

# -----------------------------------------------------------
# Gatekeeper Filtre Parametreleri
# -----------------------------------------------------------
GATEKEEPER = {
    "anti_flip": {
        "lookback_days":     10,     # Geriye dönük analiz gün sayısı
        "consistency_ratio": 0.6,    # %60+ tutarlılık → kalıcı alıcı
    },
    "sector_check": {
        "min_correlation":  0.30,    # Pearson r minimum eşiği
        "lookback_minutes": 60,      # Endeks korelasyon penceresi (dakika)
    },
    "zscore_volume": {
        "threshold":        2.0,     # Z > 2 → Anormal hacim
        "lookback_periods": 20,      # Tarihsel periyot sayısı
    },
}

# -----------------------------------------------------------
# CSV Logger Parametreleri
# -----------------------------------------------------------
LOG_DIR          = "data/logs"
LOG_FILE_PREFIX  = "whale_tracker_log"
LOG_ROTATE_DAILY = True        # Her gün yeni dosya oluştur

# -----------------------------------------------------------
# Çıktı Formatı
# -----------------------------------------------------------
OUTPUT = {
    "telegram_enabled":  True,
    "heatmap_enabled":   False,   # Opsiyonel görsel çıktı
    "console_verbose":   True,    # Terminal çıktısı detaylı mı?
}
