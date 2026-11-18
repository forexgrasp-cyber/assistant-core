import { useState, useRef, useEffect } from 'react'
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Mic,
  MessageSquare,
  Globe,
  Repeat,
  SkipBack,
  SkipForward,
  CheckCircle,
  Sparkles,
  Copy,
  Languages,
  Headphones,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn, generateId } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface DialoguePlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  playbackSpeed: number
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function DialoguePlayer({
  content,
  targetLanguage,
  nativeLanguage,
  playbackSpeed,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: DialoguePlayerProps) {
  const data = content.data as {
    dialogues: {
      id: string
      speaker: 'tutor' | 'native' | 'user'
      text: string
      translation?: string
      audioUrl?: string
      lipSyncData?: { time: number; viseme: string; intensity: number }[]
      order: number
    }[]
    settings?: {
      autoPlay?: boolean
      showTranslation?: boolean
      showTransliteration?: boolean
    }
  }

  const [currentDialogueIndex, setCurrentDialogueIndex] = useState(0)
  const [showTranslations, setShowTranslations] = useState(data.settings?.showTranslation ?? true)
  const [showTransliteration, setShowTransliteration] = useState(data.settings?.showTransliteration ?? false)
  const [isPlaying, setIsPlaying] = useState(false)
  const [completedDialogues, setCompletedDialogues] = useState<string[]>([])
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  const currentDialogue = data.dialogues[currentDialogueIndex]
  const isLastDialogue = currentDialogueIndex >= data.dialogues.length - 1
  const allCompleted = completedDialogues.length >= data.dialogues.length

  // Audio element setup
  useEffect(() => {
    if (currentDialogue?.audioUrl) {
      audioRef.current = new Audio(currentDialogue.audioUrl)
      audioRef.current.playbackRate = playbackSpeed

      audioRef.current.addEventListener('loadedmetadata', () => {
        setDuration(audioRef.current?.duration || 0)
      })

      audioRef.current.addEventListener('timeupdate', () => {
        setCurrentTime(audioRef.current?.currentTime || 0)
      })

      audioRef.current.addEventListener('ended', () => {
        setIsPlaying(false)
        if (!completedDialogues.includes(currentDialogue.id)) {
          setCompletedDialogues(prev => [...prev, currentDialogue.id])
        }
        if (data.settings?.autoPlay && !isLastDialogue) {
          handleNext()
        }
      })

      return () => {
        audioRef.current?.pause()
        audioRef.current = null
      }
    }
  }, [currentDialogue, playbackSpeed, data.settings?.autoPlay, isLastDialogue, completedDialogues])

  const handlePlayPause = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleNext = () => {
    if (!isLastDialogue) {
      setCurrentDialogueIndex(prev => prev + 1)
      setIsPlaying(false)
    }
  }

  const handlePrev = () => {
    if (currentDialogueIndex > 0) {
      setCurrentDialogueIndex(prev => prev - 1)
      setIsPlaying(false)
    }
  }

  const handleReplay = () => {
    if (audioRef.current) {
      audioRef.current.currentTime = 0
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Number(e.target.value)
      setCurrentTime(Number(e.target.value))
    }
  }

  const handleSpeakLine = (text: string) => {
    stopSpeaking()
    speak(text)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  // Check completion
  useEffect(() => {
    if (allCompleted && !isPlaying) {
      setTimeout(() => onComplete(95), 500)
    }
  }, [allCompleted, isPlaying, onComplete])

  const speakerConfig = {
    tutor: { color: 'primary', icon: Sparkles, label: 'AI Tutor' },
    native: { color: 'green', icon: Globe, label: 'Native Speaker' },
    user: { color: 'amber', icon: Mic, label: 'You' },
  }

  const speaker = speakerConfig[currentDialogue?.speaker || 'tutor']

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600">Dialogue {currentDialogueIndex + 1} of {data.dialogues.length}</span>
          <span className="font-medium text-gray-900">{completedDialogues.length}/{data.dialogues.length} completed</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
            style={{ width: `${(completedDialogues.length / data.dialogues.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Dialogue Card */}
      <div className="space-y-4">
        {data.dialogues.map((dialogue, index) => {
          const speakerCfg = speakerConfig[dialogue.speaker]
          const SpeakerIcon = speakerCfg.icon
          const isActive = index === currentDialogueIndex
          const isDone = completedDialogues.includes(dialogue.id)

          return (
            <div
              key={dialogue.id}
              className={cn(
                'rounded-2xl p-4 transition-all duration-300',
                isActive ? 'bg-gradient-to-r from-primary-50 to-accent-50 border border-primary-200' : 'bg-white border border-gray-100',
                isDone && !isActive ? 'bg-green-50 border-green-100' : ''
              )}
            >
              <div className="flex items-start gap-4">
                {/* Speaker Avatar */}
                <div className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                  `bg-${speakerCfg.color}-100 text-${speakerCfg.color}-600`
                )}>
                  <SpeakerIcon className="w-6 h-6" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={cn(
                      'text-sm font-medium',
                      isActive ? `text-${speakerCfg.color}-700` : 'text-gray-900'
                    )}>
                      {speakerCfg.label}
                    </span>
                    {isActive && (
                      <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-primary-100 text-primary-600 animate-pulse">
                        Playing
                      </span>
                    )}
                    {isDone && !isActive && (
                      <CheckCircle className="w-4 h-4 text-green-500 ml-auto" />
                    )}
                  </div>

                  {/* Target Language Text */}
                  <p className={cn(
                    'text-lg leading-relaxed',
                    isActive ? 'text-gray-900 font-medium' : 'text-gray-700'
                  )}>
                    {dialogue.text}
                  </p>

                  {/* Translation */}
                  {showTranslations && dialogue.translation && (
                    <p className="mt-2 text-base text-primary-700 italic leading-relaxed">
                      {dialogue.translation}
                    </p>
                  )}

                  {/* Audio Controls for active dialogue */}
                  {isActive && dialogue.audioUrl && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-3">
                        <Button
                          variant={isPlaying ? 'primary' : 'secondary'}
                          size="sm"
                          onClick={handlePlayPause}
                          leftIcon={isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleReplay}
                          leftIcon={<RotateCcw className="w-4 h-4" />}
                        >
                          Replay
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSpeakLine(dialogue.text)}
                          leftIcon={<Headphones className="w-4 h-4" />}
                        >
                          TTS
                        </Button>
                      </div>

                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500 w-10 text-right">{formatTime(currentTime)}</span>
                        <input
                          type="range"
                          min={0}
                          max={duration || 100}
                          value={currentTime}
                          onChange={handleSeek}
                          className="flex-1 h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                        />
                        <span className="text-xs text-gray-500 w-10">{formatTime(duration)}</span>
                      </div>

                      {/* Lip Sync Visualization */}
                      {dialogue.lipSyncData && dialogue.lipSyncData.length > 0 && (
                        <div className="mt-2 h-8 flex items-end gap-1">
                          {dialogue.lipSyncData.map((frame, i) => (
                            <div
                              key={i}
                              className="flex-1 bg-primary-500 rounded-t transition-all duration-50"
                              style={{
                                height: `${Math.max(4, frame.intensity * 32)}px`,
                                opacity: isPlaying ? 1 : 0.3,
                              }}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Copy Button for inactive/completed */}
                  {(isDone || !isActive) && (
                    <div className="mt-2 flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => copyToClipboard(dialogue.text)}
                        leftIcon={<Copy className="w-4 h-4" />}
                      >
                        Copy
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleSpeakLine(dialogue.text)}
                        leftIcon={<Headphones className="w-4 h-4" />}
                      >
                        Listen
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <Button
          variant="secondary"
          leftIcon={<SkipBack className="w-4 h-4" />}
          onClick={handlePrev}
          disabled={currentDialogueIndex === 0}
        >
          Previous
        </Button>

        <div className="text-sm text-gray-500">
          {currentDialogueIndex + 1} / {data.dialogues.length}
        </div>

        <Button
          variant={isLastDialogue && allCompleted ? 'primary' : 'secondary'}
          rightIcon={<SkipForward className="w-4 h-4" />}
          onClick={handleNext}
          disabled={isLastDialogue}
        >
          {isLastDialogue && allCompleted ? 'Finish' : 'Next'}
        </Button>
      </div>

      {/* Completion Message */}
      {allCompleted && (
        <div className="p-6 bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl border border-green-100 text-center animate-in">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-3" />
          <h3 className="text-lg font-bold text-green-800 mb-1">Dialogue Complete!</h3>
          <p className="text-green-600">You've practiced all {data.dialogues.length} dialogue lines.</p>
        </div>
      )}

      {/* Settings */}
      <div className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showTranslations}
            onChange={(e) => setShowTranslations(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-gray-700">Show translations</span>
        </label>
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={showTransliteration}
            onChange={(e) => setShowTransliteration(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
          />
          <span className="text-sm text-gray-700">Show transliteration</span>
        </label>
      </div>
    </div>
  )
}

// Helper function
function formatTime(seconds: number): string {
  if (isNaN(seconds)) return '0:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}