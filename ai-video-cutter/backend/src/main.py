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
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    if file:
        video_id = str(uuid.uuid4())
        filename = f"{video_id}_{file.filename}"
        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        video_path = os.path.join(upload_folder, filename)
        file.save(video_path)

        # Celery görevini başlat
        from tasks import analyze_video
        analyze_video.delay(video_path, video_id)

        return jsonify({"message": "Video yüklendi ve analiz başlatıldı", "video_id": video_id}), 202

@app.route("/api/status/<video_id>", methods=["GET"])
def get_status(video_id):
    from tasks import celery_app
    task = celery_app.AsyncResult(video_id)
    if task.state == "PENDING":
        response = {
            "state": task.state,
            "status": "Görev henüz başlamadı veya kuyrukta."
        }
    elif task.state == "PROGRESS":
        response = {
            "state": task.state,
            "status": task.info.get("status", "İşlem devam ediyor...")
        }
    elif task.state == "SUCCESS":
        response = {
            "state": task.state,
            "status": "İşlem başarıyla tamamlandı.",
            "result": task.result
        }
    elif task.state == "FAILURE":
        response = {
            "state": task.state,
            "status": "İşlem başarısız oldu.",
            "error": str(task.info)
        }
    else:
        response = {
            "state": task.state,
            "status": "Bilinmeyen durum."
        }
    return jsonify(response)

@app.route("/api/chat/<video_id>", methods=["POST"])
def handle_chat(video_id):
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "Message not provided"}), 400

    from tasks import process_chat_command, redis_client
    from config import Config
    import json

    chat_history_key = Config.REDIS_CHAT_HISTORY_KEY.format(video_id)
    current_history_json = redis_client.get(chat_history_key)
    current_history = []
    if current_history_json:
        current_history = json.loads(current_history_json)

    # Get video path (assuming it's stored somewhere or passed)
    # For now, let's assume video_path can be retrieved from a global store or passed from frontend
    # In a real app, you'd likely store this in a database or a more robust state management system
    # For this example, we'll assume the video_path is available from the initial upload task result
    # This is a simplification; a more robust solution would involve storing video metadata.
    # For now, we'll just pass a placeholder video_path.
    video_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{video_id}_*.mp4") # This needs to be more precise
    # A better way would be to store the actual filename in Redis or a database when uploaded.
    # For now, let's just assume we can find it.
    # Let's refine this: the analyze_video task should return the actual video_path and store it.
    # For now, we'll just use a dummy path and focus on the chat logic.

    # Add user message to history before sending to Celery
    current_history.append({"role": "user", "parts": [{"text": user_message}]})

    # Trigger Celery task for chat processing
    task = process_chat_command.delay(video_path, video_id, user_message, current_history)

    # Update Redis with the new history (including user's message)
    redis_client.set(chat_history_key, json.dumps(current_history))

    return jsonify({"message": "Sohbet mesajı alındı ve işleniyor", "task_id": task.id}), 202

@app.route("/api/finalize", methods=["POST"])
def finalize_video():
    data = request.json
    video_id = data.get("video_id")
    cuts = data.get("cuts")

    if not video_id or not cuts:
        return jsonify({"error": "video_id and cuts are required"}), 400

    # Retrieve the original video path. This is a simplification.
    # In a real application, you would store video metadata (including its path) in a database
    # or a more persistent storage solution associated with the video_id.
    # For now, we'll assume the video is in the UPLOAD_FOLDER and try to find it.
    # A more robust solution would be to pass the actual video_path from the upload step.
    upload_folder = app.config["UPLOAD_FOLDER"]
    video_files = [f for f in os.listdir(upload_folder) if f.startswith(video_id)]
    if not video_files:
        return jsonify({"error": "Original video not found for this video_id"}), 404
    original_video_path = os.path.join(upload_folder, video_files[0])

    output_filename = f"final_{video_id}.mp4"
    output_path = os.path.join(app.config["PROCESSED_FOLDER"], output_filename)

    from tasks import finalize_video_task
    task = finalize_video_task.delay(original_video_path, output_path, cuts)

    return jsonify({"message": "Video sonlandırma görevi başlatıldı", "task_id": task.id, "output_path": output_path}), 202

# --- Uygulamayı Çalıştırma ---
if __name__ == '__main__':
    # Gerekli klasörleri oluştur
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['PROCESSED_FOLDER'], exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)

