import { useState, useCallback, useEffect } from 'react'
import {
  CheckCircle,
  XCircle,
  HelpCircle,
  RotateCcw,
  ArrowRight,
  Trophy,
  Star,
  Target,
  Clock,
  AlertCircle,
  Sparkles,
  BookOpen,
  Flag,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface QuizPlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function QuizPlayer({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: QuizPlayerProps) {
  const data = content.data as {
    questions: {
      id: string
      question: string
      type: 'single' | 'multiple' | 'true_false' | 'input'
      options?: string[]
      correctAnswer: string | string[]
      explanation?: string
      hints?: string[]
      audioUrl?: string
      points?: number
      image?: string
    }[]
    settings?: {
      timeLimit?: number
      passingScore?: number
      shuffleQuestions?: boolean
      shuffleOptions?: boolean
      showFeedback?: boolean
    }
    passingScore?: number
    timeLimit?: number
  }

  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({})
  const [submitted, setSubmitted] = useState(false)
  const [showFeedback, setShowFeedback] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [timeRemaining, setTimeRemaining] = useState(data.timeLimit || data.settings?.timeLimit || 0)
  const [quizStartTime, setQuizStartTime] = useState<Date | null>(null)
  const [usedHints, setUsedHints] = useState<Record<string, number>>({})

  const questions = data.questions
  const currentQuestion = questions[currentQuestionIndex]
  const isLastQuestion = currentQuestionIndex >= questions.length - 1

  // Timer
  useEffect(() => {
    if (timeRemaining > 0 && !showResults) {
      const timer = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            clearInterval(timer)
            handleTimeUp()
            return 0
          }
          return prev - 1
        })
      }, 1000)
      return () => clearInterval(timer)
    }
  }, [timeRemaining, showResults])

  // Initialize quiz
  useEffect(() => {
    if (!quizStartTime) {
      setQuizStartTime(new Date())
      // Shuffle if needed
      if (data.settings?.shuffleQuestions) {
        // Would shuffle questions array
      }
    }
  }, [quizStartTime])

  const handleTimeUp = () => {
    // Auto-submit when time runs out
    handleFinishQuiz()
  }

  const handleAnswerChange = useCallback((questionId: string, answer: string | string[]) => {
    setAnswers(prev => ({ ...prev, [questionId]: answer }))
  }, [])

  const handleNextQuestion = useCallback(() => {
    if (!isLastQuestion) {
      setCurrentQuestionIndex(prev => prev + 1)
      setShowFeedback(false)
    } else {
      handleFinishQuiz()
    }
  }, [isLastQuestion])

  const handlePrevQuestion = useCallback(() => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1)
      setShowFeedback(false)
    }
  }, [currentQuestionIndex])

  const handleFinishQuiz = useCallback(() => {
    let correctCount = 0
    let totalPoints = 0
    let earnedPoints = 0

    questions.forEach(q => {
      const userAnswer = answers[q.id]
      const points = q.points || 1
      totalPoints += points

      let isCorrect = false
      const correctAnswers = Array.isArray(q.correctAnswer) ? q.correctAnswer : [q.correctAnswer]

      if (userAnswer !== undefined) {
        if (q.type === 'multiple') {
          const userArr = Array.isArray(userAnswer) ? userAnswer : [userAnswer]
          isCorrect = userArr.length === correctAnswers.length &&
            userArr.every(a => correctAnswers.includes(a))
        } else {
          const userStr = Array.isArray(userAnswer) ? userAnswer[0] : userAnswer
          isCorrect = correctAnswers.some(ca =>
            ca.toLowerCase().trim() === userStr.toLowerCase().trim()
          )
        }
      }

      if (isCorrect) {
        correctCount++
        earnedPoints += points
      }
    })

    const score = totalPoints > 0 ? Math.round((earnedPoints / totalPoints) * 100) : 0
    setShowResults(true)

    // Complete after showing results
    setTimeout(() => {
      const passing = data.passingScore || data.settings?.passingScore || 70
      if (score >= passing) {
        onComplete(score)
      }
    }, 3000)
  }, [questions, answers, data.passingScore, data.settings?.passingScore, onComplete])

  const handleRetry = useCallback(() => {
    setAnswers({})
    setSubmitted(false)
    setShowFeedback(false)
    setShowResults(false)
    setCurrentQuestionIndex(0)
    setQuizStartTime(null)
    setTimeRemaining(data.timeLimit || data.settings?.timeLimit || 0)
  }, [data.timeLimit, data.settings?.timeLimit])

  const playAudio = useCallback(() => {
    if (currentQuestion.audioUrl) {
      const audio = new Audio(currentQuestion.audioUrl)
      audio.play()
    }
  }, [currentQuestion])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Results View
  if (showResults) {
    const correctCount = questions.filter(q => {
      const userAnswer = answers[q.id]
      const correctAnswers = Array.isArray(q.correctAnswer) ? q.correctAnswer : [q.correctAnswer]
      if (userAnswer === undefined) return false
      if (q.type === 'multiple') {
        const userArr = Array.isArray(userAnswer) ? userAnswer : [userAnswer]
        return userArr.length === correctAnswers.length && userArr.every(a => correctAnswers.includes(a))
      } else {
        const userStr = Array.isArray(userAnswer) ? userAnswer[0] : userAnswer
        return correctAnswers.some(ca => ca.toLowerCase().trim() === userStr.toLowerCase().trim())
      }
    }).length

    const totalTime = quizStartTime ? Math.floor((Date.now() - quizStartTime.getTime()) / 1000) : 0
    const passing = data.passingScore || data.settings?.passingScore || 70
    const passed = (correctCount / questions.length) * 100 >= passing

    return (
      <div className="space-y-6 animate-in">
        {/* Result Header */}
        <div className="text-center mb-8">
          <div className={cn(
            'w-20 h-20 mx-auto mb-4 rounded-full flex items-center justify-center',
            passed ? 'bg-gradient-to-br from-green-500 to-emerald-500' : 'bg-gradient-to-br from-amber-500 to-orange-500'
          )}>
            {passed ? <Trophy className="w-10 h-10 text-white" /> : <Target className="w-10 h-10 text-white" />}
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            {passed ? 'Quiz Passed! 🎉' : 'Keep Practicing'}
          </h2>
          <p className="text-gray-600">
            You scored <span className="font-bold text-primary-600">{correctCount}/{questions.length}</span> ({Math.round((correctCount / questions.length) * 100)}%)
          </p>
        </div>

        {/* Score Breakdown */}
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="grid grid-cols-4 gap-4 text-center">
              <div className="p-4 bg-green-50 rounded-xl">
                <p className="text-2xl font-bold text-green-600">{correctCount}</p>
                <p className="text-sm text-green-700">Correct</p>
              </div>
              <div className="p-4 bg-red-50 rounded-xl">
                <p className="text-2xl font-bold text-red-600">{questions.length - correctCount}</p>
                <p className="text-sm text-red-700">Incorrect</p>
              </div>
              <div className="p-4 bg-blue-50 rounded-xl">
                <p className="text-2xl font-bold text-blue-600">{formatTime(totalTime)}</p>
                <p className="text-sm text-blue-700">Time</p>
              </div>
              <div className="p-4 bg-purple-50 rounded-xl">
                <p className="text-2xl font-bold text-purple-600">{passed ? 'Passed' : 'Failed'}</p>
                <p className="text-sm text-purple-700">Status</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Question Review */}
        <div className="space-y-3">
          <h3 className="font-semibold text-gray-900">Question Review</h3>
          {questions.map((q, index) => {
            const userAnswer = answers[q.id]
            const correctAnswers = Array.isArray(q.correctAnswer) ? q.correctAnswer : [q.correctAnswer]
            let isCorrect = false

            if (userAnswer !== undefined) {
              if (q.type === 'multiple') {
                const userArr = Array.isArray(userAnswer) ? userAnswer : [userAnswer]
                isCorrect = userArr.length === correctAnswers.length && userArr.every(a => correctAnswers.includes(a))
              } else {
                const userStr = Array.isArray(userAnswer) ? userAnswer[0] : userAnswer
                isCorrect = correctAnswers.some(ca => ca.toLowerCase().trim() === userStr.toLowerCase().trim())
              }
            }

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
                    {!isCorrect && userAnswer !== undefined && (
                      <p className="text-sm text-red-600 mt-1">
                        Your answer: {Array.isArray(userAnswer) ? userAnswer.join(', ') : userAnswer}
                      </p>
                    )}
                    {!isCorrect && (
                      <p className="text-sm text-green-600 mt-1">
                        Correct: {correctAnswers.join(', ')}
                      </p>
                    )}
                    {q.explanation && (
                      <p className="text-xs text-gray-500 mt-2">{q.explanation}</p>
                    )}
                  </div>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Actions */}
        <div className="flex gap-4 justify-center">
          {questions.length - correctCount > 0 && (
            <Button variant="secondary" onClick={handleRetry} leftIcon={<RotateCcw className="w-4 h-4" />}>
              Retry Quiz
            </Button>
          )}
          <Button
            variant={passed ? 'primary' : 'secondary'}
            onClick={() => passed ? onComplete(Math.round((correctCount / questions.length) * 100)) : handleRetry}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {passed ? 'Continue' : 'Try Again'}
          </Button>
        </div>
      </div>
    )
  }

  // Question View
  const userAnswer = answers[currentQuestion.id]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">Question {currentQuestionIndex + 1} of {questions.length}</p>
          <div className="flex items-center gap-4 mt-1">
            {timeRemaining > 0 && (
              <div className={cn(
                'flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
                timeRemaining <= 60 ? 'bg-red-100 text-red-700 animate-pulse' : 'bg-gray-100 text-gray-700'
              )}>
                <Clock className="w-4 h-4" />
                {formatTime(timeRemaining)}
              </div>
            )}
            <span className="text-sm text-gray-500">
              {currentQuestion.points ? `${currentQuestion.points} pts` : '1 pt'}
            </span>
          </div>
        </div>

        <div className="text-right">
          <p className="text-lg font-bold text-primary-600">
            {Math.round(((currentQuestionIndex) / questions.length) * 100)}%
          </p>
          <p className="text-xs text-gray-500">Progress</p>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-6">
        <div
          className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
          style={{ width: `${((currentQuestionIndex) / questions.length) * 100}%` }}
        />
      </div>

      {/* Question Card */}
      <Card>
        <CardContent className="p-6">
          {currentQuestion.image && (
            <div className="mb-4 rounded-xl overflow-hidden">
              <img src={currentQuestion.image} alt="" className="w-full h-auto" />
            </div>
          )}

          <div className="mb-6">
            <p className="text-xl font-medium text-gray-900">{currentQuestion.question}</p>
            {currentQuestion.audioUrl && (
              <Button variant="ghost" size="sm" onClick={playAudio} className="mt-2" leftIcon={<Volume2 className="w-4 h-4" />}>
                Listen to Question
              </Button>
            )}
          </div>

          {/* Answer Options */}
          <div className="space-y-3">
            {currentQuestion.type === 'single' && currentQuestion.options && (
              <>
                {currentQuestion.options.map((option, index) => (
                  <button
                    key={index}
                    onClick={() => !showFeedback && handleAnswerChange(currentQuestion.id, option)}
                    className={cn(
                      'w-full p-4 rounded-xl border-2 text-left transition-all duration-200',
                      userAnswer === option
                        ? 'border-primary-500 bg-primary-50'
                        : showFeedback && correctAnswers.includes(option)
                        ? 'border-green-500 bg-green-50'
                        : showFeedback && userAnswer === option && !correctAnswers.includes(option)
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                        userAnswer === option
                          ? 'border-primary-500'
                          : showFeedback && correctAnswers.includes(option)
                          ? 'border-green-500'
                          : showFeedback && userAnswer === option && !correctAnswers.includes(option)
                          ? 'border-red-500'
                          : 'border-gray-300'
                      )}>
                        {(userAnswer === option || (showFeedback && correctAnswers.includes(option))) && (
                          <CheckCircle className="w-4 h-4" style={{ color: userAnswer === option && showFeedback && !correctAnswers.includes(option) ? 'white' : undefined }} />
                        )}
                      </div>
                      <span className="text-gray-900">{option}</span>
                    </div>
                  </button>
                ))}
              </>
            )}

            {currentQuestion.type === 'multiple' && currentQuestion.options && (
              <>
                <p className="text-sm text-gray-500 mb-2">Select all that apply</p>
                {currentQuestion.options.map((option, index) => {
                  const userAnswers = (Array.isArray(userAnswer) ? userAnswer : []) as string[]
                  const isSelected = userAnswers.includes(option)
                  return (
                    <button
                      key={index}
                      onClick={() => {
                        if (showFeedback) return
                        const newAnswers = isSelected
                          ? userAnswers.filter(a => a !== option)
                          : [...userAnswers, option]
                        handleAnswerChange(currentQuestion.id, newAnswers)
                      }}
                      className={cn(
                        'w-full p-4 rounded-xl border-2 text-left transition-all duration-200',
                        isSelected
                          ? 'border-primary-500 bg-primary-50'
                          : showFeedback && correctAnswers.includes(option)
                          ? 'border-green-500 bg-green-50'
                          : showFeedback && isSelected && !correctAnswers.includes(option)
                          ? 'border-red-500 bg-red-50'
                          : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                      )}
                    >
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          'w-6 h-6 rounded border-2 flex items-center justify-center flex-shrink-0',
                          isSelected
                            ? 'border-primary-500 bg-primary-500'
                            : showFeedback && correctAnswers.includes(option)
                            ? 'border-green-500 bg-green-500'
                            : showFeedback && isSelected && !correctAnswers.includes(option)
                            ? 'border-red-500 bg-red-500'
                            : 'border-gray-300'
                        )}>
                          {isSelected && <CheckCircle className="w-4 h-4 text-white" />}
                          {showFeedback && correctAnswers.includes(option) && <CheckCircle className="w-4 h-4 text-white" />}
                          {showFeedback && isSelected && !correctAnswers.includes(option) && <XCircle className="w-4 h-4 text-white" />}
                        </div>
                        <span className="text-gray-900">{option}</span>
                      </div>
                    </button>
                  )
                })}
              </>
            )}

            {currentQuestion.type === 'true_false' && (
              <>
                {['True', 'False'].map((option, index) => (
                  <button
                    key={index}
                    onClick={() => !showFeedback && handleAnswerChange(currentQuestion.id, option)}
                    className={cn(
                      'w-full p-4 rounded-xl border-2 text-left transition-all duration-200',
                      userAnswer === option
                        ? 'border-primary-500 bg-primary-50'
                        : showFeedback && correctAnswers.includes(option)
                        ? 'border-green-500 bg-green-50'
                        : showFeedback && userAnswer === option && !correctAnswers.includes(option)
                        ? 'border-red-500 bg-red-50'
                        : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        'w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                        userAnswer === option
                          ? 'border-primary-500'
                          : showFeedback && correctAnswers.includes(option)
                          ? 'border-green-500'
                          : showFeedback && userAnswer === option && !correctAnswers.includes(option)
                          ? 'border-red-500'
                          : 'border-gray-300'
                      )}>
                        {(userAnswer === option || (showFeedback && correctAnswers.includes(option))) && (
                          <CheckCircle className="w-4 h-4" style={{ color: userAnswer === option && showFeedback && !correctAnswers.includes(option) ? 'white' : undefined }} />
                        )}
                      </div>
                      <span className="text-gray-900 text-lg font-medium">{option}</span>
                    </div>
                  </button>
                ))}
              </>
            )}

            {currentQuestion.type === 'input' && (
              <div className="space-y-2">
                <Input
                  value={typeof userAnswer === 'string' ? userAnswer : ''}
                  onChange={(e) => handleAnswerChange(currentQuestion.id, e.target.value)}
                  placeholder="Type your answer..."
                  disabled={showFeedback}
                  className={cn(
                    showFeedback && correctAnswers.some(ca => ca.toLowerCase() === (userAnswer || '').toLowerCase().trim())
                      ? 'border-green-500 bg-green-50'
                      : showFeedback && userAnswer && !correctAnswers.some(ca => ca.toLowerCase() === (userAnswer || '').toLowerCase().trim())
                      ? 'border-red-500 bg-red-50'
                      : ''
                  )}
                />
                {currentQuestion.hints && currentQuestion.hints.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const hintIndex = (usedHints[currentQuestion.id] || 0)
                      if (hintIndex < currentQuestion.hints!.length) {
                        setUsedHints(prev => ({ ...prev, [currentQuestion.id]: hintIndex + 1 }))
                      }
                    }}
                    leftIcon={<HelpCircle className="w-4 h-4" />}
                  >
                    Show Hint {usedHints[currentQuestion.id] + 1}
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Explanation */}
          {showFeedback && currentQuestion.explanation && (
            <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
              <p className="text-sm text-gray-700">{currentQuestion.explanation}</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="secondary"
          onClick={handlePrevQuestion}
          disabled={currentQuestionIndex === 0}
          leftIcon={<ArrowLeft className="w-4 h-4" />}
        >
          Previous
        </Button>

        <div className="flex gap-2">
          {currentQuestion.hints && currentQuestion.hints.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const hintIndex = (usedHints[currentQuestion.id] || 0)
                if (hintIndex < currentQuestion.hints.length) {
                  setUsedHints(prev => ({ ...prev, [currentQuestion.id]: hintIndex + 1 }))
                }
              }}
              leftIcon={<HelpCircle className="w-4 h-4" />}
            >
              Hint
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowFeedback(true)}
            leftIcon={<Flag className="w-4 h-4" />}
          >
            Check Answer
          </Button>
        </div>

        <Button
          variant={isLastQuestion ? 'primary' : 'secondary'}
          onClick={isLastQuestion ? handleFinishQuiz : handleNextQuestion}
          disabled={showResults}
          rightIcon={<ArrowRight className="w-4 h-4" />}
        >
          {isLastQuestion ? 'Finish Quiz' : 'Next Question'}
        </Button>
      </div>
    </div>
  )
}

// Import Volume2
import { Volume2 } from 'lucide-react'