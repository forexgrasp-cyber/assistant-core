import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Mic,
  MessageSquare,
  Headphones,
  PenTool,
  BookOpen,
  Target,
  Zap,
  Trophy,
  Flame,
  ArrowRight,
  RotateCcw,
  Play,
  Pause,
  Volume2,
  Settings,
  Shuffle,
  Timer,
  Crown,
  Sparkles,
  Bookmark,
  Share2,
  Download,
  Copy,
  CheckCircle,
  XCircle,
  HelpCircle,
  Layers,
  Globe,
  Image,
  Film,
  FileText,
  Mic2,
  Keyboard,
  Languages,
  Heart,
  Star,
  TrendingUp,
  Calendar,
  Clock,
  AlertTriangle,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useTutorStore } from '@/stores/tutorStore'
import { useSpeechRecognition, useSpeechSynthesis } from '@/hooks/useSpeechRecognition'
import { cn, generateId } from '@/lib/utils'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { PronunciationEvaluator } from '@/components/pronunciation/PronunciationEvaluator'
import { WritingEvaluator } from '@/components/writing/WritingEvaluator'
import { ExercisePlayer } from '@/components/lesson/ExercisePlayer'
import { DialoguePlayer } from '@/components/lesson/DialoguePlayer'
import { FlashcardPlayer } from '@/components/lesson/FlashcardPlayer'
import { useAuth } from '@/contexts/AuthContext'
import confetti from 'canvas-confetti'
import type { LessonContent, FocusArea } from '@/types'

// Practice modes
const practiceModes = [
  {
    id: 'conversation',
    label: 'Free Conversation',
    description: 'Chat naturally with the AI tutor about any topic',
    icon: MessageSquare,
    color: 'bg-blue-500',
    estimatedTime: '∞',
  },
  {
    id: 'pronunciation',
    label: 'Pronunciation Drills',
    description: 'Practice specific sounds with real-time feedback',
    icon: Mic,
    color: 'bg-green-500',
    estimatedTime: '10 min',
  },
  {
    id: 'vocabulary',
    label: 'Vocabulary Builder',
    description: 'Flashcards, matching, and recall exercises',
    icon: Layers,
    color: 'bg-purple-500',
    estimatedTime: '15 min',
  },
  {
    id: 'grammar',
    label: 'Grammar Practice',
    description: 'Targeted exercises for grammar patterns',
    icon: BookOpen,
    color: 'bg-amber-500',
    estimatedTime: '12 min',
  },
  {
    id: 'listening',
    label: 'Listening Comprehension',
    description: 'Audio exercises with transcripts and questions',
    icon: Headphones,
    color: 'bg-teal-500',
    estimatedTime: '10 min',
  },
  {
    id: 'writing',
    label: 'Writing Workshop',
    description: 'Guided writing with AI evaluation',
    icon: PenTool,
    color: 'bg-pink-500',
    estimatedTime: '20 min',
  },
  {
    id: 'roleplay',
    label: 'Roleplay Scenarios',
    description: 'Real-life situations: restaurant, travel, business',
    icon: Globe,
    color: 'bg-indigo-500',
    estimatedTime: '15 min',
  },
  {
    id: 'shadowing',
    label: 'Shadowing Practice',
    description: 'Repeat after native speakers for fluency',
    icon: Volume2,
    color: 'bg-rose-500',
    estimatedTime: '10 min',
  },
]

// Mock practice content
const practiceContent: Record<string, LessonContent[]> = {
  pronunciation: [
    {
      id: 'pron-1',
      type: 'pronunciation',
      title: 'Spanish Vowels: a, e, i, o, u',
      data: {
        targetText: 'El niño come manzanas en la escuela',
        phonemes: [
          { symbol: 'a', sound: 'ah', example: 'casa', mouthShape: 'Open wide' },
          { symbol: 'e', sound: 'eh', example: 'mesa', mouthShape: 'Slightly open' },
          { symbol: 'i', sound: 'ee', example: 'sí', mouthShape: 'Spread lips' },
          { symbol: 'o', sound: 'oh', example: 'todo', mouthShape: 'Rounded lips' },
          { symbol: 'u', sound: 'oo', example: 'tú', mouthShape: 'Tight circle' },
        ],
        audioUrl: '',
        difficulty: 'easy',
      },
      order: 1,
      estimatedTime: 5,
      xpReward: 25,
      required: true,
    },
  ],
  vocabulary: [
    {
      id: 'vocab-1',
      type: 'flashcard',
      title: 'Daily Routine Verbs',
      data: {
        cards: [
          { id: '1', front: 'to wake up', back: 'despertarse', frontAudio: '', backAudio: '' },
          { id: '2', front: 'to get up', back: 'levantarse', frontAudio: '', backAudio: '' },
          { id: '3', front: 'to brush teeth', back: 'cepillarse los dientes', frontAudio: '', backAudio: '' },
          { id: '4', front: 'to eat breakfast', back: 'desayunar', frontAudio: '', backAudio: '' },
          { id: '5', front: 'to go to work', back: 'ir al trabajo', frontAudio: '', backAudio: '' },
        ],
        settings: { shuffle: true, showImages: false, autoPlayAudio: false },
      },
      order: 1,
      estimatedTime: 10,
      xpReward: 50,
      required: true,
    },
  ],
  grammar: [
    {
      id: 'grammar-1',
      type: 'exercise',
      title: 'Present Tense -AR Verbs',
      data: {
        question: 'Complete the conjugation for "hablar" (to speak)',
        type: 'multiple_choice',
        options: ['hablo', 'hablas', 'habla', 'hablamos', 'habláis', 'hablan'],
        correctAnswer: ['hablo', 'hablas', 'habla', 'hablamos', 'habláis', 'hablan'],
        explanation: 'Regular -AR verbs follow this pattern in present tense.',
      },
      order: 1,
      estimatedTime: 8,
      xpReward: 40,
      required: true,
    },
  ],
  listening: [
    {
      id: 'listen-1',
      type: 'audio',
      title: 'At the Café',
      data: {
        url: '',
        title: 'Ordering Coffee',
        duration: 2,
        transcript: 'Buenos días. Quisiera un café con leche, por favor. ¿Cuánto cuesta?',
        translation: 'Good morning. I would like a coffee with milk, please. How much does it cost?',
      },
      order: 1,
      estimatedTime: 5,
      xpReward: 30,
      required: true,
    },
  ],
  writing: [
    {
      id: 'write-1',
      type: 'writing',
      title: 'Introduce Yourself',
      data: {
        prompt: 'Write a short paragraph introducing yourself in Spanish. Include your name, where you\'re from, what you do, and your hobbies.',
        minWords: 50,
        maxWords: 150,
        criteria: [
          { name: 'Grammar', description: 'Correct verb conjugations and sentence structure', weight: 0.3 },
          { name: 'Vocabulary', description: 'Appropriate and varied word choice', weight: 0.25 },
          { name: 'Coherence', description: 'Logical flow and organization', weight: 0.25 },
          { name: 'Task Completion', description: 'Addresses all required elements', weight: 0.2 },
        ],
        examples: [
          'Hola, me llamo María. Soy de México y vivo en Madrid. Trabajo como profesora y me gusta leer y cocinar.',
        ],
      },
      order: 1,
      estimatedTime: 15,
      xpReward: 75,
      required: true,
    },
  ],
  roleplay: [
    {
      id: 'roleplay-1',
      type: 'dialogue',
      title: 'Restaurant Roleplay',
      data: {
        dialogues: [
          { id: '1', speaker: 'native', text: 'Buenas tardes. Mesa para dos, por favor.', translation: 'Good evening. Table for two, please.', audioUrl: '', order: 1 },
          { id: '2', speaker: 'tutor', text: '¡Claro! Aquí tienen el menú. ¿Les gustaría algo de beber?', translation: 'Of course! Here is the menu. Would you like something to drink?', audioUrl: '', order: 2 },
          { id: '3', speaker: 'user', text: 'Sí, agua con gas para mí.', translation: 'Yes, sparkling water for me.', audioUrl: '', order: 3 },
        ],
        settings: { autoPlay: false, showTranslation: true },
      },
      order: 1,
      estimatedTime: 10,
      xpReward: 50,
      required: true,
    },
  ],
  shadowing: [
    {
      id: 'shadow-1',
      type: 'audio',
      title: 'News Segment - Technology',
      data: {
        url: '',
        title: 'AI Advances',
        duration: 3,
        transcript: 'La inteligencia artificial está transformando la forma en que trabajamos y vivimos en el siglo veintiuno.',
        translation: 'Artificial intelligence is transforming how we work and live in the twenty-first century.',
        segments: [
          { start: 0, end: 5, text: 'La inteligencia artificial está transformando', translation: 'Artificial intelligence is transforming' },
          { start: 5, end: 9, text: 'la forma en que trabajamos', translation: 'how we work' },
          { start: 9, end: 13, text: 'y vivimos en el siglo veintiuno', translation: 'and live in the twenty-first century' },
        ],
      },
      order: 1,
      estimatedTime: 8,
      xpReward: 40,
      required: true,
    },
  ],
  conversation: [
    {
      id: 'conv-1',
      type: 'exercise',
      title: 'Open Conversation',
      data: {
        question: 'Start a conversation with your AI tutor about any topic!',
        type: 'input',
        correctAnswer: '',
        explanation: 'There are no wrong answers in free conversation.',
      },
      order: 1,
      estimatedTime: 0,
      xpReward: 10,
      required: true,
    },
  ],
}

export function Practice() {
  const { targetLanguage, nativeLanguage, userProgress, user, addToPracticeHistory } = useTutorStore()
  const { user: authUser } = useAuth()
  const [selectedMode, setSelectedMode] = useState<string>('conversation')
  const [activeContentIndex, setActiveContentIndex] = useState(0)
  const [showContent, setShowContent] = useState(false)
  const [practiceStats, setPracticeStats] = useState({
    sessionsToday: 3,
    minutesToday: 45,
    streakDays: 7,
    totalXPEarned: 2450,
  })

  // Speech hooks
  const {
    isListening,
    transcript,
    interimTranscript,
    confidence,
    startListening,
    stopListening,
    browserSupportsSpeechRecognition,
  } = useSpeechRecognition({
    language: targetLanguage === 'es' ? 'es-ES' : targetLanguage === 'fr' ? 'fr-FR' : targetLanguage === 'de' ? 'de-DE' : targetLanguage === 'ja' ? 'ja-JP' : targetLanguage === 'ko' ? 'ko-KR' : targetLanguage === 'zh' ? 'zh-CN' : targetLanguage === 'pt' ? 'pt-BR' : targetLanguage === 'it' ? 'it-IT' : targetLanguage === 'ru' ? 'ru-RU' : targetLanguage === 'ar' ? 'ar-SA' : targetLanguage === 'hi' ? 'hi-IN' : targetLanguage === 'nl' ? 'nl-NL' : targetLanguage === 'pl' ? 'pl-PL' : targetLanguage === 'tr' ? 'tr-TR' : targetLanguage === 'sv' ? 'sv-SE' : targetLanguage === 'da' ? 'da-DK' : targetLanguage === 'no' ? 'nb-NO' : targetLanguage === 'fi' ? 'fi-FI' : targetLanguage === 'cs' ? 'cs-CZ' : targetLanguage === 'hu' ? 'hu-HU' : targetLanguage === 'ro' ? 'ro-RO' : targetLanguage === 'uk' ? 'uk-UA' : targetLanguage === 'el' ? 'el-GR' : targetLanguage === 'he' ? 'he-IL' : targetLanguage === 'th' ? 'th-TH' : targetLanguage === 'vi' ? 'vi-VN' : targetLanguage === 'id' ? 'id-ID' : targetLanguage === 'ms' ? 'ms-MY' : targetLanguage === 'tl' ? 'tl-PH' : targetLanguage === 'sw' ? 'sw-KE' : targetLanguage === 'fa' ? 'fa-IR' : 'en-US',
  })

  const {
    speak,
    stop: stopSpeaking,
    isSpeaking,
  } = useSpeechSynthesis({ language: targetLanguage })

  const currentContent = practiceContent[selectedMode]?.[activeContentIndex]

  const handleContentComplete = (score?: number) => {
    const content = practiceContent[selectedMode]?.[activeContentIndex]
    if (content) {
      addToPracticeHistory({
        id: generateId(),
        role: 'system',
        content: `Completed practice: ${content.title}`,
        type: 'text',
        timestamp: new Date().toISOString(),
      })

      setPracticeStats(prev => ({
        ...prev,
        sessionsToday: prev.sessionsToday + 1,
        minutesToday: prev.minutesToday + content.estimatedTime,
        totalXPEarned: prev.totalXPEarned + content.xpReward,
      }))

      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.8 },
        colors: ['#0ea5e9', '#d946ef', '#10b981', '#f59e0b'],
      })
    }

    // Move to next content
    const nextIndex = activeContentIndex + 1
    if (practiceContent[selectedMode] && nextIndex < practiceContent[selectedMode].length) {
      setActiveContentIndex(nextIndex)
    } else {
      setShowContent(false)
      setActiveContentIndex(0)
    }
  }

  const getModeContent = (modeId: string) => {
    const content = practiceContent[modeId] || []
    return content.length
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">Practice</h1>
          <p className="text-gray-600 mt-1">
            Targeted practice sessions for {nativeLanguage} → {targetLanguage}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" leftIcon={<Settings className="w-4 h-4" />}>
            Practice Settings
          </Button>
        </div>
      </div>

      {/* Today's Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={MessageSquare} value={practiceStats.sessionsToday} label="Sessions Today" color="blue" />
        <StatCard icon={Clock} value={`${practiceStats.minutesToday} min`} label="Minutes" color="green" />
        <StatCard icon={Flame} value={`${practiceStats.streakDays} days`} label="Practice Streak" color="amber" />
        <StatCard icon={Zap} value={(practiceStats.totalXPEarned ?? 0).toLocaleString()} label="XP Earned" color="purple" />
      </div>

      {/* Practice Modes */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Choose a Practice Mode</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {practiceModes.map(mode => {
            const Icon = mode.icon
            const contentCount = getModeContent(mode.id)
            const isSelected = selectedMode === mode.id

            return (
              <Button
                key={mode.id}
                onClick={() => {
                  setSelectedMode(mode.id)
                  setShowContent(false)
                  setActiveContentIndex(0)
                }}
                variant={isSelected ? 'primary' : 'ghost'}
                className={cn(
                  'h-40 p-6 flex flex-col items-start justify-between text-left',
                  isSelected ? 'shadow-xl shadow-primary-500/20' : ''
                )}
              >
                <div className={cn(
                  'w-12 h-12 rounded-xl flex items-center justify-center mb-4',
                  isSelected ? 'bg-white/20 text-white' : `${mode.color} text-white`
                )}>
                  <Icon className="w-6 h-6" />
                </div>
                <div className="w-full">
                  <h3 className="font-semibold text-gray-900 mb-1">{mode.label}</h3>
                  <p className="text-sm text-gray-600 mb-2 line-clamp-2">{mode.description}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1">
                      <Layers className="w-3 h-3" />
                      {contentCount} exercises
                    </span>
                    <span className="flex items-center gap-1">
                      <Timer className="w-3 h-3" />
                      {mode.estimatedTime}
                    </span>
                  </div>
                </div>
              </Button>
            )
          })}
        </div>
      </section>

      {/* Selected Mode Content */}
      {showContent && currentContent && (
        <div className="animate-in">
          <div className="mb-4 flex items-center justify-between">
            <Button variant="ghost" onClick={() => setShowContent(false)} leftIcon={<ArrowLeft className="w-4 h-4" />}>
              Back to Modes
            </Button>
            <span className="text-sm text-gray-500">
              Exercise {activeContentIndex + 1} of {practiceContent[selectedMode]?.length || 0}
            </span>
          </div>

          <Card>
            <CardContent className="p-6">
              <ContentRenderer
                content={currentContent}
                targetLanguage={targetLanguage}
                nativeLanguage={nativeLanguage}
                playbackSpeed={1}
                onComplete={handleContentComplete}
                speak={speak}
                stopSpeaking={stopSpeaking}
                isSpeaking={isSpeaking}
              />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Mode Description / Start Button */}
      {!showContent && selectedMode && (() => {
        const mode = practiceModes.find(m => m.id === selectedMode)
        return (
        <Card variant="hover" className="p-8 text-center">
          <div className="max-w-2xl mx-auto">
            <div className={cn(
              'w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4',
              `${mode.color} text-white`
            )}>
              <mode.icon className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">{mode.label}</h2>
            <p className="text-gray-600 mb-6">{mode.description}</p>

            <div className="grid sm:grid-cols-3 gap-4 mb-6 text-left">
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-2xl font-bold text-primary-600">{practiceContent[selectedMode]?.length || 0}+</p>
                <p className="text-sm text-gray-500">Exercises</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-2xl font-bold text-green-600">{mode.estimatedTime}</p>
                <p className="text-sm text-gray-500">Est. Time</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="text-2xl font-bold text-amber-600">{practiceContent[selectedMode]?.reduce((sum, c) => sum + c.xpReward, 0) || 0}+</p>
                <p className="text-sm text-gray-500">Total XP</p>
              </div>
            </div>

            <Button
              variant="primary"
              size="lg"
              className="w-full max-w-md mx-auto"
              onClick={() => setShowContent(true)}
              leftIcon={<Play className="w-5 h-5" />}
            >
              Start Practice
            </Button>
          </div>
        </Card>
      )})}

      {/* Quick Practice Actions */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <QuickActionCard
            title="Daily Pronunciation"
            description="10 minutes of focused pronunciation drills"
            icon={<Mic className="w-6 h-6" />}
            color="green"
            onClick={() => { setSelectedMode('pronunciation'); setShowContent(true); }}
          />
          <QuickActionCard
            title="Vocabulary Review"
            description="Spaced repetition for your weak areas"
            icon={<Layers className="w-6 h-6" />}
            color="purple"
            onClick={() => { setSelectedMode('vocabulary'); setShowContent(true); }}
          />
          <QuickActionCard
            title="Conversation Partner"
            description="Free-flowing chat with AI tutor"
            icon={<MessageSquare className="w-6 h-6" />}
            color="blue"
            onClick={() => { setSelectedMode('conversation'); setShowContent(true); }}
          />
        </div>
      </section>

      {/* Recent Practice History */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Recent Practice</h2>
          <Button variant="ghost" size="sm">View All</Button>
        </div>
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-gray-100">
              {[
                { mode: 'pronunciation', title: 'Spanish Vowels', time: '10 min', score: 92, date: 'Today' },
                { mode: 'vocabulary', title: 'Daily Routine', time: '15 min', score: 88, date: 'Yesterday' },
                { mode: 'grammar', title: 'Present -AR', time: '12 min', score: 95, date: '2 days ago' },
              ].map((session, index) => (
                <div key={index} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center">
                      <Mic className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{session.title}</p>
                      <p className="text-sm text-gray-500">{session.time} • {session.date}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-bold text-green-600">{session.score}%</p>
                    <p className="text-xs text-gray-500">Accuracy</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

// Content Renderer for Practice
function ContentRenderer(props: {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  playbackSpeed: number
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}) {
  const { content, ...rest } = props

  switch (content.type) {
    case 'pronunciation':
      return <PronunciationEvaluator {...props} />
    case 'flashcard':
      return <FlashcardPlayer {...props} />
    case 'exercise':
      return <ExercisePlayer {...props} />
    case 'dialogue':
      return <DialoguePlayer {...props} />
    case 'audio':
      return <AudioPlayerSimple {...props} />
    case 'writing':
      return <WritingEvaluator {...props} />
    default:
      return <div className="p-8 text-center text-gray-500">Content type not supported: {content.type}</div>
  }
}

// Simple Audio Player
function AudioPlayerSimple({ content, targetLanguage, nativeLanguage, onComplete, speak, stopSpeaking, isSpeaking }: any) {
  const data = content.data
  const [isPlaying, setIsPlaying] = useState(false)
  const audioRef = useRef<HTMLAudioElement>(null)

  useEffect(() => {
    if (data.url) {
      audioRef.current = new Audio(data.url)
      audioRef.current.addEventListener('ended', () => {
        setIsPlaying(false)
        onComplete(90)
      })
    }
  }, [data.url])

  const togglePlay = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause()
      } else {
        audioRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  return (
    <div className="space-y-4 text-center">
      <div className="w-24 h-24 mx-auto rounded-full bg-primary-100 flex items-center justify-center">
        <Volume2 className="w-10 h-10 text-primary-600" />
      </div>
      <h3 className="text-xl font-semibold text-gray-900">{data.title}</h3>
      <p className="text-gray-600">{data.transcript}</p>

      <Button variant="primary" size="lg" onClick={togglePlay} leftIcon={isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />} className="w-full max-w-md mx-auto">
        {isPlaying ? 'Pause' : 'Play Audio'}
      </Button>

      {data.translation && (
        <div className="p-4 bg-primary-50 rounded-xl border border-primary-100 text-primary-800">
          {nativeLanguage}: {data.translation}
        </div>
      )}
    </div>
  )
}

// Stat Card
function StatCard({ icon: Icon, value, label, color }: { icon: React.ComponentType<{ className?: string }>; value: string | number; label: string; color: string }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-100 text-blue-600',
    green: 'bg-green-50 border-green-100 text-green-600',
    amber: 'bg-amber-50 border-amber-100 text-amber-600',
    purple: 'bg-purple-50 border-purple-100 text-purple-600',
  }

  return (
    <Card variant="hover" className={`border ${colors[color as keyof typeof colors] || colors.blue}`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-2xl font-bold text-gray-900">{value}</p>
            <p className="text-xs text-gray-500">{label}</p>
          </div>
          <Icon className="w-8 h-8 opacity-50" />
        </div>
      </CardContent>
    </Card>
  )
}

// Quick Action Card
function QuickActionCard({ title, description, icon, color, onClick }: { title: string; description: string; icon: React.ReactNode; color: string; onClick: () => void }) {
  const colors = {
    green: 'bg-green-50 border-green-100 text-green-600',
    purple: 'bg-purple-50 border-purple-100 text-purple-600',
    blue: 'bg-blue-50 border-blue-100 text-blue-600',
  }

  return (
    <Button
      variant="ghost"
      className={`h-32 p-6 text-left border ${colors[color as keyof typeof colors] || colors.blue} hover:shadow-lg`}
      onClick={onClick}
    >
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mb-4', `bg-${color}-100 text-${color}-600`)}>
        {icon}
      </div>
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-600">{description}</p>
    </Button>
  )
}

// Import missing icons
import { ArrowLeft, Play, Pause } from 'lucide-react'
import { useState, useRef, useEffect } from 'react'