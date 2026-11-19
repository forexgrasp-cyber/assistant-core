import { useState, useRef, useCallback, useEffect } from 'react'
import type { SpeechRecognitionResult } from '@/types'

interface UseSpeechRecognitionOptions {
  language?: string
  continuous?: boolean
  interimResults?: boolean
  onResult?: (result: SpeechRecognitionResult) => void
  onError?: (error: string) => void
  onEnd?: () => void
}

interface UseSpeechRecognitionReturn {
  isListening: boolean
  transcript: string
  interimTranscript: string
  confidence: number
  error: string | null
  startListening: () => void
  stopListening: () => void
  resetTranscript: () => void
  browserSupportsSpeechRecognition: boolean
}

export function useSpeechRecognition({
  language = 'en-US',
  continuous = true,
  interimResults = true,
  onResult,
  onError,
  onEnd,
}: UseSpeechRecognitionOptions = {}): UseSpeechRecognitionReturn {
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [interimTranscript, setInterimTranscript] = useState('')
  const [confidence, setConfidence] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const recognitionRef = useRef<SpeechRecognition | null>(null)
  const isInitialized = useRef(false)

  // Initialize speech recognition
  useEffect(() => {
    if (typeof window === 'undefined') return

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognition) {
      setError('Speech recognition not supported in this browser')
      return
    }

    recognitionRef.current = new SpeechRecognition()
    const recognition = recognitionRef.current

    recognition.lang = language
    recognition.continuous = continuous
    recognition.interimResults = interimResults
    recognition.maxAlternatives = 1

    recognition.onresult = (event) => {
      let finalTranscript = ''
      let interimTranscript = ''
      let maxConfidence = 0

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const alt = result[0]
        if (result.isFinal) {
          finalTranscript += alt.transcript
          maxConfidence = Math.max(maxConfidence, alt.confidence)
        } else {
          interimTranscript += alt.transcript
        }
      }

      if (finalTranscript) {
        setTranscript((prev) => prev + finalTranscript)
        setConfidence(maxConfidence)
        onResult?.({
          transcript: finalTranscript,
          confidence: maxConfidence,
          isFinal: true,
          language,
        })
      }

      setInterimTranscript(interimTranscript)
      if (interimTranscript) {
        onResult?.({
          transcript: interimTranscript,
          confidence: 0,
          isFinal: false,
          language,
        })
      }
    }

    recognition.onerror = (event) => {
      const errorMsg = event.error
      setError(errorMsg)
      onError?.(errorMsg)

      // Auto-restart on certain errors
      if (errorMsg === 'no-speech' && continuous) {
        // No speech detected, continue listening
        return
      }
      if (errorMsg === 'audio-capture') {
        setIsListening(false)
      }
    }

    recognition.onend = () => {
      setIsListening(false)
      onEnd?.()

      // Auto-restart if continuous mode
      if (continuous && isListening) {
        try {
          recognition.start()
          setIsListening(true)
        } catch {
          // Ignore restart errors
        }
      }
    }

    isInitialized.current = true

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
        recognitionRef.current = null
      }
      isInitialized.current = false
    }
  }, [language, continuous, interimResults, onResult, onError, onEnd])

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return

    if (isListening) return

    setError(null)
    try {
      recognitionRef.current.start()
      setIsListening(true)
    } catch (err) {
      setError('Failed to start speech recognition')
      console.error('Speech recognition start error:', err)
    }
  }, [isListening])

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return

    try {
      recognitionRef.current.stop()
      setIsListening(false)
    } catch (err) {
      console.error('Speech recognition stop error:', err)
    }
  }, [])

  const resetTranscript = useCallback(() => {
    setTranscript('')
    setInterimTranscript('')
    setConfidence(0)
    setError(null)
  }, [])

  return {
    isListening,
    transcript,
    interimTranscript,
    confidence,
    error,
    startListening,
    stopListening,
    resetTranscript,
    browserSupportsSpeechRecognition: !!(
      typeof window !== 'undefined' &&
      (window.SpeechRecognition || window.webkitSpeechRecognition)
    ),
  }
}

// Text-to-Speech hook
interface UseSpeechSynthesisOptions {
  language?: string
  voice?: SpeechSynthesisVoice | null
  rate?: number
  pitch?: number
  volume?: number
  onStart?: () => void
  onEnd?: () => void
  onError?: (error: string) => void
}

interface UseSpeechSynthesisReturn {
  speak: (text: string) => void
  stop: () => void
  pause: () => void
  resume: () => void
  isSpeaking: boolean
  isPaused: boolean
  voices: SpeechSynthesisVoice[]
  selectedVoice: SpeechSynthesisVoice | null
  setVoice: (voice: SpeechSynthesisVoice) => void
}

export function useSpeechSynthesis({
  language = 'en-US',
  voice: initialVoice,
  rate = 1,
  pitch = 1,
  volume = 1,
  onStart,
  onEnd,
  onError,
}: UseSpeechSynthesisOptions = {}): UseSpeechSynthesisReturn {
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([])
  const [selectedVoice, setSelectedVoice] = useState<SpeechSynthesisVoice | null>(
    initialVoice || null
  )
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Load voices
  useEffect(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return

    const loadVoices = () => {
      const availableVoices = window.speechSynthesis.getVoices()
      setVoices(availableVoices)

      // Auto-select voice for language if not set
      if (!selectedVoice && availableVoices.length > 0) {
        const voice = availableVoices.find((v) => v.lang.startsWith(language.split('-')[0]))
        if (voice) {
          setSelectedVoice(voice)
        }
      }
    }

    loadVoices()

    // Voices might load asynchronously
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = loadVoices
    }

    return () => {
      if (window.speechSynthesis.onvoiceschanged === loadVoices) {
        window.speechSynthesis.onvoiceschanged = null
      }
    }
  }, [language, selectedVoice])

  const speak = useCallback(
    (text: string) => {
      if (typeof window === 'undefined' || !window.speechSynthesis) {
        onError?.('Speech synthesis not supported')
        return
      }

      // Cancel any ongoing speech
      window.speechSynthesis.cancel()

      const utterance = new SpeechSynthesisUtterance(text)
      utterance.lang = language
      utterance.rate = rate
      utterance.pitch = pitch
      utterance.volume = volume

      if (selectedVoice) {
        utterance.voice = selectedVoice
      }

      utterance.onstart = () => {
        setIsSpeaking(true)
        setIsPaused(false)
        onStart?.()
      }

      utterance.onend = () => {
        setIsSpeaking(false)
        setIsPaused(false)
        onEnd?.()
      }

      utterance.onerror = (event) => {
        setIsSpeaking(false)
        setIsPaused(false)
        onError?.(event.error)
      }

      utteranceRef.current = utterance
      window.speechSynthesis.speak(utterance)
    },
    [language, rate, pitch, volume, selectedVoice, onStart, onEnd, onError]
  )

  const stop = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel()
      setIsSpeaking(false)
      setIsPaused(false)
    }
  }, [])

  const pause = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.pause()
      setIsPaused(true)
    }
  }, [])

  const resume = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.resume()
      setIsPaused(false)
    }
  }, [])

  const setVoice = useCallback((voice: SpeechSynthesisVoice) => {
    setSelectedVoice(voice)
  }, [])

  return {
    speak,
    stop,
    pause,
    resume,
    isSpeaking,
    isPaused,
    voices,
    selectedVoice,
    setVoice,
  }
}

// Audio visualization hook
export function useAudioVisualizer(audioElement: HTMLAudioElement | null) {
  const [waveData, setWaveData] = useState<number[]>(Array(32).fill(0))
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationRef = useRef<number | null>(null)
  const dataArrayRef = useRef<Uint8Array<ArrayBuffer> | null>(null)

  const startVisualization = useCallback(() => {
    if (!audioElement || audioContextRef.current) return

    const audioContext = new AudioContext()
    audioContextRef.current = audioContext

    const source = audioContext.createMediaElementSource(audioElement)
    const analyser = audioContext.createAnalyser()
    analyser.fftSize = 64
    analyserRef.current = analyser

    const bufferLength = analyser.frequencyBinCount
    dataArrayRef.current = new Uint8Array(bufferLength)

    source.connect(analyser)
    analyser.connect(audioContext.destination)

    const animate = () => {
      if (!analyserRef.current || !dataArrayRef.current) return

      analyserRef.current.getByteFrequencyData(dataArrayRef.current)
      const data = Array.from(dataArrayRef.current)
      const normalized = data.map((value) => value / 255)
      setWaveData(normalized)

      animationRef.current = requestAnimationFrame(animate)
    }

    animate()
  }, [audioElement])

  const stopVisualization = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current)
      animationRef.current = null
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    setWaveData(Array(32).fill(0))
  }, [])

  useEffect(() => {
    if (audioElement?.src) {
      startVisualization()
    }
    return stopVisualization
  }, [audioElement?.src, startVisualization, stopVisualization])

  return { waveData, startVisualization, stopVisualization }
}