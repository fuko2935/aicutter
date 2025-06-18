# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import uuid # Video ID'leri için
import time # Durum takibi için basit bir örnek
from config import Config

# Ortam değişkenlerini yükle
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config) # Yapılandırmayı yükle
CORS(app) # Frontend'den gelen isteklere izin ver

# Basit bir durum takip sistemi (Redis/Celery entegrasyonundan önce)
# Gerçek uygulamada Redis veya veritabanı kullanılacak
video_status = {}
chat_histories = {} # video_id: [{"role": "user", "parts": [...]}, ...]

@app.route('/')
def index():
    return "AI Video Cutter Backend Çalışıyor!"

# --- API Endpoints (Placeholder - Detaylar sonraki adımlarda) ---

@app.route("/api/upload", methods=["POST"])
def upload_video():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file part in the request"}), 400
        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No selected file"}), 400
        if file:
            video_id = str(uuid.uuid4())
            filename = f"{video_id}_{file.filename}"
            upload_folder = app.config.get("UPLOAD_FOLDER", "/tmp/uploads")
            os.makedirs(upload_folder, exist_ok=True)
            video_path = os.path.join(upload_folder, filename)
            file.save(video_path)

            # Basit bir başarı simülasyonu (Celery olmadan)
            video_status[video_id] = {
                "state": "SUCCESS",
                "status": "Video başarıyla yüklendi ve analiz edildi",
                "video_path": video_path
            }
            app.logger.info(f"Video uploaded: {video_id}, path: {video_path}")

            return jsonify({"message": "Video yüklendi ve analiz başlatıldı", "video_id": video_id}), 202
    except Exception as e:
        return jsonify({"error": f"Upload error: {str(e)}"}), 500

@app.route("/api/status/<video_id>", methods=["GET"])
def get_status(video_id):
    try:
        if video_id in video_status:
            return jsonify(video_status[video_id])
        else:
            return jsonify({
                "state": "PENDING",
                "status": "Video bulunamadı veya henüz işlenmedi"
            })
    except Exception as e:
        return jsonify({
            "state": "FAILURE",
            "status": f"Status check error: {str(e)}"
        }), 500

@app.route("/api/video/<video_id>", methods=["GET"])
def serve_video(video_id):
    """Video dosyalarını serve etmek için endpoint"""
    try:
        if video_id in video_status and "video_path" in video_status[video_id]:
            video_path = video_status[video_id]["video_path"]
            if os.path.exists(video_path):
                from flask import send_file
                return send_file(video_path, as_attachment=True)
            else:
                return jsonify({"error": "Video file not found"}), 404
        else:
            return jsonify({"error": "Video not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Video serve error: {str(e)}"}), 500
@app.route("/api/chat/<video_id>", methods=["POST"])
def handle_chat(video_id):
    try:
        user_message = request.json.get("message")
        if not user_message:
            return jsonify({"error": "Message not provided"}), 400

        # Gemini API key kontrolü
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return jsonify({"error": "Gemini API key not configured"}), 500

        # Gemini'yi yapılandır
        from google import genai
        
        # Gemini client oluştur
        client = genai.Client(api_key=api_key)
        
        # Video bilgilerini al
        if video_id in video_status and "video_path" in video_status[video_id]:
            video_path = video_status[video_id]["video_path"]
        else:
            return jsonify({"error": "Video not found"}), 404

        # Video süresini al
        try:
            import subprocess
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
        except:
            duration = 120  # Varsayılan süre

        # Gemini modeli oluştur
        model = "gemini-2.5-flash"
        
        # Sistem promptu
        system_prompt = f"""
        Sen, 'Klip Asistanı' adında uzman bir video editörüsün. Görevin, kullanıcının komutlarını anlayıp sağlanan videodan kesilecek anları belirlemektir. 
        
        Video süresi: {duration:.1f} saniye
        
        Cevapların daima JSON formatında olmalı ve şu yapıda olmalı:
        {{
            "ai_message": "Kullanıcıya yönelik dostça mesaj",
            "cuts": [
                {{"start": "00:00:05", "end": "00:00:15"}},
                {{"start": "00:00:30", "end": "00:00:45"}}
            ]
        }}
        
        Zaman formatı HH:MM:SS veya MM:SS veya SS olabilir. Zaman damgaları videonun süresini ({duration:.1f} saniye) aşmamalıdır.
        Kullanıcının komutu anlamsızsa veya video içeriğiyle alakasızsa, cuts dizisini boş bırak.
        """
        
        # Gemini Files API kullanarak videoyu yükle
        from google.genai import types
        
        # Video dosyasını Gemini'ye yükle
        with open(video_path, 'rb') as video_file:
                         uploaded_file = client.files.upload(file=video_path)
        
        # Dosyanın işlenmesini bekle
        import time
        while uploaded_file.state == "PROCESSING":
            time.sleep(1)
            uploaded_file = client.files.get(name=uploaded_file.name)
        
        if uploaded_file.state == "FAILED":
            return jsonify({"error": "Video upload failed"}), 500
        
        # Gemini'ye istek gönder
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        file_data=types.FileData(
                            file_uri=uploaded_file.uri,
                            mime_type=uploaded_file.mime_type
                        ),
                        video_metadata=types.VideoMetadata(
                            fps=15, # Varsayılan olarak 15 FPS kullanıyorum
                        ),
                    ),
                    types.Part.from_text(text=f"{system_prompt}\n\nKullanıcı mesajı: {user_message}")
                ]
            )
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json"
        )
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config
        )
        
        ai_response_text = response.text
        
        # JSON yanıtını ayrıştır
        try:
            import json
            # JSON'u temizle (markdown formatından çıkar)
            if "```json" in ai_response_text:
                ai_response_text = ai_response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in ai_response_text:
                ai_response_text = ai_response_text.split("```")[1].strip()
            
            ai_response = json.loads(ai_response_text)
            ai_message = ai_response.get("ai_message", "Merhaba! Size nasıl yardımcı olabilirim?")
            cuts = ai_response.get("cuts", [])
        except:
            # JSON ayrıştırma başarısız olursa varsayılan yanıt
            ai_message = ai_response_text
            cuts = []

        # Yüklenen dosyayı temizle
        try:
            client.files.delete(name=uploaded_file.name)
        except:
            pass  # Dosya silme hatası önemli değil

        # Task sonucunu sakla
        task_id = str(uuid.uuid4())
        video_status[task_id] = {
            "state": "SUCCESS",
            "status": "Chat işlemi tamamlandı",
            "result": {
                "ai_message": ai_message,
                "cuts": cuts
            }
        }

        return jsonify({"message": "Sohbet mesajı alındı ve işleniyor", "task_id": task_id}), 202
    except Exception as e:
        return jsonify({"error": f"Chat error: {str(e)}"}), 500

@app.route("/api/finalize", methods=["POST"])
def finalize_video():
    try:
        data = request.json
        video_id = data.get("video_id")
        cuts = data.get("cuts")

        if not video_id or not cuts:
            return jsonify({"error": "video_id and cuts are required"}), 400

        # Video kesme işlemini başlat
        try:
            import subprocess
            input_video_path = video_status[video_id]["video_path"]
            processed_folder = app.config.get("PROCESSED_FOLDER", "/tmp/processed")
            
            # Kesilen parçaları saklamak için geçici klasör
            temp_cuts_folder = os.path.join(processed_folder, video_id)
            os.makedirs(temp_cuts_folder, exist_ok=True)

            concat_list_path = os.path.join(temp_cuts_folder, "concat_list.txt")
            with open(concat_list_path, "w") as f:
                for i, cut in enumerate(cuts):
                    start_time = cut["start"]
                    end_time = cut["end"]
                    segment_output_path = os.path.join(temp_cuts_folder, f"segment_{i}.mp4")
                    
                    # Her bir kesimi ayrı ayrı işle
                    segment_command = [
                        "ffmpeg",
                        "-i", input_video_path,
                        "-ss", start_time,
                        "-to", end_time,
                        "-c", "copy",
                        segment_output_path
                    ]
                    subprocess.run(segment_command, check=True)
                    f.write(f"file {os.path.basename(segment_output_path)}\n")

            final_output_path = os.path.join(processed_folder, f"final_{video_id}.mp4")
            
            # Kesilen parçaları birleştir
            concat_command = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", concat_list_path,
                "-c", "copy",
                final_output_path
            ]
            subprocess.run(concat_command, check=True)

            video_status[task_id] = {
                "state": "SUCCESS",
                "status": "Video başarıyla işlendi",
                "output_path": final_output_path
            }

        except Exception as ffmpeg_error:
            video_status[task_id] = {
                "state": "FAILURE",
                "status": f"Video işleme hatası: {str(ffmpeg_error)}"
            }
            return jsonify({"error": f"Video processing error: {str(ffmpeg_error)}"}), 500

        return jsonify({"message": "Video sonlandırma görevi başlatıldı", "task_id": task_id, "output_path": output_path}), 202
    except Exception as e:
        return jsonify({"error": f"Finalize error: {str(e)}"}), 500

# --- Uygulamayı Çalıştırma ---
if __name__ == '__main__':
    # Gerekli klasörleri oluştur
    upload_folder = "/tmp/uploads"
    processed_folder = "/tmp/processed"
    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(processed_folder, exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)

