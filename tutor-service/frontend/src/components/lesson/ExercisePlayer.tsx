import { useState, useCallback } from 'react'
import {
  CheckCircle,
  XCircle,
  HelpCircle,
  RotateCcw,
  Volume2,
  Mic,
  Keyboard,
  Sparkles,
  Lightbulb,
  Flag,
  ArrowRight,
  Trophy,
  Star,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input, Textarea } from '@/components/ui/Input'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface ExercisePlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
  evaluatePronunciation?: (audioBlob: Blob, targetText: string) => Promise<any>
  evaluateWriting?: (text: string, criteria: string[]) => Promise<any>
}

export function ExercisePlayer({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
  evaluatePronunciation,
  evaluateWriting,
}: ExercisePlayerProps) {
  const data = content.data as {
    question: string
    type: 'multiple_choice' | 'fill_blank' | 'match' | 'order' | 'speak' | 'write' | 'translate'
    options?: string[]
    correctAnswer: string | string[]
    explanation?: string
    hints?: string[]
    audioUrl?: string
    context?: string
    acceptableAnswers?: string[]
    caseSensitive?: boolean
    allowTypos?: boolean
  }

  const [userAnswer, setUserAnswer] = useState<string>('')
  const [selectedOption, setSelectedOption] = useState<number | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [showExplanation, setShowExplanation] = useState(false)
  const [usedHint, setUsedHint] = useState(false)
  const [hintIndex, setHintIndex] = useState(0)
  const [attempts, setAttempts] = useState(0)
  const [showCelebration, setShowCelebration] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null)
  const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)

  const correctAnswers = Array.isArray(data.correctAnswer) ? data.correctAnswer : [data.correctAnswer]
  const acceptableAnswers = data.acceptableAnswers || []

  const checkAnswer = useCallback((answer: string): boolean => {
    const normalizedAnswer = data.caseSensitive ? answer.trim() : answer.trim().toLowerCase()

    for (const correct of correctAnswers) {
      const normalizedCorrect = data.caseSensitive ? correct.trim() : correct.trim().toLowerCase()

      if (normalizedAnswer === normalizedCorrect) return true

      if (data.allowTypos && levenshteinDistance(normalizedAnswer, normalizedCorrect) <= 2) {
        return true
      }
    }

    for (const acceptable of acceptableAnswers) {
      const normalizedAcceptable = data.caseSensitive ? acceptable.trim() : acceptable.trim().toLowerCase()
      if (normalizedAnswer === normalizedAcceptable) return true
    }

    return false
  }, [data.correctAnswer, data.caseSensitive, data.allowTypos, data.acceptableAnswers])

  const handleSubmit = async () => {
    if (!userAnswer.trim() && selectedOption === null && !audioBlob) return

    setAttempts(prev => prev + 1)
    setSubmitted(true)

    let correct = false

    switch (data.type) {
      case 'multiple_choice':
        correct = selectedOption !== null && checkAnswer(data.options?.[selectedOption] || '')
        break
      case 'fill_blank':
      case 'translate':
        correct = checkAnswer(userAnswer)
        break
      case 'speak':
        if (audioBlob && evaluatePronunciation) {
          const result = await evaluatePronunciation(audioBlob, correctAnswers[0])
          correct = result.score >= 70
        }
        break
      case 'write':
        if (evaluateWriting) {
          const result = await evaluateWriting(userAnswer, ['grammar', 'vocabulary', 'coherence'])
          correct = result.score >= 70
        }
        break
    }

    setIsCorrect(correct)

    if (correct) {
      setShowCelebration(true)
      setTimeout(() => onComplete(Math.max(70, 100 - attempts * 10)), 1500)
    }
  }

  const handleTryAgain = () => {
    setUserAnswer('')
    setSelectedOption(null)
    setSubmitted(false)
    setIsCorrect(false)
    setShowExplanation(false)
    setAudioBlob(null)
  }

  const handleNextHint = () => {
    if (data.hints && hintIndex < data.hints.length - 1) {
      setHintIndex(prev => prev + 1)
      setUsedHint(true)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks: BlobPart[] = []

      recorder.ondataavailable = (e) => chunks.push(e.data)
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'audio/webm' })
        setAudioBlob(blob)
        stream.getTracks().forEach(t => t.stop())
      }

      setMediaRecorder(recorder)
      recorder.start()
      setIsRecording(true)
    } catch (error) {
      console.error('Recording failed:', error)
    }
  }

  const stopRecording = () => {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
      setIsRecording(false)
    }
  }

  const playAudio = () => {
    if (data.audioUrl) {
      stopSpeaking()
      const audio = new Audio(data.audioUrl)
      audio.play()
    }
  }

  const speakQuestion = () => {
    speak(data.question)
  }

  // Levenshtein distance for typo tolerance
  function levenshteinDistance(a: string, b: string): number {
    const matrix = Array(b.length + 1).fill(null).map(() => Array(a.length + 1).fill(null))

    for (let i = 0; i <= a.length; i++) matrix[0][i] = i
    for (let j = 0; j <= b.length; j++) matrix[j][0] = j

    for (let j = 1; j <= b.length; j++) {
      for (let i = 1; i <= a.length; i++) {
        const indicator = a[i - 1] === b[j - 1] ? 0 : 1
        matrix[j][i] = Math.min(
          matrix[j][i - 1] + 1,
          matrix[j - 1][i] + 1,
          matrix[j - 1][i - 1] + indicator
        )
      }
    }

    return matrix[b.length][a.length]
  }

  const renderExercise = () => {
    switch (data.type) {
      case 'multiple_choice':
        return (
          <div className="space-y-3">
            {data.options?.map((option, index) => (
              <button
                key={index}
                onClick={() => !submitted && setSelectedOption(index)}
                className={cn(
                  'w-full p-4 rounded-xl border-2 text-left transition-all duration-200',
                  selectedOption === index
                    ? 'border-primary-500 bg-primary-50'
                    : submitted && index === correctAnswers.findIndex(ca => ca.toLowerCase() === option.toLowerCase())
                    ? 'border-green-500 bg-green-50'
                    : submitted && selectedOption === index && !isCorrect
                    ? 'border-red-500 bg-red-50'
                    : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                )}
              >
                <div className="flex items-center gap-3">
                  <div className={cn(
                    'w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0',
                    selectedOption === index
                      ? 'border-primary-500 bg-primary-500'
                      : submitted && index === correctAnswers.findIndex(ca => ca.toLowerCase() === option.toLowerCase())
                      ? 'border-green-500 bg-green-500'
                      : submitted && selectedOption === index && !isCorrect
                      ? 'border-red-500 bg-red-500'
                      : 'border-gray-300'
                  )}>
                    {selectedOption === index && <CheckCircle className="w-4 h-4 text-white" />}
                    {submitted && index === correctAnswers.findIndex(ca => ca.toLowerCase() === option.toLowerCase()) && (
                      <CheckCircle className="w-4 h-4 text-white" />
                    )}
                    {submitted && selectedOption === index && !isCorrect && (
                      <XCircle className="w-4 h-4 text-white" />
                    )}
                  </div>
                  <span className="text-gray-900">{option}</span>
                </div>
              </button>
            ))}
          </div>
        )

      case 'fill_blank':
        return (
          <div className="space-y-4">
            <Input
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder="Type your answer here..."
              disabled={submitted}
              className={cn(
                submitted && isCorrect ? 'border-green-500 bg-green-50' :
                submitted && !isCorrect ? 'border-red-500 bg-red-50' : ''
              )}
              leftIcon={submitted && isCorrect ? <CheckCircle className="w-5 h-5 text-green-500" /> : submitted && !isCorrect ? <XCircle className="w-5 h-5 text-red-500" /> : null}
            />
          </div>
        )

      case 'translate':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-primary-50 rounded-xl border border-primary-100">
              <p className="font-medium text-primary-900">Translate to {nativeLanguage}:</p>
              <p className="text-lg text-primary-700 mt-1">{data.context || data.question}</p>
            </div>
            <Textarea
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder={`Write the translation in ${nativeLanguage}...`}
              disabled={submitted}
              rows={4}
              className={cn(
                submitted && isCorrect ? 'border-green-500 bg-green-50' :
                submitted && !isCorrect ? 'border-red-500 bg-red-50' : ''
              )}
            />
          </div>
        )

      case 'speak':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-green-50 rounded-xl border border-green-100">
              <p className="font-medium text-green-900 mb-2">Pronounce this phrase:</p>
              <p className="text-xl text-green-800 font-medium text-center">{data.question}</p>
            </div>

            <div className="flex items-center justify-center gap-4">
              <Button
                variant={isRecording ? 'danger' : 'primary'}
                size="lg"
                onClick={isRecording ? stopRecording : startRecording}
                leftIcon={isRecording ? <Mic className="w-5 h-5 animate-pulse" /> : <Mic className="w-5 h-5" />}
              >
                {isRecording ? 'Stop Recording' : 'Start Recording'}
              </Button>

              <Button variant="secondary" onClick={playAudio} leftIcon={<Volume2 className="w-5 h-5" />}>
                Hear Native
              </Button>
            </div>

            {audioBlob && (
              <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
                <audio controls src={URL.createObjectURL(audioBlob)} className="w-full" />
                <p className="text-sm text-gray-600 mt-2 text-center">Your recording</p>
              </div>
            )}

            {data.audioUrl && (
              <Button variant="ghost" size="sm" onClick={playAudio} leftIcon={<Volume2 className="w-4 h-4" />}>
                Listen to native pronunciation
              </Button>
            )}
          </div>
        )

      case 'write':
        return (
          <div className="space-y-4">
            <div className="p-4 bg-purple-50 rounded-xl border border-purple-100">
              <p className="font-medium text-purple-900 mb-2">Writing Prompt:</p>
              <p className="text-purple-800">{data.question}</p>
              {data.context && <p className="text-sm text-purple-700 mt-1">{data.context}</p>}
            </div>

            <Textarea
              value={userAnswer}
              onChange={(e) => setUserAnswer(e.target.value)}
              placeholder="Start writing your response here..."
              disabled={submitted}
              rows={8}
              className={cn(
                submitted && isCorrect ? 'border-green-500 bg-green-50' :
                submitted && !isCorrect ? 'border-red-500 bg-red-50' : ''
              )}
            />

            {!submitted && userAnswer.length > 0 && (
              <div className="text-right text-sm text-gray-500">
                {userAnswer.length} characters
              </div>
            )}
          </div>
        )

      default:
        return <div className="text-gray-500 text-center py-8">Exercise type not implemented</div>
    }
  }

  return (
    <div className="space-y-6">
      {/* Question */}
      <div className="p-6 bg-gradient-to-br from-primary-50 to-accent-50 rounded-2xl border border-primary-100">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-primary-500 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <p className="text-lg font-medium text-gray-900">{data.question}</p>
            {data.context && <p className="text-sm text-gray-600 mt-1">{data.context}</p>}
          </div>
          <Button variant="ghost" size="icon" onClick={speakQuestion} className="mt-0.5">
            <Volume2 className="w-5 h-5" />
          </Button>
        </div>
      </div>

      {/* Exercise Content */}
      <Card>
        <CardContent className="p-6">
          {renderExercise()}
        </CardContent>
      </Card>

      {/* Feedback & Actions */}
      {submitted && (
        <Card variant={isCorrect ? 'gradient' : 'default'} className="animate-in">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className={cn(
                'w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0',
                isCorrect ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
              )}>
                {isCorrect ? <CheckCircle className="w-6 h-6" /> : <XCircle className="w-6 h-6" />}
              </div>
              <div className="flex-1">
                <h3 className={cn('font-semibold', isCorrect ? 'text-green-800' : 'text-red-800')}>
                  {isCorrect ? 'Correct! 🎉' : 'Not quite right'}
                </h3>
                <p className={cn('mt-1', isCorrect ? 'text-green-700' : 'text-red-700')}>
                  {isCorrect
                    ? `Great job! ${attempts === 1 ? 'First try!' : 'Attempt ' + attempts}`
                    : 'Keep practicing, you\'ll get it!'}
                </p>

                {data.explanation && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowExplanation(!showExplanation)}
                    className="mt-2"
                    leftIcon={<HelpCircle className="w-4 h-4" />}
                  >
                    {showExplanation ? 'Hide' : 'Show'} Explanation
                  </Button>
                )}
              </div>
            </div>

            {showExplanation && data.explanation && (
              <div className="mt-4 p-4 bg-white/50 rounded-xl border border-gray-200 animate-in">
                <p className="text-gray-700">{data.explanation}</p>
              </div>
            )}

            {!isCorrect && (
              <div className="mt-4 flex gap-3">
                {data.hints && data.hints.length > 0 && hintIndex < data.hints.length && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleNextHint}
                    leftIcon={<Lightbulb className="w-4 h-4" />}
                  >
                    Hint {hintIndex + 1}: {data.hints[hintIndex]}
                  </Button>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleTryAgain}
                  leftIcon={<RotateCcw className="w-4 h-4" />}
                >
                  Try Again
                </Button>
              </div>
            )}

            {isCorrect && (
              <Button
                variant="primary"
                size="lg"
                className="w-full"
                onClick={() => onComplete(Math.max(70, 100 - attempts * 10))}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Continue
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Hint Button (before submit) */}
      {!submitted && data.hints && data.hints.length > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => { setUsedHint(true); setHintIndex(0); }}
          leftIcon={<Lightbulb className="w-4 h-4" />}
        >
          Show Hint
        </Button>
      )}

      {/* Submit Button */}
      {!submitted && (
        <Button
          variant="primary"
          size="lg"
          className="w-full"
          onClick={handleSubmit}
          disabled={!userAnswer.trim() && selectedOption === null && data.type !== 'speak' || isRecording}
        >
          {isRecording ? 'Finish Recording' : 'Submit Answer'}
        </Button>
      )}
    </div>
  )
}

export default ExercisePlayer