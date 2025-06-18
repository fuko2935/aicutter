import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Progress } from '@/components/ui/progress.jsx'
import { Upload, MessageCircle, Scissors, Download, Play, Pause, ArrowRight, CheckCircle } from 'lucide-react'
import './App.css'

function App() {
  const [currentScreen, setCurrentScreen] = useState('upload') // 'upload' or 'chat'
  const [videoFile, setVideoFile] = useState(null)
  const [videoId, setVideoId] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState('')
  const [chatHistory, setChatHistory] = useState([])
  const [currentMessage, setCurrentMessage] = useState('')
  const [suggestedCuts, setSuggestedCuts] = useState([])
  const [finalVideoUrl, setFinalVideoUrl] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const fileInputRef = useRef(null)
  const videoRef = useRef(null)

  const API_BASE_URL = 'https://5000-i7bje6rb4wcdrih1optmr-c579c314.manusvm.computer'

  const handleFileSelect = (event) => {
    const file = event.target.files[0]
    if (file && file.type.startsWith('video/')) {
      setVideoFile(file)
      setVideoId(null)
      setAnalysisStatus('')
      setChatHistory([])
      setSuggestedCuts([])
      setFinalVideoUrl('')
      setUploadProgress(0)
      setIsUploading(false)
    }
  }

  const uploadVideo = async () => {
    if (!videoFile) return

    setIsUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', videoFile)

    try {
      // Simulated progress for better UX
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return prev
          }
          return prev + Math.random() * 10
        })
      }, 200)

      const response = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData
      })

      clearInterval(progressInterval)

      if (response.ok) {
        const result = await response.json()
        console.log('Upload response:', result) // Debug log
        setVideoId(result.video_id)
        setUploadProgress(100)
        setAnalysisStatus("Video başarıyla yüklendi!")
        
        // 2 saniye sonra chat ekranına geç
        setTimeout(() => {
          console.log("Switching to chat screen with video_id:", result.video_id) // Debug log
          setCurrentScreen("chat")
          setAnalysisStatus("Video analiz ediliyor...")
          checkAnalysisStatus(result.video_id)
        }, 2000)
      } else {
        const errorText = await response.text()
        console.error("Upload error:", errorText) // Debug log
        setAnalysisStatus("Video yükleme hatası: " + errorText)
        setUploadProgress(0)
        setIsUploading(false)
      }
    } catch (error) {
      console.error("Upload catch error:", error) // Debug log
      setAnalysisStatus("Bağlantı hatası: " + error.message)
      setUploadProgress(0)
      setIsUploading(false)
    }
  }

  const checkAnalysisStatus = async (id) => {
    console.log("Checking analysis status for video_id:", id) // Debug log
    try {
      const response = await fetch(`${API_BASE_URL}/api/status/${id}`)
      const result = await response.json()
      console.log("Analysis status response:", result) // Debug log
      
      setAnalysisStatus(result.status)
      
      if (result.state === "PENDING" || result.state === "PROGRESS") {
        setTimeout(() => checkAnalysisStatus(id), 2000)
      } else if (result.state === "SUCCESS") {
        setAnalysisStatus("Video analizi tamamlandı! Artık AI asistanıyla sohbet edebilirsiniz.")
        console.log("Analysis successful, ready for chat.") // New debug log
      } else {
        console.error("Analysis status error:", result) // Debug log
        setAnalysisStatus("Video analizi hatası: " + result.status)
      }
    } catch (error) {
      console.error("Analysis status catch error:", error) // Debug log
      setAnalysisStatus("Durum kontrol hatası: " + error.message)
    }
  }

  const sendChatMessage = async () => {
    if (!currentMessage.trim() || !videoId) {
      console.log("Cannot send message: currentMessage or videoId missing.", { currentMessage, videoId }); // New debug log
      return;
    }

    setIsLoading(true)
    const userMessage = currentMessage
    setCurrentMessage("")

    // Kullanıcı mesajını chat geçmişine ekle
    setChatHistory(prev => [...prev, { role: "user", message: userMessage }])
    console.log("Sending message:", userMessage); // New debug log

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/${videoId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: userMessage })
      })

      if (response.ok) {
        const result = await response.json()
        console.log("Chat API response:", result); // New debug log
        
        // Task ID ile sonucu bekle
        setTimeout(() => checkChatResult(result.task_id), 2000)
      } else {
        const errorText = await response.text();
        console.error("Message send error:", errorText); // New debug log
        setChatHistory(prev => [...prev, { role: "assistant", message: "Mesaj gönderme hatası: " + errorText }])
      }
    } catch (error) {
      console.error("Chat send catch error:", error); // New debug log
      setChatHistory(prev => [...prev, { role: "assistant", message: "Bağlantı hatası: " + error.message }])
    } finally {
      setIsLoading(false)
    }
  }

  const checkChatResult = async (taskId) => {
    console.log("Checking chat result for task ID:", taskId); // New debug log
    try {
      const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
      const result = await response.json()
      console.log("Chat result status response:", result); // New debug log
      
      if (result.state === "SUCCESS") {
        const aiResponse = result.result
        setChatHistory(prev => [...prev, { role: "assistant", message: aiResponse.ai_message }])
        
        if (aiResponse.cuts && aiResponse.cuts.length > 0) {
          setSuggestedCuts(aiResponse.cuts)
        }
      } else if (result.state === "PENDING" || result.state === "PROGRESS") {
        setTimeout(() => checkChatResult(taskId), 2000)
      } else {
        console.error("Chat result error:", result); // New debug log
        setChatHistory(prev => [...prev, { role: "assistant", message: "Mesaj işleme hatası: " + result.status }])
      }
    } catch (error) {
      console.error("Chat result catch error:", error); // New debug log
      setChatHistory(prev => [...prev, { role: "assistant", message: "Sonuç kontrol hatası: " + error.message }])
    }
  }

  const finalizeVideo = async () => {
    if (!videoId || suggestedCuts.length === 0) return

    setIsLoading(true)

    try {
      const response = await fetch(`${API_BASE_URL}/api/finalize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          video_id: videoId,
          cuts: suggestedCuts
        })
      })

      if (response.ok) {
        const result = await response.json()
        setAnalysisStatus('Video işleniyor...')
        
        // Finalize durumunu kontrol et
        setTimeout(() => checkFinalizeStatus(result.task_id, result.output_path), 3000)
      } else {
        setAnalysisStatus('Video sonlandırma hatası')
      }
    } catch (error) {
      setAnalysisStatus('Bağlantı hatası: ' + error.message)
    } finally {
      setIsLoading(false)
    }
  }

  const checkFinalizeStatus = async (taskId, outputPath) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/status/${taskId}`)
      const result = await response.json()
      
      if (result.state === 'SUCCESS') {
        setFinalVideoUrl(outputPath)
        setAnalysisStatus('Video başarıyla oluşturuldu!')
      } else if (result.state === 'PENDING' || result.state === 'PROGRESS') {
        setTimeout(() => checkFinalizeStatus(taskId, outputPath), 3000)
      } else {
        setAnalysisStatus('Video işleme hatası')
      }
    } catch (error) {
      setAnalysisStatus('Durum kontrol hatası: ' + error.message)
    }
  }

  const formatTime = (timeStr) => {
    // "00:00:05" formatını "5s" formatına çevir
    const parts = timeStr.split(':')
    if (parts.length === 3) {
      const hours = parseInt(parts[0])
      const minutes = parseInt(parts[1])
      const seconds = parseInt(parts[2])
      
      if (hours > 0) {
        return `${hours}s ${minutes}d ${seconds}s`
      } else if (minutes > 0) {
        return `${minutes}d ${seconds}s`
      } else {
        return `${seconds}s`
      }
    }
    return timeStr
  }

  const goBackToUpload = () => {
    setCurrentScreen('upload')
    setVideoFile(null)
    setVideoId(null)
    setUploadProgress(0)
    setIsUploading(false)
    setAnalysisStatus('')
    setChatHistory([])
    setSuggestedCuts([])
    setFinalVideoUrl('')
  }

  // Upload Screen
  if (currentScreen === 'upload') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
        <div className="max-w-4xl mx-auto">
          <header className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">
              AI Video Cutter
            </h1>
            <p className="text-lg text-gray-600">
              Yapay zeka destekli akıllı video kesici
            </p>
          </header>

          <div className="max-w-2xl mx-auto">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="w-5 h-5" />
                  Video Yükleme
                </CardTitle>
                <CardDescription>
                  Kesilecek videoyu seçin ve yükleyin
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="video/*"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                  <Button
                    onClick={() => fileInputRef.current?.click()}
                    variant="outline"
                    className="mb-4"
                    disabled={isUploading}
                  >
                    Video Seç
                  </Button>
                  <p className="text-sm text-gray-500">
                    MP4, AVI, MOV ve diğer video formatları desteklenir
                  </p>
                </div>

                {videoFile && (
                  <div className="space-y-4">
                    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center gap-3">
                        <CheckCircle className="w-5 h-5 text-green-500" />
                        <div>
                          <p className="font-medium text-gray-800">{videoFile.name}</p>
                          <p className="text-sm text-gray-600">
                            Boyut: {(videoFile.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                    </div>

                    {/* Video Önizleme */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-lg">Video Önizleme</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <video
                          ref={videoRef}
                          src={URL.createObjectURL(videoFile)}
                          controls
                          className="w-full rounded-lg"
                        />
                      </CardContent>
                    </Card>

                    {!isUploading && uploadProgress === 0 && (
                      <Button 
                        onClick={uploadVideo} 
                        className="w-full"
                        size="lg"
                      >
                        <ArrowRight className="w-4 h-4 mr-2" />
                        Videoyu Yükle ve Devam Et
                      </Button>
                    )}
                  </div>
                )}

                {isUploading && (
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Video Yükleniyor...</span>
                        <span>{Math.round(uploadProgress)}%</span>
                      </div>
                      <Progress value={uploadProgress} className="h-3" />
                    </div>
                    <div className="text-center text-sm text-gray-600">
                      <p>Lütfen bekleyin, video sunucuya yükleniyor...</p>
                    </div>
                  </div>
                )}

                {uploadProgress === 100 && !isUploading && (
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg text-center">
                    <CheckCircle className="w-8 h-8 mx-auto mb-2 text-green-500" />
                    <p className="text-green-800 font-medium">{analysisStatus}</p>
                    <p className="text-sm text-green-600 mt-1">
                      Chat ekranına yönlendiriliyorsunuz...
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    )
  }

  // Chat Screen
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-6xl mx-auto">
        <header className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            AI Video Cutter - Sohbet
          </h1>
          <div className="flex items-center justify-center gap-4">
            <Button 
              variant="outline" 
              onClick={goBackToUpload}
              size="sm"
            >
              ← Yeni Video Yükle
            </Button>
            {videoFile && (
              <p className="text-sm text-gray-600">
                Aktif Video: {videoFile.name}
              </p>
            )}
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Sol Panel - Video Önizleme ve Kesimler */}
          <div className="space-y-6">
            {/* Video Önizleme */}
            {videoFile && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Play className="w-5 h-5" />
                    Video Önizleme
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <video
                    ref={videoRef}
                    src={URL.createObjectURL(videoFile)}
                    controls
                    className="w-full rounded-lg"
                  />
                </CardContent>
              </Card>
            )}

            {/* Durum */}
            {analysisStatus && (
              <Card>
                <CardContent className="pt-6">
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-sm text-blue-800">{analysisStatus}</p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Önerilen Kesimler */}
            {suggestedCuts.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Scissors className="w-5 h-5" />
                    Önerilen Kesimler
                  </CardTitle>
                  <CardDescription>
                    AI tarafından önerilen video kesimleri
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {suggestedCuts.map((cut, index) => (
                    <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <Badge variant="outline">Kesim {index + 1}</Badge>
                        <p className="text-sm text-gray-600 mt-1">
                          {formatTime(cut.start)} - {formatTime(cut.end)}
                        </p>
                      </div>
                    </div>
                  ))}
                  <Button 
                    onClick={finalizeVideo} 
                    disabled={isLoading}
                    className="w-full mt-4"
                  >
                    {isLoading ? 'İşleniyor...' : 'Videoyu Oluştur'}
                  </Button>
                </CardContent>
              </Card>
            )}

            {/* Final Video İndirme */}
            {finalVideoUrl && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Download className="w-5 h-5" />
                    İşlenmiş Video
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                    <p className="text-green-800 mb-3">Video başarıyla oluşturuldu!</p>
                    <p className="text-sm text-gray-600 mb-3">
                      Dosya yolu: {finalVideoUrl}
                    </p>
                    <Button variant="outline" className="w-full">
                      Videoyu İndir
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sağ Panel - AI Sohbet */}
          <div className="space-y-6">
            <Card className="h-[700px] flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageCircle className="w-5 h-5" />
                  AI Asistan
                </CardTitle>
                <CardDescription>
                  Video kesimi için AI asistanıyla sohbet edin
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                {/* Chat Geçmişi */}
                <div className="flex-1 overflow-y-auto space-y-4 mb-4 p-4 bg-gray-50 rounded-lg">
                  {chatHistory.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                      <MessageCircle className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                      <p className="font-medium mb-2">AI asistanıyla sohbet etmeye başlayın!</p>
                      <p className="text-sm">
                        Örnek sorular:
                      </p>
                      <div className="text-sm mt-2 space-y-1">
                        <p>"Bu videodan önemli anları kesebilir misin?"</p>
                        <p>"İlk 30 saniyeyi kes"</p>
                        <p>"En hareketli bölümleri bul"</p>
                      </div>
                    </div>
                  ) : (
                    chatHistory.map((msg, index) => (
                      <div
                        key={index}
                        className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div
                          className={`max-w-[80%] p-3 rounded-lg ${
                            msg.role === 'user'
                              ? 'bg-blue-500 text-white'
                              : 'bg-white border border-gray-200'
                          }`}
                        >
                          <p className="text-sm">{msg.message}</p>
                        </div>
                      </div>
                    ))
                  )}
                  {isLoading && (
                    <div className="flex justify-start">
                      <div className="bg-white border border-gray-200 p-3 rounded-lg">
                        <p className="text-sm text-gray-500">AI düşünüyor...</p>
                      </div>
                    </div>
                  )}
                </div>

                {/* Mesaj Gönderme */}
                <div className="space-y-3">
                  <Textarea
                    placeholder="AI asistanına mesajınızı yazın..."
                    value={currentMessage}
                    onChange={(e) => setCurrentMessage(e.target.value)}
                    disabled={!videoId || isLoading}
                    rows={3}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        sendChatMessage()
                      }
                    }}
                  />
                  <Button
                    onClick={sendChatMessage}
                    disabled={!videoId || !currentMessage.trim() || isLoading}
                    className="w-full"
                  >
                    {isLoading ? 'Gönderiliyor...' : 'Mesaj Gönder'}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

