import { useState, useRef, useCallback, useEffect } from 'react'
import {
  PenTool,
  CheckCircle,
  XCircle,
  HelpCircle,
  RotateCcw,
  Sparkles,
  ArrowRight,
  Trophy,
  Target,
  BookOpen,
  FileText,
  Copy,
  Download,
  Share2,
  Flag,
  AlertCircle,
  Highlighter,
  Underline,
  Strikethrough,
  Type,
  Zap,
  Wand2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Textarea } from '@/components/ui/Input'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import confetti from 'canvas-confetti'
import type { LessonContent } from '@/types'

interface WritingEvaluatorProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
  evaluateWriting?: (text: string, criteria: string[]) => Promise<any>
}

export function WritingEvaluator({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
  evaluateWriting,
}: WritingEvaluatorProps) {
  const data = content.data as {
    prompt: string
    minWords?: number
    maxWords?: number
    template?: string
    criteria: { name: string; description: string; weight: number }[]
    examples?: string[]
    context?: string
    vocabulary?: { word: string; translation: string }[]
    rubric?: { level: string; description: string; scoreRange: string }[]
  }

  const [text, setText] = useState(data.template || '')
  const [result, setResult] = useState<{
    score: number
    corrections: {
      original: string
      corrected: string
      type: string
      explanation: string
      position: { start: number; end: number }
      severity: 'minor' | 'major' | 'critical'
    }[]
    feedback: string
    criteriaScores: Record<string, number>
  } | null>(null)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [showCriteria, setShowCriteria] = useState(true)
  const [showVocabulary, setShowVocabulary] = useState(false)
  const [confettiTrigger, setConfettiTrigger] = useState(0)
  const [attempts, setAttempts] = useState(0)
  const [currentTab, setCurrentTab] = useState<'write' | 'review' | 'examples'>('write')

  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Confetti effect
  useEffect(() => {
    if (confettiTrigger > 0) {
      confetti({
        particleCount: 60,
        spread: 50,
        origin: { y: 0.8 },
        colors: ['#0ea5e9', '#d946ef', '#10b981', '#f59e0b'],
      })
    }
  }, [confettiTrigger])

  // Word count
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const charCount = text.length
  const meetsMinWords = !data.minWords || wordCount >= data.minWords
  const meetsMaxWords = !data.maxWords || wordCount <= data.maxWords

  const handleEvaluate = useCallback(async () => {
    if (!text.trim() || !meetsMinWords) return

    setIsEvaluating(true)
    try {
      // In production, this would call the actual writing evaluation API
      await new Promise(resolve => setTimeout(resolve, 2000))

      // Simulate evaluation result
      const criteriaScores: Record<string, number> = {}
      data.criteria.forEach(c => {
        criteriaScores[c.name] = Math.floor(Math.random() * 30) + 70
      })

      const overallScore = Math.round(
        data.criteria.reduce((sum, c) => sum + criteriaScores[c.name] * c.weight, 0)
      )

      // Generate mock corrections
      const corrections = generateMockCorrections(text)

      const feedback = generateFeedback(overallScore, corrections.length)

      setResult({
        score: overallScore,
        corrections,
        feedback,
        criteriaScores,
      })

      setAttempts(prev => prev + 1)

      if (overallScore >= 85) {
        setConfettiTrigger(prev => prev + 1)
      }
    } catch (error) {
      console.error('Evaluation failed:', error)
    } finally {
      setIsEvaluating(false)
    }
  }, [text, meetsMinWords, data.criteria])

  const handleRetry = useCallback(() => {
    setText(data.template || '')
    setResult(null)
  }, [data.template])

  const copyText = useCallback(() => {
    navigator.clipboard.writeText(text)
  }, [text])

  const downloadText = useCallback(() => {
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'writing-practice.txt'
    a.click()
  }, [text])

  const speakText = useCallback(() => {
    if (isSpeaking) {
      stopSpeaking()
    } else {
      speak(text)
    }
  }, [text, speak, stopSpeaking, isSpeaking])

  // Generate mock corrections
  function generateMockCorrections(userText: string) {
    const corrections = []
    const words = userText.split(/\s+/)

    // Randomly flag some words
    const commonErrors = [
      { pattern: /\b(i|I)\b/g, type: 'grammar', explanation: 'Capitalize "I" when used as a pronoun' },
      { pattern: /\b(am|is|are)\s+go\b/g, type: 'grammar', explanation: 'Use "-ing" form after be verb' },
      { pattern: /\b(to|too|two)\b/g, type: 'grammar', explanation: 'Check usage of to/too/two' },
      { pattern: /\b(their|there|they're)\b/g, type: 'grammar', explanation: 'Check homophones' },
    ]

    let match
    commonErrors.forEach(({ pattern, type, explanation }) => {
      while ((match = pattern.exec(userText)) !== null) {
        if (Math.random() > 0.5) {
          corrections.push({
            original: match[0],
            corrected: match[0].charAt(0).toUpperCase() + match[0].slice(1),
            type,
            explanation,
            position: { start: match.index, end: match.index + match[0].length },
            severity: 'minor' as const,
          })
        }
      }
    })

    return corrections.slice(0, 5)
  }

  function generateFeedback(score: number, correctionCount: number): string {
    if (score >= 95) return 'Outstanding writing! Your text is clear, accurate, and well-structured.'
    if (score >= 85) return 'Excellent work! Minor improvements will make it perfect.'
    if (score >= 75) return 'Good effort! Review the corrections below to improve.'
    if (score >= 65) return 'Keep practicing! Focus on the highlighted areas.'
    return 'Don\'t give up! Writing takes practice. Review the feedback and try again.'
  }

  return (
    <div className="space-y-6">
      {/* Prompt */}
      <Card variant="gradient" className="p-6">
        <div className="mb-4">
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white">
            <PenTool className="w-4 h-4" />
            Writing Practice
          </span>
        </div>

        <h2 className="text-xl font-bold text-white mb-4">{data.prompt}</h2>

        {data.context && (
          <p className="text-white/80 text-sm mb-4">{data.context}</p>
        )}

        {data.examples && data.examples.length > 0 && (
          <div className="mt-4 p-4 bg-white/10 rounded-xl">
            <p className="text-white/90 text-sm font-medium mb-2">Example approaches:</p>
            <ul className="space-y-1 text-white/80 text-sm">
              {data.examples.map((ex, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="w-4 h-4 rounded-full bg-primary-300 flex-shrink-0 mt-1" />
                  <span>{truncate(ex, 100)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {(['write', 'review', 'examples'] as const).map(tab => (
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

      {/* Write Tab */}
      {currentTab === 'write' && (
        <div className="space-y-6 animate-in">
          {/* Word Count & Requirements */}
          <div className="grid sm:grid-cols-3 gap-4">
            <div className={cn('p-4 rounded-xl text-center', meetsMinWords ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200')}>
              <p className="text-2xl font-bold text-gray-900">{wordCount}</p>
              <p className="text-xs text-gray-500">Words</p>
              {data.minWords && (
                <p className="text-xs text-gray-400 mt-1">Min: {data.minWords}</p>
              )}
            </div>
            <div className={cn('p-4 rounded-xl text-center', meetsMaxWords ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200')}>
              <p className="text-2xl font-bold text-gray-900">{charCount}</p>
              <p className="text-xs text-gray-500">Characters</p>
              {data.maxWords && (
                <p className="text-xs text-gray-400 mt-1">Max: {data.maxWords} words</p>
              )}
            </div>
            <div className="p-4 rounded-xl text-center bg-primary-50 border border-primary-200">
              <p className="text-2xl font-bold text-primary-600">{data.criteria.length}</p>
              <p className="text-xs text-gray-500">Criteria</p>
            </div>
          </div>

          {/* Writing Area */}
          <Card className="overflow-hidden">
            <CardContent className="p-0">
              {/* Toolbar */}
              <div className="p-4 border-b border-gray-100 flex flex-wrap gap-2">
                <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                  <Button variant="ghost" size="icon" onClick={() => document.execCommand('bold')}>
                    <Type className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => document.execCommand('italic')}>
                    <Italic className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => document.execCommand('underline')}>
                    <Underline className="w-4 h-4" />
                  </Button>
                </div>
                <div className="w-px h-8 bg-gray-200 mx-2" />
                <Button variant="ghost" size="sm" onClick={copyText} leftIcon={<Copy className="w-4 h-4" />}>
                  Copy
                </Button>
                <Button variant="ghost" size="sm" onClick={downloadText} leftIcon={<Download className="w-4 h-4" />}>
                  Download
                </Button>
                <Button variant="ghost" size="sm" onClick={speakText} leftIcon={isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}>
                  {isSpeaking ? 'Stop' : 'Listen'}
                </Button>
              </div>

              {/* Textarea */}
              <Textarea
                ref={textareaRef}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Start writing your response here..."
                rows={15}
                className="w-full h-[400px] border-none focus:ring-0 p-4 resize-y font-medium text-gray-900"
                spellCheck={true}
              />
            </CardContent>
          </Card>

          {/* Evaluation Criteria */}
          {showCriteria && (
            <Card variant="glass">
              <CardContent className="p-4">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900">Evaluation Criteria</h3>
                  <Button variant="ghost" size="icon" onClick={() => setShowCriteria(!showCriteria)}>
                    <ChevronUp className="w-4 h-4" />
                  </Button>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {data.criteria.map((criterion, index) => (
                    <div key={index} className="p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-900 text-sm">{criterion.name}</span>
                        <span className="text-xs text-primary-600 font-semibold">{Math.round(criterion.weight * 100)}%</span>
                      </div>
                      <p className="text-xs text-gray-500">{criterion.description}</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Submit Button */}
          <Button
            variant="primary"
            className="w-full"
            onClick={handleEvaluate}
            disabled={!text.trim() || !meetsMinWords || isEvaluating}
            size="lg"
            leftIcon={isEvaluating ? <Loader className="w-5 h-5 animate-spin" /> : <Target className="w-5 h-5" />}
          >
            {isEvaluating ? 'Evaluating...' : 'Evaluate Writing'}
          </Button>
        </div>
      )}

      {/* Review Tab */}
      {currentTab === 'review' && result && (
        <div className="space-y-6 animate-in">
          {/* Score Summary */}
          <Card variant={result.score >= 85 ? 'hover' : 'default'} className="p-6 text-center">
            <div className={cn(
              'w-24 h-24 rounded-full mx-auto mb-4 flex items-center justify-center',
              result.score >= 85 ? 'bg-gradient-to-br from-green-500 to-emerald-500' :
              result.score >= 70 ? 'bg-gradient-to-br from-amber-500 to-yellow-500' :
              'bg-gradient-to-br from-red-500 to-pink-500'
            )}>
              <span className="text-3xl font-bold text-white">{result.score}%</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              {result.score >= 95 ? 'Outstanding!' :
              result.score >= 85 ? 'Excellent!' :
              result.score >= 75 ? 'Good Job!' :
              result.score >= 65 ? 'Keep Practicing!' : 'Don\'t Give Up!'}
            </h3>
            <p className="text-gray-600 mb-4">{result.feedback}</p>

            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="p-3 bg-gray-50 rounded-xl">
                <p className="text-lg font-bold text-primary-600">{wordCount}</p>
                <p className="text-xs text-gray-500">Words Written</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl">
                <p className="text-lg font-bold text-red-600">{result.corrections.length}</p>
                <p className="text-xs text-gray-500">Corrections</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-xl">
                <p className="text-lg font-bold text-purple-600">{attempts}</p>
                <p className="text-xs text-gray-500">Attempts</p>
              </div>
            </div>

            <Button
              variant="primary"
              className="w-full"
              onClick={() => onComplete(result.score)}
              rightIcon={<ArrowRight className="w-4 h-4" />}
              size="lg"
            >
              Continue
            </Button>
          </Card>

          {/* Criteria Scores */}
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Criteria Breakdown</h3>
              <div className="space-y-3">
                {data.criteria.map((criterion, index) => {
                  const score = result.criteriaScores[criterion.name] || 0
                  return (
                    <div key={index} className="p-3 bg-gray-50 rounded-xl">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-medium text-gray-900">{criterion.name}</span>
                        <span className={cn(
                          'text-lg font-bold',
                          score >= 80 ? 'text-green-600' :
                          score >= 60 ? 'text-amber-600' : 'text-red-600'
                        )}>
                          {score}%
                        </span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all duration-500',
                            score >= 80 ? 'bg-green-500' :
                            score >= 60 ? 'bg-amber-500' : 'bg-red-500'
                          )}
                          style={{ width: `${score}%` }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>

          {/* Corrections */}
          {result.corrections.length > 0 && (
            <Card>
              <CardContent className="p-6">
                <h3 className="font-semibold text-gray-900 mb-4">Corrections & Suggestions</h3>
                <div className="space-y-3">
                  {result.corrections.map((correction, index) => (
                    <div key={index} className={cn(
                      'p-4 rounded-xl border',
                      correction.severity === 'critical' ? 'border-red-200 bg-red-50' :
                      correction.severity === 'major' ? 'border-amber-200 bg-amber-50' :
                      'border-gray-200 bg-gray-50'
                    )}>
                      <div className="flex items-start gap-3">
                        <div className={cn(
                          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                          correction.severity === 'critical' ? 'bg-red-100 text-red-600' :
                          correction.severity === 'major' ? 'bg-amber-100 text-amber-600' :
                          'bg-gray-100 text-gray-600'
                        )}>
                          {correction.type === 'grammar' && <FileText className="w-4 h-4" />}
                          {correction.type === 'vocabulary' && <BookOpen className="w-4 h-4" />}
                          {correction.type === 'spelling' && <Type className="w-4 h-4" />}
                          {correction.type === 'style' && <Wand2 className="w-4 h-4" />}
                          {correction.type === 'punctuation' && <AlertCircle className="w-4 h-4" />}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-mono text-red-600 line-through">{correction.original}</span>
                            <span className="font-mono text-green-600">{correction.corrected}</span>
                          </div>
                          <p className="text-sm text-gray-600">{correction.explanation}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Examples Tab */}
      {currentTab === 'examples' && (
        <div className="space-y-4 animate-in">
          <Card>
            <CardContent className="p-6">
              <h3 className="font-semibold text-gray-900 mb-4">Writing Models</h3>
              <p className="text-gray-600 mb-4">Study these examples to understand structure and style:</p>
              <div className="space-y-4">
                {data.examples?.map((example, index) => (
                  <Card key={index} variant="hover" className="p-4">
                    <p className="text-gray-700 mb-2">{example}</p>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => setText(example)} leftIcon={<Copy className="w-4 h-4" />}>
                        Use as Template
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => speak(example)} leftIcon={<Volume2 className="w-4 h-4" />}>
                        Listen
                      </Button>
                    </div>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>

          {data.vocabulary && data.vocabulary.length > 0 && (
            <Card variant="glass">
              <CardContent className="p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Useful Vocabulary</h3>
                <div className="flex flex-wrap gap-2">
                  {data.vocabulary.map((vocab, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const cursorPos = textareaRef.current?.selectionStart || 0
                        const before = text.slice(0, cursorPos)
                        const after = text.slice(cursorPos)
                        setText(before + vocab.word + after)
                      }}
                    >
                      <span className="font-medium">{vocab.word}</span>
                      <span className="text-primary-600 ml-1">- {vocab.translation}</span>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Attempts */}
      <div className="text-center text-sm text-gray-500">
        Attempt {attempts + 1} • Every draft makes you a better writer!
      </div>
    </div>
  )
}

// Helper
function truncate(text: string, length: number): string {
  if (text.length <= length) return text
  return text.slice(0, length - 3) + '...'
}

// Import missing icons
import { Italic, ChevronUp, Volume2, VolumeX, Loader } from 'lucide-react'