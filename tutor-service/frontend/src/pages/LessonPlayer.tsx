import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Mic,
  MicOff,
  MessageSquare,
  BookOpen,
  Flag,
  CheckCircle,
  XCircle,
  RotateCcw,
  SkipBack,
  SkipForward,
  Settings,
  X,
  Maximize2,
  Copy,
  Download,
  Share2,
  Heart,
  Bookmark,
  Layers,
  Target,
  Sparkles,
  Volume1,
  Headphones,
  PenTool,
  Image,
  Film,
  FileText,
  Mic2,
  Keyboard,
  Languages,
  Zap,
  Trophy,
  ArrowLeft,
  Home,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Textarea } from '@/components/ui/Input'
import { useTutorStore } from '@/stores/tutorStore'
import { useTutor } from '@/contexts/TutorContext'
import { useSpeechRecognition, useSpeechSynthesis } from '@/hooks/useSpeechRecognition'
import { cn, formatTime, generateId, getCEFRColor } from '@/lib/utils'
import { ChatInterface } from '@/components/chat/ChatInterface'
import type { ChatInterfaceHandle } from '@/components/chat/ChatInterface'
import { PronunciationEvaluator } from '@/components/pronunciation/PronunciationEvaluator'
import { WritingEvaluator } from '@/components/writing/WritingEvaluator'
import { ExercisePlayer } from '@/components/lesson/ExercisePlayer'
import { DialoguePlayer } from '@/components/lesson/DialoguePlayer'
import { VideoPlayer } from '@/components/lesson/VideoPlayer'
import { AudioPlayer } from '@/components/lesson/AudioPlayer'
import { FlashcardPlayer } from '@/components/lesson/FlashcardPlayer'
import { QuizPlayer } from '@/components/lesson/QuizPlayer'
import { ReadingPlayer } from '@/components/lesson/ReadingPlayer'
import { useAuth } from '@/contexts/AuthContext'
import toast from 'react-hot-toast'
import confetti from 'canvas-confetti'
import type { Lesson, LessonContent, ChatMessage } from '@/types'

export function LessonPlayer() {
  const { lessonId } = useParams<{ lessonId: string }>()
  const navigate = useNavigate()
  const { user, lessons, lessonProgress, currentLesson, currentContentIndex, setCurrentLesson, setCurrentContentIndex, completeLesson, updateLessonProgress, targetLanguage, nativeLanguage, autoPlayAudio, updateProgress, dailyGoalMinutes, addToPracticeHistory } = useTutorStore()
  const { sendMessage, sendVoiceMessage, evaluatePronunciation, evaluateWriting, tutorState, isConnected } = useTutor()
  const { user: authUser } = useAuth()

  // Speech recognition & synthesis
  const {
    isListening,
    transcript,
    interimTranscript,
    confidence,
    startListening,
    stopListening,
    resetTranscript,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition({
    language: targetLanguage === 'es' ? 'es-ES' : targetLanguage === 'fr' ? 'fr-FR' : targetLanguage === 'de' ? 'de-DE' : targetLanguage === 'ja' ? 'ja-JP' : targetLanguage === 'ko' ? 'ko-KR' : targetLanguage === 'zh' ? 'zh-CN' : targetLanguage === 'pt' ? 'pt-BR' : targetLanguage === 'it' ? 'it-IT' : targetLanguage === 'ru' ? 'ru-RU' : targetLanguage === 'ar' ? 'ar-SA' : targetLanguage === 'hi' ? 'hi-IN' : targetLanguage === 'nl' ? 'nl-NL' : targetLanguage === 'pl' ? 'pl-PL' : targetLanguage === 'tr' ? 'tr-TR' : targetLanguage === 'sv' ? 'sv-SE' : targetLanguage === 'da' ? 'da-DK' : targetLanguage === 'no' ? 'nb-NO' : targetLanguage === 'fi' ? 'fi-FI' : targetLanguage === 'cs' ? 'cs-CZ' : targetLanguage === 'hu' ? 'hu-HU' : targetLanguage === 'ro' ? 'ro-RO' : targetLanguage === 'uk' ? 'uk-UA' : targetLanguage === 'el' ? 'el-GR' : targetLanguage === 'he' ? 'he-IL' : targetLanguage === 'th' ? 'th-TH' : targetLanguage === 'vi' ? 'vi-VN' : targetLanguage === 'id' ? 'id-ID' : targetLanguage === 'ms' ? 'ms-MY' : targetLanguage === 'tl' ? 'tl-PH' : targetLanguage === 'sw' ? 'sw-KE' : targetLanguage === 'fa' ? 'fa-IR' : 'en-US',
    continuous: false,
    interimResults: true,
  })

  const {
    speak,
    stop: stopSpeaking,
    isSpeaking,
    isPaused,
    voices,
    selectedVoice,
  } = useSpeechSynthesis({
    language: targetLanguage,
  })

  // State
  const [lesson, setLesson] = useState<Lesson | null>(null)
  const [currentContent, setCurrentContent] = useState<LessonContent | null>(null)
  const [showChat, setShowChat] = useState(false)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
  const [isContentComplete, setIsContentComplete] = useState(false)
  const [contentScore, setContentScore] = useState<number | null>(null)
  const [showTranscript, setShowTranscript] = useState(false)
  const [playbackSpeed, setPlaybackSpeed] = useState(1)
  const [showSettings, setShowSettings] = useState(false)
  const [showExitConfirm, setShowExitConfirm] = useState(false)
  const [confettiTrigger, setConfettiTrigger] = useState(0)

  // Refs
  const contentContainerRef = useRef<HTMLDivElement>(null)
  const chatContainerRef = useRef<ChatInterfaceHandle>(null)

  // Load lesson on mount
  useEffect(() => {
    if (lessonId) {
      const foundLesson = lessons.find(l => l.id === lessonId)
      if (foundLesson) {
        setLesson(foundLesson)
        setCurrentLesson(foundLesson)

        // Restore progress
        const progress = lessonProgress[lessonId]
        const startIndex = progress?.currentContentIndex || 0
        setCurrentContentIndex(startIndex)
        setCurrentContent(foundLesson.content[startIndex])
        setIsContentComplete(progress?.status === 'completed' || progress?.status === 'mastered')

        // Load chat history
        // In real app, fetch from backend
        setChatMessages([])
      } else {
        toast.error('Lesson not found')
        navigate('/curriculum')
      }
    }
  }, [lessonId, lessons, lessonProgress, setCurrentLesson, setCurrentContentIndex, navigate])

  // Update current content when index changes
  useEffect(() => {
    if (lesson && currentContentIndex < lesson.content.length) {
      const content = lesson.content[currentContentIndex]
      setCurrentContent(content)
      setIsContentComplete(false)
      setContentScore(null)

      // Auto-play audio if enabled
      if (autoPlayAudio && content.type === 'audio') {
        // Handled by AudioPlayer component
      }
    }
  }, [currentContentIndex, lesson, autoPlayAudio])

  // Handle content completion
  const handleContentComplete = useCallback(async (score?: number) => {
    if (!lesson || !currentContent) return

    setIsContentComplete(true)
    if (score !== undefined) setContentScore(score)

    // Update lesson progress
    updateLessonProgress(lesson.id, {
      currentContentIndex: currentContentIndex + 1,
      completedContent: [
        ...(lessonProgress[lesson.id]?.completedContent || []),
        currentContent.id,
      ],
      lastAccessed: new Date().toISOString(),
      masteryLevel: score || 100,
    })

    // Check if lesson is complete
    if (currentContentIndex + 1 >= lesson.content.length) {
      const avgScore = contentScore ?? 85
      await completeLesson(lesson.id, avgScore)

      // Show confetti for completion
      setConfettiTrigger(prev => prev + 1)
      toast.success('🎉 Lesson completed! Great job!')

      // Add to practice history
      addToPracticeHistory({
        id: generateId(),
        role: 'system',
        content: `Completed lesson: ${lesson.title}`,
        type: 'text',
        timestamp: new Date().toISOString(),
      })
    } else {
      toast.success('Content completed! Continue to next section.')
    }
  }, [lesson, currentContent, currentContentIndex, lessonProgress, updateLessonProgress, completeLesson, contentScore, addToPracticeHistory])

  // Navigation
  const goToNextContent = useCallback(() => {
    if (lesson && currentContentIndex < lesson.content.length - 1) {
      setCurrentContentIndex(currentContentIndex + 1)
    }
  }, [lesson, currentContentIndex, setCurrentContentIndex])

  const goToPrevContent = useCallback(() => {
    if (currentContentIndex > 0) {
      setCurrentContentIndex(currentContentIndex - 1)
    }
  }, [currentContentIndex, setCurrentContentIndex])

  const exitLesson = useCallback(() => {
    if (!isContentComplete && currentContentIndex > 0) {
      setShowExitConfirm(true)
    } else {
      navigate('/curriculum')
    }
  }, [isContentComplete, currentContentIndex, navigate])

  // Confetti effect
  useEffect(() => {
    if (confettiTrigger > 0) {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#0ea5e9', '#d946ef', '#10b981', '#f59e0b'],
      })
    }
  }, [confettiTrigger])

  if (!lesson) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary-500 border-t-transparent mx-auto mb-4" />
          <p className="text-gray-600">Loading lesson...</p>
        </div>
      </div>
    )
  }

  const totalDuration = lesson.content.reduce((sum, c) => sum + c.estimatedTime, 0)
  const completedCount = lessonProgress[lesson.id]?.completedContent.length || 0
  const overallProgress = lesson.content.length > 0 ? (completedCount / lesson.content.length) * 100 : 0

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Bar */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-xl border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Left: Exit + Progress */}
            <div className="flex items-center gap-4 flex-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={exitLesson}
                className="lg:hidden"
              >
                <ArrowLeft className="w-5 h-5" />
              </Button>

              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/curriculum')}
                className="hidden lg:flex items-center gap-2"
              >
                <Home className="w-4 h-4" />
                <span className="font-medium text-gray-700">Curriculum</span>
              </Button>

              {/* Progress Ring */}
              <div className="relative w-14 h-14 flex-shrink-0">
                <svg className="lesson-progress-ring w-full h-full">
                  <circle
                    cx="28"
                    cy="28"
                    r="24"
                    fill="none"
                    stroke="#e5e7eb"
                    strokeWidth="4"
                  />
                  <circle
                    cx="28"
                    cy="28"
                    r="24"
                    fill="none"
                    stroke="url(#progress-gradient)"
                    strokeWidth="4"
                    strokeLinecap="round"
                    strokeDasharray={150.8}
                    strokeDashoffset={150.8 * (1 - overallProgress / 100)}
                    className="lesson-progress-ring circle"
                  />
                  <defs>
                    <linearGradient id="progress-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#0ea5e9" />
                      <stop offset="100%" stopColor="#d946ef" />
                    </linearGradient>
                  </defs>
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-sm font-bold text-gray-900">{Math.round(overallProgress)}%</span>
                </div>
              </div>

              <div className="hidden sm:block">
                <p className="font-medium text-gray-900 text-sm">{lesson.title}</p>
                <p className="text-xs text-gray-500">
                  {currentContentIndex + 1} of {lesson.content.length} • {totalDuration} min total
                </p>
              </div>
            </div>

            {/* Right: Controls */}
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSettings(!showSettings)}
              >
                <Settings className="w-5 h-5" />
              </Button>

              <Button
                variant="primary"
                size="icon"
                onClick={() => setShowChat(!showChat)}
                className={showChat ? 'bg-primary-100 text-primary-600' : ''}
              >
                <MessageSquare className="w-5 h-5" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={exitLesson}
                className="hidden sm:flex"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </div>

          {/* Content Navigation Tabs */}
          <div className="mt-3 overflow-x-auto pb-2">
            <div className="flex gap-1 min-w-max px-2">
              {lesson.content.map((content, index) => {
                const contentProgress = lessonProgress[lesson.id]?.completedContent.includes(content.id)
                const isCurrent = index === currentContentIndex
                const isCompleted = contentProgress

                return (
                  <button
                    key={content.id}
                    onClick={() => setCurrentContentIndex(index)}
                    className={cn(
                      'px-3 py-1.5 rounded-xl text-xs font-medium whitespace-nowrap transition-all duration-200 flex items-center gap-1.5',
                      isCurrent
                        ? 'bg-primary-100 text-primary-700'
                        : isCompleted
                        ? 'bg-green-100 text-green-700'
                        : index < currentContentIndex
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-gray-50 text-gray-400 hover:bg-gray-100'
                    )}
                    disabled={index > currentContentIndex && !isCompleted}
                  >
                    {isCompleted && <CheckCircle className="w-3 h-3" />}
                    {content.type === 'dialogue' && <MessageSquare className="w-3 h-3" />}
                    {content.type === 'exercise' && <PenTool className="w-3 h-3" />}
                    {content.type === 'video' && <Film className="w-3 h-3" />}
                    {content.type === 'audio' && <Headphones className="w-3 h-3" />}
                    {content.type === 'text' && <FileText className="w-3 h-3" />}
                    {content.type === 'pronunciation' && <Mic2 className="w-3 h-3" />}
                    {content.type === 'writing' && <PenTool className="w-3 h-3" />}
                    {content.type === 'quiz' && <Target className="w-3 h-3" />}
                    {content.type === 'flashcard' && <Layers className="w-3 h-3" />}
                    {content.type === 'reading' && <BookOpen className="w-3 h-3" />}
                    <span className="hidden xs:block">{content.title}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid lg:grid-cols-[1fr_380px] gap-6">
          {/* Lesson Content */}
          <div className="space-y-6">
            {/* Content Header */}
            <Card variant="glass">
              <CardContent className="p-4 sm:p-6">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`badge text-sm ${getCEFRColor(lesson.level).replace('bg-', 'bg-').replace('500', '100')} text-gray-700`}>
                        {lesson.level}
                      </span>
                      <span className="badge text-sm bg-gray-100 text-gray-600">
                        {currentContent?.focusArea || lesson.focusArea}
                      </span>
                      {currentContent?.required && (
                        <span className="badge text-sm bg-red-100 text-red-700">Required</span>
                      )}
                    </div>
                    <h1 className="text-2xl lg:text-3xl font-bold text-gray-900 mb-2">
                      {currentContent?.title || lesson.title}
                    </h1>
                    <p className="text-gray-600 text-lg max-w-2xl">
                      {currentContent ? '' : lesson.description}
                    </p>
                  </div>

                  {/* XP Reward */}
                  <div className="flex items-center gap-2 text-right">
                    <div className="p-3 bg-gradient-to-br from-amber-500 to-yellow-500 rounded-xl text-white">
                      <Zap className="w-6 h-6" />
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold text-gray-900">+{currentContent?.xpReward || lesson.xpReward} XP</p>
                      <p className="text-xs text-gray-500">completion bonus</p>
                    </div>
                  </div>
                </div>

                {/* Estimated Time */}
                <div className="mt-4 flex items-center gap-4 text-sm text-gray-600">
                  <span className="flex items-center gap-1">
                    <Clock className="w-4 h-4" />
                    {currentContent?.estimatedTime || lesson.duration} min estimated
                  </span>
                  <span className="flex items-center gap-1">
                    <Target className="w-4 h-4" />
                    Focus: {currentContent?.focusArea || lesson.focusArea}
                  </span>
                </div>
              </CardContent>
            </Card>

            {/* Content Player */}
            <Card>
              <CardContent className="p-0">
                <div className="p-6">
                  {currentContent && (
                    <ContentRenderer
                      content={currentContent}
                      lesson={lesson}
                      targetLanguage={targetLanguage}
                      nativeLanguage={nativeLanguage}
                      playbackSpeed={playbackSpeed}
                      onComplete={handleContentComplete}
                      onNavigate={goToNextContent}
                      speak={speak}
                      stopSpeaking={stopSpeaking}
                      isSpeaking={isSpeaking}
                      evaluatePronunciation={evaluatePronunciation}
                      evaluateWriting={evaluateWriting}
                    />
                  )}

                  {/* Navigation Buttons */}
                  <div className="mt-8 flex items-center justify-between pt-6 border-t border-gray-100">
                    <Button
                      variant="secondary"
                      leftIcon={<ChevronLeft className="w-4 h-4" />}
                      onClick={goToPrevContent}
                      disabled={currentContentIndex === 0}
                    >
                      Previous
                    </Button>

                    <div className="text-sm text-gray-500">
                      Section {currentContentIndex + 1} of {lesson.content.length}
                    </div>

                    <Button
                      variant={isContentComplete ? 'secondary' : 'primary'}
                      rightIcon={<ChevronRight className="w-4 h-4" />}
                      onClick={goToNextContent}
                      disabled={currentContentIndex >= lesson.content.length - 1 || (!isContentComplete && currentContent?.required)}
                    >
                      {isContentComplete ? 'Next Section' : 'Complete & Continue'}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Transcript Section */}
            {showTranscript && currentContent && (
              <Card variant="glass">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-gray-900">Transcript & Translation</h3>
                    <Button variant="ghost" size="sm" onClick={() => setShowTranscript(false)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                  <TranscriptViewer content={currentContent} targetLanguage={targetLanguage} nativeLanguage={nativeLanguage} />
                </CardContent>
              </Card>
            )}

            {/* Notes Section */}
            <Card variant="glass">
              <CardContent className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Your Notes</h3>
                <Textarea
                  placeholder="Take notes while learning..."
                  className="min-h-[120px]"
                  rows={4}
                />
              </CardContent>
            </Card>
          </div>

          {/* Sidebar: Chat & Tools */}
          <div className="space-y-4">
            {/* Tutor Chat */}
            <Card className="h-full flex flex-col" variant={showChat ? 'hover' : 'default'}>
              <CardContent className="p-0 flex-1 flex flex-col">
                <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-gray-900">AI Tutor</p>
                      <p className="text-xs text-gray-500">{isConnected ? 'Online' : 'Connecting...'}</p>
                    </div>
                  </div>
                  <Button variant="ghost" size="icon" onClick={() => setShowChat(false)}>
                    <X className="w-4 h-4" />
                  </Button>
                </div>

                <ChatInterface
                  messages={chatMessages}
                  onSendMessage={(content, type) => sendMessage(content, type)}
                  onSendVoice={sendVoiceMessage}
                  targetLanguage={targetLanguage}
                  nativeLanguage={nativeLanguage}
                  tutorState={tutorState}
                  isRecording={isListening}
                  onStartRecording={startListening}
                  onStopRecording={stopListening}
                  transcript={transcript}
                  interimTranscript={interimTranscript}
                  confidence={confidence}
                  browserSupportsSpeechRecognition={browserSupportsSpeechRecognition}
                  ref={chatContainerRef}
                />
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card variant="glass">
              <CardContent className="p-4">
                <h4 className="font-semibold text-gray-900 mb-3">Learning Tools</h4>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Languages className="w-4 h-4" />}
                    onClick={() => setShowTranscript(true)}
                  >
                    Transcript
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Flag className="w-4 h-4" />}
                  >
                    Report Issue
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Bookmark className="w-4 h-4" />}
                  >
                    Bookmark
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    leftIcon={<Share2 className="w-4 h-4" />}
                  >
                    Share
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Lesson Progress */}
            <Card variant="glass">
              <CardContent className="p-4">
                <h4 className="font-semibold text-gray-900 mb-3">Section Progress</h4>
                <div className="space-y-3">
                  {lesson.content.map((content, index) => {
                    const isDone = lessonProgress[lesson.id]?.completedContent.includes(content.id)
                    const isCurrent = index === currentContentIndex

                    return (
                      <div
                        key={content.id}
                        className={cn(
                          'flex items-center gap-3 p-2 rounded-xl transition-colors',
                          isCurrent ? 'bg-primary-50' : '',
                          isDone ? '' : index > currentContentIndex ? 'opacity-50' : ''
                        )}
                      >
                        <div className={cn(
                          'w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0',
                          isDone ? 'bg-green-500 text-white' : isCurrent ? 'bg-primary-500 text-white' : index < currentContentIndex ? 'bg-gray-300 text-gray-600' : 'bg-gray-100 text-gray-400'
                        )}>
                          {isDone ? <CheckCircle className="w-4 h-4" /> : index + 1}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 truncate">{content.title}</p>
                          <p className="text-xs text-gray-500">{content.estimatedTime} min • {content.type}</p>
                        </div>
                        {isDone && <CheckCircle className="w-4 h-4 text-green-500" />}
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Lesson Settings</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowSettings(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Playback Speed</label>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.25"
                    value={playbackSpeed}
                    onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                    className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                  <span className="text-lg font-bold text-gray-900 w-16 text-right">{playbackSpeed}x</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Tutor Voice</label>
                <select
                  value={selectedVoice?.name || ''}
                  onChange={(e) => {
                    const voice = voices.find(v => v.name === e.target.value)
                    if (voice) {
                      // setSelectedVoice(voice) - need to add to hook
                    }
                  }}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="">Default</option>
                  {voices.filter(v => v.lang.startsWith(targetLanguage.split('-')[0])).map(v => (
                    <option key={v.name} value={v.name}>{v.name} ({v.lang})</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="autoPlay"
                  checked={autoPlayAudio}
                  onChange={(e) => { /* update setting */ }}
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="autoPlay" className="text-sm text-gray-700">Auto-play audio content</label>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="showTranslations"
                  defaultChecked
                  className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <label htmlFor="showTranslations" className="text-sm text-gray-700">Show translations by default</label>
              </div>
            </div>
          </Card>
        </div>
      )}

      {/* Exit Confirmation Modal */}
      {showExitConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-md p-6">
            <div className="text-center mb-6">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-100 flex items-center justify-center">
                <AlertTriangle className="w-8 h-8 text-amber-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900">Leave Lesson?</h2>
              <p className="text-gray-600 mt-2">Your progress will be saved, but you'll need to resume from where you left off.</p>
            </div>
            <div className="flex gap-3">
              <Button variant="secondary" className="flex-1" onClick={() => setShowExitConfirm(false)}>
                Stay
              </Button>
              <Button variant="primary" className="flex-1" onClick={() => { setShowExitConfirm(false); navigate('/curriculum'); }}>
                Leave Lesson
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* Import missing icons */}
      <script
        dangerouslySetInnerHTML={{
          __html: `
            // Icons imported at top
          `,
        }}
      />
    </div>
  )
}

// Content Renderer - routes to appropriate player component
function ContentRenderer(props: {
  content: LessonContent
  lesson: Lesson
  targetLanguage: string
  nativeLanguage: string
  playbackSpeed: number
  onComplete: (score?: number) => void
  onNavigate: () => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
  evaluatePronunciation: (audioBlob: Blob, targetText: string) => Promise<any>
  evaluateWriting: (text: string, criteria: string[]) => Promise<any>
}) {
  const { content, ...rest } = props

  switch (content.type) {
    case 'dialogue':
      return <DialoguePlayer {...props} />
    case 'exercise':
      return <ExercisePlayer {...props} />
    case 'video':
      return <VideoPlayer {...props} />
    case 'audio':
      return <AudioPlayer {...props} />
    case 'pronunciation':
      return <PronunciationEvaluator {...props} />
    case 'writing':
      return <WritingEvaluator {...props} />
    case 'quiz':
      return <QuizPlayer {...props} />
    case 'flashcard':
      return <FlashcardPlayer {...props} />
    case 'reading':
      return <ReadingPlayer {...props} />
    case 'text':
      return <TextContent {...props} />
    default:
      return <div className="p-8 text-center text-gray-500">Content type not supported: {content.type}</div>
  }
}

// Simple text content component
function TextContent({ content, targetLanguage, nativeLanguage }: { content: LessonContent; targetLanguage: string; nativeLanguage: string }) {
  const data = content.data as { text: string; translation?: string; keyPoints?: string[] }

  return (
    <div className="prose prose-primary max-w-none">
      <div className="space-y-6">
        <div className="bg-gray-50 rounded-xl p-6">
          <h4 className="font-semibold text-gray-900 mb-3">Target Language ({targetLanguage})</h4>
          <p className="text-lg text-gray-900 leading-relaxed">{data.text}</p>
        </div>

        {data.translation && (
          <div className="bg-primary-50 rounded-xl p-6 border border-primary-100">
            <h4 className="font-semibold text-primary-900 mb-3">Translation ({nativeLanguage})</h4>
            <p className="text-lg text-primary-800 leading-relaxed">{data.translation}</p>
          </div>
        )}

        {data.keyPoints && data.keyPoints.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Key Points</h4>
            <ul className="space-y-2">
              {data.keyPoints.map((point, i) => (
                <li key={i} className="flex items-start gap-2 p-3 bg-gray-50 rounded-xl">
                  <span className="w-5 h-5 rounded-full bg-primary-100 text-primary-600 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                  <span className="text-gray-700">{point}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

// Transcript Viewer
function TranscriptViewer({ content, targetLanguage, nativeLanguage }: { content: LessonContent; targetLanguage: string; nativeLanguage: string }) {
  // In real app, this would fetch actual transcript data
  return (
    <div className="space-y-4 max-h-96 overflow-y-auto">
      <p className="text-gray-500 text-sm italic">Transcript will appear here as you progress through the content.</p>
    </div>
  )
}

// Import missing icons
import { Clock, AlertTriangle } from 'lucide-react'