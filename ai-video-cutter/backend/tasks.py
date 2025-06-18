from celery import Celery
from config import Config
import os
import subprocess # FFmpeg için
import json # Gemini yanıtını işlemek için
import redis # Konuşma geçmişi için
from google import genai
from google.genai import types

# Celery uygulamasını başlat
celery_app = Celery(
    'video_tasks',
    broker=Config.REDIS_URL,
    backend=Config.REDIS_URL # Görev sonuçlarını saklamak için
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Redis istemcisini başlat
redis_client = redis.from_url(Config.REDIS_URL)

# Gemini istemcisini başlat - Lazy initialization
gemini_client = None

def get_gemini_client():
    global gemini_client
    if gemini_client is None:
        gemini_client = genai.GenerativeModel(model_name=Config.GEMINI_MODEL)
    return gemini_client

# --- Celery Görevleri Tanımlamaları ---

@celery_app.task(name='tasks.analyze_video')
def analyze_video(video_path, video_id):
    """
    Videoyu temel analiz eder (süre, vb.) ve ilk Gemini isteğini hazırlar.
    """
    print(f"Video analiz görevi başladı: {video_id}")
    try:
        # FFprobe ile video süresini al (FFmpeg paketinin bir parçası)
        # Bu sadece bir örnek, daha fazla analiz yapılabilir (ses dökümü vb.)
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        duration = float(result.stdout.strip())
        print(f"Video süresi: {duration} saniye")

        return {"status": "success", "duration": duration}

    except subprocess.CalledProcessError as e:
        print(f"FFprobe hatası: {e}")
        return {"status": "error", "message": f"Video analiz hatası: {e}"}
    except Exception as e:
        print(f"Beklenmedik analiz hatası: {e}")
        return {"status": "error", "message": f"Beklenmedik hata: {e}"}


@celery_app.task(name='tasks.process_chat_command')
def process_chat_command(video_path, video_id, user_message, current_history):
    """
    Kullanıcı mesajını ve geçmişi alıp Gemini'ye gönderir, kesim önerilerini döndürür.
    """
    print(f"Sohbet komut işleme görevi başladı: {video_id}")
    try:
        # Sohbet geçmişini Gemini formatına dönüştür
        formatted_history = []
        for item in current_history:
            role = item["role"]
            parts = []
            for part_data in item["parts"]:
                if "text" in part_data:
                    parts.append(types.Part.from_text(part_data["text"]))
            formatted_history.append(types.Content(role=role, parts=parts))

        # Kullanıcı mesajını ekle
        user_content = types.Content(
            role="user", 
            parts=[types.Part.from_text(user_message)]
        )
        formatted_history.append(user_content)

        # Gemini'ye istek gönder
        model = get_gemini_client()
        chat_session = model.start_chat(history=formatted_history)
        response = chat_session.send_message(user_message)

        # Gemini yanıtını işle
        ai_message = response.text
        
        # Yanıttan JSON formatında kesim önerilerini çıkarmaya çalış
        try:
            # Eğer yanıt JSON formatında ise ayrıştır
            if ai_message.strip().startswith('{') and ai_message.strip().endswith('}'):
                response_data = json.loads(ai_message)
                cuts = response_data.get("cuts", [])
                ai_message = response_data.get("message", ai_message)
            else:
                # JSON formatında değilse, basit bir kesim önerisi formatı kullan
                cuts = []
                ai_message = ai_message
        except json.JSONDecodeError:
            cuts = []

        # AI yanıtını geçmişe ekle
        current_history.append({"role": "user", "parts": [{"text": user_message}]})
        current_history.append({"role": "model", "parts": [{"text": ai_message}]})
        
        # Redis'te geçmişi güncelle
        redis_client.set(Config.REDIS_CHAT_HISTORY_KEY.format(video_id), json.dumps(current_history))

        return {"status": "success", "cuts": cuts, "ai_message": ai_message}

    except Exception as e:
        print(f"Beklenmedik sohbet işleme hatası: {e}")
        ai_message = f"Beklenmedik bir hata oluştu: {e}"
        current_history.append({"role": "user", "parts": [{"text": user_message}]})
        current_history.append({"role": "model", "parts": [{"text": ai_message}]})
        redis_client.set(Config.REDIS_CHAT_HISTORY_KEY.format(video_id), json.dumps(current_history))
        return {"status": "error", "message": ai_message, "cuts": []}


@celery_app.task(name='tasks.finalize_video_task')
def finalize_video_task(video_path, output_path, cuts):
    """
    Verilen kesimlere göre videoyu FFmpeg ile keser ve birleştirir.
    """
    print(f"Video sonlandırma görevi başladı: {video_path}")
    try:
        # FFmpeg komutunu oluştur
        # Karmaşık filtre grafiği kullanılarak birden fazla kesim birleştirilebilir.
        # Basitlik adına, her kesimi ayrı ayrı işleyip sonra birleştirelim veya
        # doğrudan karmaşık bir komut oluşturalım.
        # Örnek: -ss [start] -to [end] -i input.mp4 -c copy output.mp4

        # Geçici dosyaları saklamak için bir dizin oluştur
        temp_dir = os.path.join(os.path.dirname(output_path), "temp_segments")
        os.makedirs(temp_dir, exist_ok=True)

        segment_files = []
        for i, cut in enumerate(cuts):
            start_time = cut["start"]
            end_time = cut["end"]
            segment_output_path = os.path.join(temp_dir, f"segment_{i}.mp4")

            cmd = [
                "ffmpeg",
                "-y",  # Otomatik üzerine yazma
                "-ss", str(start_time),
                "-to", str(end_time),
                "-i", video_path,
                "-c", "copy",
                segment_output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            segment_files.append(segment_output_path)

        # Segmentleri birleştir
        if len(segment_files) > 1:
            concat_list_path = os.path.join(temp_dir, "concat_list.txt")
            with open(concat_list_path, "w") as f:
                for segment_file in segment_files:
                    f.write(f"file \'{segment_file}\'\n")

            concat_cmd = [
                "ffmpeg",
                "-y",  # Otomatik üzerine yazma
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                output_path
            ]
            subprocess.run(concat_cmd, check=True, capture_output=True)
        elif len(segment_files) == 1:
            os.rename(segment_files[0], output_path)
        else:
            return {"status": "error", "message": "Kesim bulunamadı."}

        # Geçici dosyaları temizle
        for f in segment_files:
            os.remove(f)
        os.remove(concat_list_path)
        os.rmdir(temp_dir)

        print(f"Video sonlandırma tamamlandı: {output_path}")
        return {"status": "success", "output_path": output_path}

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg hatası: {e.stderr.decode()}")
        return {"status": "error", "message": f"Video işleme hatası: {e.stderr.decode()}"}
    except Exception as e:
        print(f"Beklenmedik sonlandırma hatası: {e}")
        return {"status": "error", "message": f"Beklenmedik hata: {e}"}



