# AI Video Cutter

AI Video Cutter, yapay zeka destekli bir video düzenleme uygulamasıdır. Bu uygulama, kullanıcıların videolarını yüklemelerine, AI asistanı ile sohbet ederek video içeriğini anlamalarına ve belirli bölümleri kesip birleştirmelerine olanak tanır.

## Özellikler

- **Video Yükleme**: Kolayca video dosyalarını yükleyin.
- **AI Destekli Sohbet**: Yüklediğiniz videolar hakkında AI asistanına sorular sorun ve video içeriğini daha iyi anlayın.
- **Video Kesme ve Birleştirme**: AI asistanının önerileri doğrultusunda veya kendi belirlediğiniz zaman aralıklarına göre videoları kesin ve birleştirin.
- **İndirme**: İşlenmiş videoları kolayca indirin.

## Kurulum

Projeyi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin:

### Ön Gereksinimler

- Python 3.9+
- Node.js 18+
- npm veya yarn
- FFmpeg (video işleme için)

### Backend Kurulumu

1.  Backend klasörüne gidin:
    ```bash
    cd backend
    ```
2.  Bir sanal ortam oluşturun ve etkinleştirin:
    ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    ```
3.  Gerekli Python paketlerini yükleyin:
    ```bash
    pip install -r requirements.txt
    ```
4.  `.env` dosyasını oluşturun ve Gemini API anahtarınızı ekleyin:
    ```
    GEMINI_API_KEY=sizin_gemini_api_anahtarınız
    ```
5.  Uygulamayı başlatın:
    ```bash
    python app.py
    ```

### Frontend Kurulumu

1.  Frontend klasörüne gidin:
    ```bash
    cd frontend/video-cutter-ui
    ```
2.  Gerekli Node.js paketlerini yükleyin:
    ```bash
    npm install
    # veya yarn install
    ```
3.  Uygulamayı geliştirme modunda başlatın:
    ```bash
    npm run dev
    # veya yarn dev
    ```
    Uygulama genellikle `http://localhost:5173` adresinde çalışacaktır.

### FFmpeg Kurulumu

FFmpeg, video kesme ve birleştirme işlemleri için gereklidir. İşletim sisteminize göre kurulum talimatlarını takip edin:

- **Ubuntu/Debian:**
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
- **macOS (Homebrew ile):**
    ```bash
    brew install ffmpeg
    ```
- **Windows (Chocolatey ile):**
    ```bash
    choco install ffmpeg
    ```

## Kullanım

1.  Uygulamayı başlattıktan sonra tarayıcınızda frontend adresine gidin.
2.  Video yükleme alanına videonuzu sürükleyip bırakın veya seçin.
3.  Video yüklendikten sonra AI asistanı ile sohbet etmeye başlayabilirsiniz.
4.  AI asistanının önerdiği kesimleri kullanabilir veya kendi kesimlerinizi belirleyebilirsiniz.
5.  Videoyu işledikten sonra indirme düğmesine tıklayarak son halini indirebilirsiniz.

## Katkıda Bulunma

Katkılarınızı bekliyoruz! Hata raporları, özellik istekleri veya kod katkıları için lütfen GitHub deposunu ziyaret edin.

## Lisans

Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için `LICENSE` dosyasına bakın.

