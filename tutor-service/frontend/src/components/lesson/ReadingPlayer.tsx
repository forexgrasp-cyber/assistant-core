import { useState, useCallback } from 'react'
import {
  Volume2,
  Globe,
  Sparkles,
  CheckCircle,
  ArrowRight,
  Highlighter,
  Search,
  Copy,
  BookOpen,
  Type,
  Minus,
  Plus,
  RotateCcw,
  Trophy,
  Target,
  ArrowLeft,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface ReadingPlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function ReadingPlayer({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: ReadingPlayerProps) {
  const data = content.data as {
    text: string
    translation?: string
    title?: string
    author?: string
    difficulty?: 'beginner' | 'intermediate' | 'advanced'
    wordCount?: number
    estimatedReadTime?: number
    vocabulary?: { word: string; translation: string; context?: string }[]
    questions?: {
      id: string
      question: string
      type: 'comprehension' | 'vocabulary' | 'inference'
      options: string[]
      correctAnswer: string
      explanation?: string
    }[]
    audioUrl?: string
  }

  const [fontSize, setFontSize] = useState(1)
  const [showTranslation, setShowTranslation] = useState(false)
  const [showVocabulary, setShowVocabulary] = useState(false)
  const [highlightedWords, setHighlightedWords] = useState<string[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [showQuestions, setShowQuestions] = useState(false)
  const [submittedQuestions, setSubmittedQuestions] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [readProgress, setReadProgress] = useState(0)

  const handleFontSizeChange = (delta: number) => {
    setFontSize(prev => Math.max(0.8, Math.min(2, prev + delta)))
  }

  const toggleWordHighlight = (word: string) => {
    setHighlightedWords(prev =>
      prev.includes(word)
        ? prev.filter(w => w !== word)
        : [...prev, word.toLowerCase()]
    )
  }

  const handleAnswerChange = (questionId: string, answer: string) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
  }

  const handleSubmitQuestions = () => {
    let correct = 0
    data.questions?.forEach(q => {
      if (answers[q.id] === q.correctAnswer) correct++
    })
    setSubmittedQuestions(true)
    if (data.questions && correct >= data.questions.length * 0.7) {
      setShowResults(true)
    }
  }

  const handleRetryQuestions = () => {
    setAnswers({})
    setSubmittedQuestions(false)
  }

  const playFullAudio = () => {
    if (data.audioUrl) {
      const audio = new Audio(data.audioUrl)
      audio.play()
    } else {
      speak(data.text)
    }
  }

  // Calculate read progress based on scroll
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget
    const progress = target.scrollTop / (target.scrollHeight - target.clientHeight)
    setReadProgress(Math.min(100, Math.max(0, progress * 100)))
  }, [])

  // Split text into paragraphs
  const paragraphs = data.text.split('\n\n').filter(p => p.trim())

  // Results View
  if (showResults && data.questions && data.questions.length > 0) {
    let correct = 0
    data.questions.forEach(q => {
      if (answers[q.id] === q.correctAnswer) correct++
    })

    return (
      <div className="space-y-6 animate-in">
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Reading Complete!</h2>
          <p className="text-gray-600">
            You answered <span className="font-bold text-primary-600">{correct}/{data.questions.length}</span> questions correctly.
          </p>
        </div>

        <Card variant="glass">
          <CardContent className="p-4">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-4 bg-green-50 rounded-xl">
                <p className="text-2xl font-bold text-green-600">{correct}</p>
                <p className="text-sm text-green-700">Correct</p>
              </div>
              <div className="p-4 bg-red-50 rounded-xl">
                <p className="text-2xl font-bold text-red-600">{data.questions.length - correct}</p>
                <p className="text-sm text-red-700">Incorrect</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-xl">
                <p className="text-2xl font-bold text-blue-600">{Math.round(readProgress)}%</p>
                <p className="text-sm text-blue-700">Read</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-3">
          <h3 className="font-semibold text-gray-900">Question Review</h3>
          {data.questions.map((q, index) => {
            const userAnswer = answers[q.id]
            const isCorrect = userAnswer === q.correctAnswer
            return (
              <Card key={q.id} variant={isCorrect ? 'hover' : 'default'} className="p-4">
                <div className="flex items-start gap-3">
                  <div className={cn(
                    'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                    isCorrect ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'
                  )}>
                    {isCorrect ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 text-sm">{q.question}</p>
                    {!isCorrect && (
                      <p className="text-sm text-red-600 mt-1">Your answer: {userAnswer || 'Not answered'}</p>
                    )}
                    <p className="text-sm text-green-600 mt-1">Correct: {q.correctAnswer}</p>
                    {q.explanation && <p className="text-xs text-gray-500 mt-2">{q.explanation}</p>}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        <div className="flex gap-4 justify-center">
          <Button variant="secondary" onClick={handleRetryQuestions} leftIcon={<RotateCcw className="w-4 h-4" />}>
            Retry Questions
          </Button>
          <Button variant="primary" onClick={() => onComplete(Math.round((correct / data.questions!.length) * 100))} rightIcon={<ArrowRight className="w-4 h-4" />}>
            Continue
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 bg-gray-100 rounded-xl p-1">
            <Button variant="ghost" size="icon" onClick={() => handleFontSizeChange(-0.1)} className="p-1">
              <Minus className="w-4 h-4" />
            </Button>
            <span className="px-3 text-sm font-medium text-gray-700">{Math.round(fontSize * 100)}%</span>
            <Button variant="ghost" size="icon" onClick={() => handleFontSizeChange(0.1)} className="p-1">
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant={showTranslation ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setShowTranslation(!showTranslation)}
              leftIcon={<Globe className="w-4 h-4" />}
            >
              Translation
            </Button>
            <Button
              variant={showVocabulary ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => setShowVocabulary(!showVocabulary)}
              leftIcon={<BookOpen className="w-4 h-4" />}
            >
              Vocabulary
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowQuestions(!showQuestions)}
              leftIcon={<Type className="w-4 h-4" />}
            >
              Questions
            </Button>
          </div>
        </div>

        {data.audioUrl && (
          <Button variant="primary" size="sm" onClick={playFullAudio} leftIcon={<Volume2 className="w-4 h-4" />}>
            Listen
          </Button>
        )}
      </div>

      {/* Read Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Reading Progress</span>
          <span className="font-medium text-gray-900">{Math.round(readProgress)}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
            style={{ width: `${readProgress}%` }}
          />
        </div>
      </div>

      {/* Reading Text */}
      <Card className="overflow-hidden">
        <CardContent className="p-0">
          {/* Title */}
          {data.title && (
            <div className="p-6 bg-gray-50 border-b border-gray-100 text-center">
              <h2 className="text-xl font-bold text-gray-900">{data.title}</h2>
              {data.author && <p className="text-sm text-gray-500 mt-1">by {data.author}</p>}
            </div>
          )}

          {/* Target Language Text */}
          <div
            className="p-6 max-h-[600px] overflow-y-auto prose prose-primary max-w-none"
            style={{ fontSize: `${fontSize}rem` }}
            onScroll={handleScroll}
          >
            {showTranslation && data.translation ? (
              <div className="space-y-4">
                {paragraphs.map((para, index) => (
                  <div key={index} className="border-b border-gray-100 pb-4 last:border-0">
                    <p className="text-gray-900 leading-relaxed mb-2">{para}</p>
                    <p className="text-primary-700 leading-relaxed italic text-sm">
                      {data.translation.split('\n\n')[index] || ''}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {paragraphs.map((para, index) => (
                  <p
                    key={index}
                    className="text-gray-900 leading-relaxed cursor-text transition-colors"
                    onClick={() => {
                      // Could implement word-by-word translation here
                    }}
                  >
                    {para.split(' ').map((word, wi) => {
                      const cleanWord = word.replace(/[.,!?;:()[\]{}"']/g, '').toLowerCase()
                      const isHighlighted = highlightedWords.includes(cleanWord)
                      return (
                        <span
                          key={wi}
                          className={cn(
                            'transition-colors',
                            isHighlighted ? 'bg-yellow-100 text-yellow-900 px-0.5 rounded cursor-pointer' : ''
                          )}
                          onClick={(e) => {
                            e.stopPropagation()
                            toggleWordHighlight(cleanWord)
                          }}
                        >
                          {word}&#8203;
                        </span>
                      )
                    })}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Translation Panel */}
          {showTranslation && data.translation && !showTranslation && (
            <div className="p-6 bg-primary-50 border-t border-primary-100 animate-in">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold text-primary-900">{nativeLanguage} Translation</h3>
                <Button variant="ghost" size="icon" onClick={() => setShowTranslation(false)}>
                  <RotateCcw className="w-4 h-4" />
                </Button>
              </div>
              <div className="prose prose-sm text-primary-800">
                {data.translation}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Vocabulary Sidebar */}
      {showVocabulary && data.vocabulary && data.vocabulary.length > 0 && (
        <Card variant="glass" className="animate-in">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Key Vocabulary</h3>
              <Button variant="ghost" size="icon" onClick={() => setShowVocabulary(false)}>
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>
            <div className="grid sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
              {data.vocabulary.map((vocab, index) => (
                <Button
                  key={index}
                  variant="outline"
                  size="sm"
                  className="w-full justify-start text-left"
                  onClick={() => speak(`${vocab.word}. ${vocab.translation}`)}
                >
                  <span className="font-medium text-gray-900">{vocab.word}</span>
                  <span className="text-primary-600 ml-2">- {vocab.translation}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Comprehension Questions */}
      {showQuestions && data.questions && data.questions.length > 0 && (
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Comprehension Questions</h3>
              <Button variant="ghost" size="icon" onClick={() => setShowQuestions(false)}>
                <RotateCcw className="w-4 h-4" />
              </Button>
            </div>

            {!submittedQuestions ? (
              <div className="space-y-4">
                {data.questions.map((q, index) => (
                  <div key={q.id} className="p-4 bg-white rounded-xl border border-gray-200">
                    <p className="font-medium text-gray-900 mb-3">{index + 1}. {q.question}</p>
                    <div className="space-y-2">
                      {q.options.map((option, optIndex) => (
                        <label
                          key={optIndex}
                          className={cn(
                            'flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors',
                            answers[q.id] === option
                              ? 'bg-primary-50 border border-primary-200'
                              : 'border border-gray-200 hover:bg-gray-50'
                          )}
                        >
                          <input
                            type="radio"
                            name={`q-${q.id}`}
                            value={option}
                            checked={answers[q.id] === option}
                            onChange={() => handleAnswerChange(q.id, option)}
                            className="w-4 h-4 text-primary-600 focus:ring-primary-500"
                          />
                          <span className="text-gray-700">{option}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                ))}

                <Button
                  variant="primary"
                  className="w-full"
                  onClick={handleSubmitQuestions}
                  disabled={Object.keys(answers).length < data.questions.length}
                >
                  Submit Answers
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {data.questions.map((q, index) => {
                  const userAnswer = answers[q.id]
                  const isCorrect = userAnswer === q.correctAnswer
                  return (
                    <div key={q.id} className={cn(
                      'p-4 rounded-xl',
                      isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                    )}>
                      <div className="flex items-center gap-2 mb-2">
                        <span className={isCorrect ? 'text-green-600' : 'text-red-600'}>
                          {isCorrect ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                        </span>
                        <span className="font-medium text-gray-900 text-sm">{index + 1}. {q.question}</span>
                      </div>
                      <p className="text-sm text-gray-600">
                        Your answer: {userAnswer || 'Not answered'}
                      </p>
                      {!isCorrect && (
                        <p className="text-sm text-green-600 mt-1">
                          Correct answer: {q.correctAnswer}
                        </p>
                      )}
                      {q.explanation && (
                        <p className="text-xs text-gray-500 mt-2">{q.explanation}</p>
                      )}
                    </div>
                  )
                })}

                <Button variant="secondary" className="w-full" onClick={handleRetryQuestions} leftIcon={<RotateCcw className="w-4 h-4" />}>
                  Try Again
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Continue Button */}
      {(data.questions && data.questions.length === 0) || (!data.questions && readProgress >= 90) ? (
        <Button
          variant="primary"
          className="w-full"
          onClick={() => onComplete(90)}
          rightIcon={<ArrowRight className="w-4 h-4" />}
          size="lg"
        >
          Mark as Complete
        </Button>
      ) : null}
    </div>
  )
}