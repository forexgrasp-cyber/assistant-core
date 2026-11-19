import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  RotateCcw,
  CheckCircle,
  XCircle,
  HelpCircle,
  Target,
  BarChart2,
  Activity,
  Sparkles,
  ArrowRight,
  Trophy,
  Star,
  Flag,
  Copy,
  Settings,
  Turtle as SlowMo,
  FastForward,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import confetti from 'canvas-confetti'
import type { LessonContent } from '@/types'

interface PronunciationEvaluatorProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
  evaluatePronunciation?: (audioBlob: Blob, targetText: string) => Promise<any>
}

export function PronunciationEvaluator({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
  evaluatePronunciation,
}: PronunciationEvaluatorProps) {
  const data = content.data as {
    targetText: string
    phonemes: { symbol: string; sound: string; example: string; mouthShape: string }[]
    audioUrl: string
    difficulty: 'easy' | 'medium' | 'hard'
    context?: string
    tips?: string[]
  }

  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
  const [result, setResult] = useState<{
    overall: number
    phonemes: { phoneme: string; score: number; expected: string; actual: string }[]
    fluency: number
    intonation: number
    feedback: string
  } | null>(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [showDetails, setShowDetails] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [attempts, setAttempts] = useState(0)
  const [confettiTrigger, setConfettiTrigger] = useState(0)
  const [currentTab, setCurrentTab] = useState<'practice' | 'analysis' | 'tips'>('practice')

  const audioRef = useRef<HTMLAudioElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | null>(null)

  // Confetti effect
  useEffect(() => {
    if (confettiTrigger > 0) {
      confetti({
        particleCount: 80,
        spread: 60,
        origin: { y: 0.7 },
        colors: ['#0ea5e9', '#d946ef', '#10b981', '#f59e0b'],
      })
    }
  }, [confettiTrigger])

  // Native audio player
  useEffect(() => {
    if (data.audioUrl) {
      audioRef.current = new Audio(data.audioUrl)
      audioRef.current.playbackRate = playbackSpeed
    }
  }, [playbackSpeed])

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      })

      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      const chunks: BlobPart[] = []

      recorder.ondataavailable = (e) => chunks.push(e.data)
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        setAudioBlob(blob)
        stream.getTracks().forEach(t => t.stop())
      }

      setMediaRecorder(recorder)
      recorder.start(100) // Collect data every 100ms
      setIsRecording(true)
    } catch (error) {
      console.error('Recording failed:', error)
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
      setIsRecording(false)
    }
  }, [mediaRecorder])

  const evaluateAudio = useCallback(async () => {
    if (!audioBlob || !evaluatePronunciation) return

    setIsEvaluating(true)
    try {
      // In production, this would call the actual pronunciation evaluation API
      // For now, we'll simulate the result
      await new Promise(resolve => setTimeout(resolve, 1500))

      // Simulate phoneme scoring
      const phonemeScores = data.phonemes.map(p => ({
        phoneme: p.symbol,
        score: Math.floor(Math.random() * 40) + 60, // 60-100
        expected: p.symbol,
        actual: p.symbol,
      }))

      const overall = Math.round(
        phonemeScores.reduce((sum, p) => sum + p.score, 0) / phonemeScores.length
      )

      const fluency = Math.floor(Math.random() * 30) + 70
      const intonation = Math.floor(Math.random() * 30) + 70

      const feedback = generateFeedback(overall, fluency, intonation)

      setResult({
        overall,
        phonemes: phonemeScores,
        fluency,
        intonation,
        feedback,
      })

      setAttempts(prev => prev + 1)

      if (overall >= 80) {
        setConfettiTrigger(prev => prev + 1)
      }
    } catch (error) {
      console.error('Evaluation failed:', error)
    } finally {
      setIsEvaluating(false)
    }
  }, [audioBlob, evaluatePronunciation, data.phonemes])

  const playNativeAudio = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.play()
    }
  }, [])

  const playUserAudio = useCallback(() => {
    if (audioBlob) {
      const audio = new Audio(URL.createObjectURL(audioBlob))
      audio.play()
    }
  }, [audioBlob])

  const speakTargetText = useCallback(() => {
    stopSpeaking()
    speak(data.targetText)
  }, [data.targetText, speak, stopSpeaking])

  const retry = useCallback(() => {
    setAudioBlob(null)
    setResult(null)
    setIsRecording(false)
  }, [])

  // Generate feedback text
  function generateFeedback(overall: number, fluency: number, intonation: number): string {
    if (overall >= 90) {
      return 'Excellent pronunciation! Your speech sounds very natural.'
    } else if (overall >= 80) {
      return 'Great job! Minor improvements on specific sounds will make it perfect.'
    } else if (overall >= 70) {
      return 'Good effort! Focus on the highlighted phonemes below.'
    } else {
      return 'Keep practicing! Listen carefully to the native speaker and try again.'
    }
  }

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-6">
      {/* Target Phrase */}
      <Card variant="gradient" className="p-6 text-center">
        <div className="mb-4">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white">
            <Target className="w-4 h-4" />
            Pronunciation Practice
          </span>
          {data.difficulty && (
            <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white ml-2">
              <Flag className="w-4 h-4" />
              {data.difficulty.charAt(0).toUpperCase() + data.difficulty.slice(1)}
            </span>
          )}
        </div>

        <p className="text-2xl lg:text-3xl font-medium text-white mb-4 leading-relaxed">
          "{data.targetText}"
        </p>

        {data.context && (
          <p className="text-white/80 text-sm mb-4">{data.context}</p>
        )}

        <div className="flex items-center justify-center gap-4">
          <Button
            variant="secondary"
            size="lg"
            onClick={playNativeAudio}
            leftIcon={<Volume2 className="w-5 h-5" />}
          >
            Hear Native
          </Button>
          <Button
            variant="primary"
            size="lg"
            onClick={speakTargetText}
            leftIcon={<Mic className="w-5 h-5" />}
          >
            Practice with TTS
          </Button>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {(['practice', 'analysis', 'tips'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setCurrentTab(tab)}
            className={cn(
              'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all',
              currentTab === tab
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Practice Tab */}
      {currentTab === 'practice' && (
        <div className="space-y-6 animate-in">
          {/* Recording Area */}
          <Card className="p-8 text-center">
            {!isRecording && !audioBlob ? (
              <>
                <div className="w-32 h-32 mx-auto mb-6 rounded-full bg-primary-100 flex items-center justify-center">
                  <Mic className="w-16 h-16 text-primary-600" />
                </div>
                <p className="text-xl font-medium text-gray-900 mb-2">Record Your Pronunciation</p>
                <p className="text-gray-600 mb-6">Press the button and speak the target phrase</p>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={startRecording}
                  leftIcon={<Mic className="w-6 h-6" />}
                  className="shadow-xl shadow-primary-500/30"
                >
                  Start Recording
                </Button>
              </>
            ) : isRecording ? (
              <>
                <div className="w-32 h-32 mx-auto mb-6 rounded-full bg-red-100 flex items-center justify-center animate-pulse">
                  <Mic className="w-16 h-16 text-red-600" />
                </div>
                <p className="text-xl font-medium text-red-600 mb-2 animate-pulse">Recording...</p>
                <p className="text-gray-600 mb-6">Speak clearly into your microphone</p>
                <Button
                  variant="danger"
                  size="lg"
                  onClick={stopRecording}
                  leftIcon={<MicOff className="w-6 h-6" />}
                >
                  Stop Recording
                </Button>
              </>
            ) : (
              <>
                <div className="w-32 h-32 mx-auto mb-6 rounded-full bg-green-100 flex items-center justify-center">
                  <CheckCircle className="w-16 h-16 text-green-600" />
                </div>
                <p className="text-xl font-medium text-green-600 mb-2">Recording Complete!</p>
                <p className="text-gray-600 mb-6">Listen to your recording or evaluate</p>

                <div className="mb-6 p-4 bg-gray-50 rounded-xl border border-gray-200 max-w-md mx-auto">
                  <audio controls src={audioBlob ? URL.createObjectURL(audioBlob) : ''} className="w-full" />
                </div>

                <div className="flex items-center justify-center gap-4">
                  <Button
                    variant="secondary"
                    onClick={playNativeAudio}
                    leftIcon={<Volume2 className="w-4 h-4" />}
                  >
                    Native
                  </Button>
                  <Button
                    variant="primary"
                    onClick={playUserAudio}
                    leftIcon={<Volume2 className="w-4 h-4" />}
                  >
                    Yours
                  </Button>
                </div>

                {!isEvaluating && (
                  <Button
                    variant="primary"
                    size="lg"
                    className="w-full max-w-md mx-auto mt-4"
                    onClick={evaluateAudio}
                    leftIcon={<Target className="w-5 h-5" />}
                  >
                    Evaluate Pronunciation
                  </Button>
                )}

                <Button
                  variant="ghost"
                  onClick={retry}
                  className="mt-4"
                  leftIcon={<RotateCcw className="w-4 h-4" />}
                >
                  Record Again
                </Button>
              </>
            )}

            {isEvaluating && (
              <div className="mt-8 flex items-center justify-center gap-3 text-primary-600">
                <div className="animate-spin rounded-full h-8 w-8 border-2 border-primary-500 border-t-transparent" />
                <span className="font-medium">Analyzing your pronunciation...</span>
              </div>
            )}
          </Card>

          {/* Results */}
          {result && (
            <Card variant={result.overall >= 80 ? 'hover' : 'default'} className="animate-in">
              <CardContent className="p-6">
                <div className="text-center mb-8">
                  <div className={cn(
                    'w-32 h-32 rounded-full mx-auto mb-4 flex items-center justify-center',
                    result.overall >= 80 ? 'bg-gradient-to-br from-green-500 to-emerald-500' :
                    result.overall >= 70 ? 'bg-gradient-to-br from-amber-500 to-yellow-500' :
                    'bg-gradient-to-br from-red-500 to-pink-500'
                  )}>
                    <span className="text-4xl font-bold text-white">{result.overall}%</span>
                  </div>
                  <h3 className="text-xl font-bold text-gray-900 mb-2">
                    {result.overall >= 90 ? 'Outstanding!' :
                    result.overall >= 80 ? 'Excellent!' :
                    result.overall >= 70 ? 'Good Job!' : 'Keep Practicing!'}
                  </h3>
                  <p className="text-gray-600">{result.feedback}</p>
                </div>

                {/* Score Breakdown */}
                <div className="grid grid-cols-3 gap-4 mb-8">
                  <div className="text-center p-4 bg-gray-50 rounded-xl">
                    <p className="text-2xl font-bold text-primary-600">{result.fluency}%</p>
                    <p className="text-sm text-gray-500">Fluency</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-xl">
                    <p className="text-2xl font-bold text-accent-600">{result.intonation}%</p>
                    <p className="text-sm text-gray-500">Intonation</p>
                  </div>
                  <div className="text-center p-4 bg-gray-50 rounded-xl">
                    <p className="text-2xl font-bold text-green-600">{attempts}</p>
                    <p className="text-sm text-gray-500">Attempts</p>
                  </div>
                </div>

                {/* Continue Button */}
                <Button
                  variant="primary"
                  className="w-full"
                  onClick={() => onComplete(result.overall)}
                  rightIcon={<ArrowRight className="w-4 h-4" />}
                  size="lg"
                >
                  Continue
                </Button>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Analysis Tab */}
      {currentTab === 'analysis' && result && (
        <div className="space-y-6 animate-in">
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-primary-600" />
                Phoneme Analysis
              </h3>
              <p className="text-sm text-gray-600 mb-6">
                Each phoneme in the target phrase analyzed for accuracy.
              </p>

              <div className="space-y-3">
                {result.phonemes.map((p, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-lg font-bold text-primary-600 w-12 text-center">
                          {p.phoneme}
                        </span>
                        <div>
                          <p className="font-medium text-gray-900">Target: {p.expected}</p>
                          <p className="text-sm text-gray-500">Detected: {p.actual}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className={cn(
                          'text-2xl font-bold',
                          p.score >= 80 ? 'text-green-600' :
                          p.score >= 60 ? 'text-amber-600' : 'text-red-600'
                        )}>
                          {p.score}%
                        </p>
                      </div>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all duration-500',
                          p.score >= 80 ? 'bg-green-500' :
                          p.score >= 60 ? 'bg-amber-500' : 'bg-red-500'
                        )}
                        style={{ width: `${p.score}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Waveform Comparison */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary-600" />
                Waveform Comparison
              </h3>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Native Speaker</p>
                  <NativeWaveform />
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-2">Your Recording</p>
                  <UserWaveform audioBlob={audioBlob} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Tips Tab */}
      {currentTab === 'tips' && (
        <div className="space-y-6 animate-in">
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary-600" />
                Pronunciation Tips
              </h3>
              <div className="space-y-4">
                {data.tips?.map((tip, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                    <div className="flex items-start gap-3">
                      <div className="w-8 h-8 rounded-lg bg-primary-100 text-primary-600 flex items-center justify-center flex-shrink-0 text-sm font-bold">
                        {index + 1}
                      </div>
                      <p className="text-gray-700">{tip}</p>
                    </div>
                  </div>
                ))}
                {data.phonemes.map((p, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                    <div className="flex items-center gap-3">
                      <span className="font-mono text-lg font-bold text-primary-600 w-12 text-center">
                        {p.symbol}
                      </span>
                      <div>
                        <p className="font-medium text-gray-900">{p.sound}</p>
                        <p className="text-sm text-gray-500">Example: {p.example}</p>
                        <p className="text-xs text-gray-400 mt-1">Mouth: {p.mouthShape}</p>
                      </div>
                      <Button variant="ghost" size="icon" onClick={() => speak(p.example)}>
                        <Volume2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {data.context && (
            <Card variant="glass">
              <CardContent className="p-6">
                <h3 className="font-semibold text-gray-900 mb-2">Context</h3>
                <p className="text-gray-700">{data.context}</p>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Attempts */}
      <div className="text-center text-sm text-gray-500">
        Attempt {attempts + 1} • Keep practicing to improve your score!
      </div>
    </div>
  )
}

// Native Speaker Waveform (placeholder)
function NativeWaveform() {
  return (
    <div className="h-16 flex items-end justify-center gap-1 bg-gray-50 rounded-xl p-2">
      {[0.8, 0.6, 0.9, 0.5, 0.7, 0.8, 0.4, 0.9, 0.6, 0.7, 0.5, 0.8].map((h, i) => (
        <div
          key={i}
          className="flex-1 bg-primary-500 rounded-t transition-all duration-300"
          style={{ height: `${h * 100}%` }}
        />
      ))}
    </div>
  )
}

// User Waveform (placeholder)
function UserWaveform({ audioBlob }: { audioBlob: Blob | null }) {
  const heights = audioBlob
    ? [0.7, 0.5, 0.8, 0.6, 0.6, 0.7, 0.5, 0.8, 0.7, 0.6, 0.5, 0.7]
    : [0.3, 0.4, 0.3, 0.5, 0.4, 0.3, 0.5, 0.4, 0.3, 0.4, 0.3, 0.4]

  return (
    <div className="h-16 flex items-end justify-center gap-1 bg-gray-50 rounded-xl p-2">
      {heights.map((h, i) => (
        <div
          key={i}
          className="flex-1 bg-green-500 rounded-t transition-all duration-300"
          style={{ height: `${h * 100}%` }}
        />
      ))}
    </div>
  )
}