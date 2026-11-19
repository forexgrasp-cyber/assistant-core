import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  SkipBack,
  SkipForward,
  RotateCcw,
  Globe,
  Sparkles,
  CheckCircle,
  Timer,
  FastForward,
  Volume1,
  Mic2,
  Repeat,
  ArrowUpRight,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface AudioPlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  playbackSpeed: number
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function AudioPlayer({
  content,
  targetLanguage,
  nativeLanguage,
  playbackSpeed,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: AudioPlayerProps) {
  const data = content.data as {
    url: string
    title: string
    duration: number
    transcript?: string
    translation?: string
    segments?: { start: number; end: number; text: string; translation?: string }[]
    poster?: string
  }

  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(data.duration)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [showTranscript, setShowTranscript] = useState(false)
  const [currentSegment, setCurrentSegment] = useState<string>('')
  const [completed, setCompleted] = useState(false)
  const [listenCount, setListenCount] = useState(0)
  const [waveData] = useState<number[]>(Array(64).fill(0))

  const audioRef = useRef<HTMLAudioElement>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const animationRef = useRef<number | null>(null)
  const dataArrayRef = useRef<Uint8Array<ArrayBuffer> | null>(null)

  // Audio visualization setup
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const setupVisualization = async () => {
      try {
        audioContextRef.current = new AudioContext()
        const source = audioContextRef.current.createMediaElementSource(audio)
        const analyser = audioContextRef.current.createAnalyser()
        analyser.fftSize = 128

        analyserRef.current = analyser
        const bufferLength = analyser.frequencyBinCount
        dataArrayRef.current = new Uint8Array(bufferLength)

        source.connect(analyser)
        analyser.connect(audioContextRef.current.destination)

        const animate = () => {
          if (!analyserRef.current || !dataArrayRef.current) return

          analyserRef.current.getByteFrequencyData(dataArrayRef.current)
          const dataArray = Array.from(dataArrayRef.current)
          // Normalize and scale
          const normalized = dataArray.map(v => Math.min(1, v / 255))
          // Only update if playing
          if (isPlaying) {
            // This would update a wave visualization state
            // For now we'll just use the static waveData
          }

          animationRef.current = requestAnimationFrame(animate)
        }

        animate()
      } catch (error) {
        console.warn('Audio visualization not available:', error)
      }
    }

    setupVisualization()

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
      if (audioContextRef.current) audioContextRef.current.close()
    }
  }, [isPlaying])

  // Audio events
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    audio.playbackRate = playbackSpeed
    audio.volume = volume

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)

      // Update current segment
      if (data.segments) {
        const segment = data.segments.find(s => audio.currentTime >= s.start && audio.currentTime <= s.end)
        setCurrentSegment(segment?.text || '')
      }

      // Auto-complete at 95%
      if (audio.currentTime / audio.duration >= 0.95 && !completed) {
        setCompleted(true)
        onComplete(90)
      }
    }

    const handleEnded = () => {
      setIsPlaying(false)
      setListenCount(prev => prev + 1)
      if (!completed) {
        setCompleted(true)
        onComplete(90)
      }
    }

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
    }

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
    }
  }, [playbackSpeed, volume, data.segments, completed, onComplete])

  const togglePlayPause = useCallback(() => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      // Resume audio context if suspended
      if (audioContextRef.current?.state === 'suspended') {
        audioContextRef.current.resume()
      }
      audio.play()
      setIsPlaying(true)
    }
  }, [isPlaying])

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = Number(e.target.value)
      setCurrentTime(Number(e.target.value))
    }
  }, [])

  const skipTime = useCallback((seconds: number) => {
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = Math.max(0, Math.min(audio.duration, audio.currentTime + seconds))
    }
  }, [])

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current
    const newVolume = Number(e.target.value)
    setVolume(newVolume)
    setIsMuted(newVolume === 0)
    if (audio) audio.volume = newVolume
  }, [])

  const toggleMute = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.muted = !isMuted
      setIsMuted(!isMuted)
      setVolume(isMuted ? volume : 0)
    }
  }, [isMuted, volume])

  const handleSpeedChange = useCallback((speed: number) => {
    const audio = audioRef.current
    if (audio) {
      audio.playbackRate = speed
    }
  }, [])

  const handleReplay = useCallback(() => {
    const audio = audioRef.current
    if (audio) {
      audio.currentTime = 0
      audio.play()
      setIsPlaying(true)
    }
  }, [])

  const formatTime = (seconds: number): string => {
    if (isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Generate visual wave bars based on audio data
  const waveBars = Array.from({ length: 32 }, (_, i) => {
    const baseHeight = Math.random() * 0.3 + 0.1
    const playingMultiplier = isPlaying ? 1 : 0.3
    const height = Math.max(4, (waveData[i] || baseHeight) * 80 * playingMultiplier)
    return (
      <div
        key={i}
        className="w-1.5 bg-primary-500 rounded-full transition-all duration-75"
        style={{ height: `${height}px` }}
      />
    )
  })

  return (
    <div className="space-y-6">
      {/* Audio Player Card */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {/* Header */}
          <div className="p-6 bg-gradient-to-r from-primary-50 to-accent-50 border-b border-primary-100">
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-xl bg-primary-500 flex items-center justify-center">
                <Volume1 className="w-7 h-7 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm text-primary-700 font-medium">Listening Practice</p>
                <h3 className="text-xl font-bold text-gray-900">{data.title}</h3>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-primary-600">{listenCount + (completed ? 1 : 0)}</p>
                <p className="text-xs text-primary-500">times played</p>
              </div>
            </div>
          </div>

          {/* Main Player */}
          <div className="p-6">
            {/* Waveform Visualization */}
            <div className="mb-6">
              <div className="audio-wave justify-center items-end gap-0.5 h-32">
                {waveBars}
              </div>
            </div>

            {/* Current Segment Display */}
            {currentSegment && (
              <div className="mb-6 p-4 bg-gray-50 rounded-xl border border-gray-100 animate-in">
                <p className="text-lg text-gray-900 font-medium text-center leading-relaxed">
                  {currentSegment}
                </p>
              </div>
            )}

            {/* Progress Bar */}
            <div className="mb-4">
              <input
                type="range"
                min={0}
                max={duration || 100}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-primary-500"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-between">
              {/* Transport Controls */}
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => skipTime(-15)}
                  leftIcon={<SkipBack className="w-5 h-5" />}
                  aria-label="Skip back 15 seconds"
                />
                <Button
                  variant="primary"
                  size="lg"
                  onClick={togglePlayPause}
                  leftIcon={isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-1" />}
                  className="shadow-lg shadow-primary-500/30"
                />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => skipTime(15)}
                  rightIcon={<SkipForward className="w-5 h-5" />}
                  aria-label="Skip forward 15 seconds"
                />
              </div>

              {/* Volume & Speed */}
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="icon" onClick={toggleMute} leftIcon={isMuted || volume === 0 ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />} />
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.1}
                    value={volume}
                    onChange={handleVolumeChange}
                    className="w-20 h-1 bg-gray-200 rounded-full appearance-none cursor-pointer accent-primary-500"
                  />
                </div>

                <div className="relative">
                  <Button variant="ghost" size="sm" onClick={() => {}} className="flex items-center gap-1">
                    <Timer className="w-4 h-4" />
                <span className="font-medium text-gray-700">{playbackSpeed}x</span>
                  </Button>
                  <div className="absolute bottom-full left-0 mb-2 p-2 bg-white rounded-xl border border-gray-200 shadow-lg animate-in">
                    <div className="flex gap-1">
                      {[0.5, 0.75, 1, 1.25, 1.5, 2].map(speed => (
                        <button
                          key={speed}
                          onClick={() => handleSpeedChange(speed)}
                          className={cn(
                            'px-3 py-1.5 text-sm rounded-lg text-gray-700 transition-colors',
                            playbackSpeed === speed ? 'bg-primary-100 text-primary-700 font-medium' : 'hover:bg-gray-100'
                          )}
                        >
                          {speed}x
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Transcript Section */}
      {(data.transcript || data.translation) && (
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Transcript & Translation</h3>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={() => setShowTranscript(!showTranscript)}>
                  {showTranscript ? <ArrowUpRight className="w-4 h-4" /> : <FileText className="w-4 h-4" />}
                  <span className="hidden sm:block">{showTranscript ? 'Hide' : 'Show'}</span>
                </Button>
                <Button variant="ghost" size="icon" onClick={() => speak(data.transcript || '')} leftIcon={<Volume2 className="w-4 h-4" />} />
              </div>
            </div>

            {showTranscript && (
              <div className="space-y-4 animate-in">
                {data.transcript && (
                  <div>
                    <p className="text-sm font-medium text-gray-500 mb-1">{targetLanguage}</p>
                <p className="text-gray-900 leading-relaxed">{data.transcript}</p>
                  </div>
                )}
                {data.translation && (
                  <div className="border-t border-gray-200 pt-4">
                    <p className="text-sm font-medium text-primary-600 mb-1">{nativeLanguage}</p>
                    <p className="text-primary-800 leading-relaxed">{data.translation}</p>
                  </div>
                )}

                {data.segments && data.segments.length > 0 && (
                  <div className="border-t border-gray-200 pt-4">
                    <p className="text-sm font-medium text-gray-500 mb-2">Segments</p>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {data.segments.map((segment, index) => (
                        <div
                          key={index}
                          className={cn(
                            'p-3 rounded-xl text-sm cursor-pointer transition-colors',
                            currentSegment === segment.text
                              ? 'bg-primary-50 border border-primary-200'
                              : 'bg-gray-50 hover:bg-gray-100'
                          )}
                          onClick={() => {
                            if (audioRef.current) {
                              audioRef.current.currentTime = segment.start
                            }
                          }}
                        >
                          <p className="text-gray-900 font-medium mb-1">{segment.text}</p>
                          {segment.translation && (
                            <p className="text-primary-700 text-sm">{segment.translation}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Completion */}
      {completed && (
        <div className="p-6 bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl border border-green-100 text-center animate-in">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-3" />
          <h3 className="text-lg font-bold text-green-800 mb-1">Audio Complete!</h3>
          <p className="text-green-600">You've listened to the full audio. Great job!</p>
        </div>
      )}

      {/* Listen Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Listen Progress</span>
          <span className="font-medium text-gray-900">{completed ? 100 : Math.round((currentTime / (duration || 1)) * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
            style={{ width: `${completed ? 100 : (currentTime / (duration || 1)) * 100}%` }}
          />
        </div>
      </div>
    </div>
  )
}

// Import missing icons
import { FileText } from 'lucide-react'