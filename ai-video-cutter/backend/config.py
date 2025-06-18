import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "cok-gizli-bir-anahtar") # Flask oturumları için
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get("UPLOAD_FOLDER", "video_processing/uploads"))
    PROCESSED_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.environ.get("PROCESSED_FOLDER", "video_processing/processed"))
    # Gemini model adı
    GEMINI_MODEL = "gemini-1.5-flash"
    # Gemini için sistem promptu
    GEMINI_SYSTEM_PROMPT = """
    Sen, 'Klip Asistanı' adında uzman bir video editörüsün. Görevin, kullanıcının komutlarını anlayıp sağlanan videodan kesilecek anları belirlemektir. Cevapların daima iki kısımdan oluşmalı: 1. `cuts` adında bir anahtar altında kesimler için geçerli bir JSON zaman damgası dizisi. Dizideki her öğe `{"start": "00:00:05", "end": "00:00:10"}` formatında saniye veya dakika:saniye veya saat:dakika:saniye olabilir. 2. `message` adında bir anahtar altında kullanıcıya yönelik dostça bir mesaj. Kullanıcının komutu anlamsızsa veya video içeriğiyle alakasızsa, `cuts` dizisini boş bırak ([]) ve bunu `message` içinde kibarca belirt. Zaman damgaları videonun süresini aşmamalıdır.
    """
    # Konuşma geçmişini saklamak için Redis anahtar formatı
    REDIS_CHAT_HISTORY_KEY = "chat_history:{}" # {video_id} formatlanacak


