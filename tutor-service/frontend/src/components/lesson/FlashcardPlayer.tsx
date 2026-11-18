import { useState, useCallback, useEffect } from 'react'
import {
  RotateCcw,
  Volume2,
  ChevronLeft,
  ChevronRight,
  CheckCircle,
  XCircle,
  Sparkles,
  Shuffle,
  Layers,
  Heart,
  Bookmark,
  ArrowRight,
  Trophy,
  Star,
  Target,
  RefreshCw,
  Copy,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface FlashcardPlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function FlashcardPlayer({
  content,
  targetLanguage,
  nativeLanguage,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: FlashcardPlayerProps) {
  const data = content.data as {
    cards: {
      id: string
      front: string
      back: string
      frontAudio?: string
      backAudio?: string
      frontImage?: string
      backImage?: string
      tags?: string[]
      difficulty?: 'easy' | 'medium' | 'hard'
    }[]
    settings?: {
      shuffle?: boolean
      showImages?: boolean
      autoPlayAudio?: boolean
    }
  }

  const [currentIndex, setCurrentIndex] = useState(0)
  const [isFlipped, setIsFlipped] = useState(false)
  const [knownCards, setKnownCards] = useState<string[]>([])
  const [unknownCards, setUnknownCards] = useState<string[]>([])
  const [showResults, setShowResults] = useState(false)
  const [mode, setMode] = useState<'learn' | 'review' | 'test'>('learn')
  const [shuffledIndices, setShuffledIndices] = useState<number[]>([])
  const [cardRotation, setCardRotation] = useState(0)

  const cards = data.cards
  const currentCard = cards[shuffledIndices[currentIndex] || currentIndex]
  const progress = ((knownCards.length + unknownCards.length) / cards.length) * 100

  // Initialize shuffled indices
  useEffect(() => {
    if (data.settings?.shuffle) {
      const indices = Array.from({ length: cards.length }, (_, i) => i)
      // Fisher-Yates shuffle
      for (let i = indices.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1))
        ;[indices[i], indices[j]] = [indices[j], indices[i]]
      }
      setShuffledIndices(indices)
    }
  }, [cards.length, data.settings?.shuffle])

  // Auto-play audio
  useEffect(() => {
    if (data.settings?.autoPlayAudio && currentCard) {
      const audioUrl = isFlipped ? currentCard.backAudio : currentCard.frontAudio
      if (audioUrl) {
        const audio = new Audio(audioUrl)
        audio.play()
      }
    }
  }, [currentIndex, isFlipped, data.settings?.autoPlayAudio, currentCard])

  const handleFlip = useCallback(() => {
    setCardRotation(prev => prev + 180)
    setTimeout(() => setIsFlipped(!isFlipped), 150)
  }, [isFlipped])

  const handleKnown = useCallback(() => {
    const cardId = currentCard.id
    setKnownCards(prev => [...prev, cardId])
    setUnknownCards(prev => prev.filter(id => id !== cardId))

    if (currentIndex < cards.length - 1) {
      setTimeout(() => {
        setCurrentIndex(prev => prev + 1)
        setIsFlipped(false)
        setCardRotation(0)
      }, 300)
    } else {
      setShowResults(true)
    }
  }, [currentIndex, cards.length, currentCard])

  const handleUnknown = useCallback(() => {
    const cardId = currentCard.id
    setUnknownCards(prev => [...prev, cardId])
    setKnownCards(prev => prev.filter(id => id !== cardId))

    if (currentIndex < cards.length - 1) {
      setTimeout(() => {
        setCurrentIndex(prev => prev + 1)
        setIsFlipped(false)
        setCardRotation(0)
      }, 300)
    } else {
      setShowResults(true)
    }
  }, [currentIndex, cards.length, currentCard])

  const handleRetry = useCallback(() => {
    setKnownCards([])
    setUnknownCards([])
    setCurrentIndex(0)
    setIsFlipped(false)
    setShowResults(false)
    setCardRotation(0)
  }, [])

  const handleShuffle = useCallback(() => {
    const indices = Array.from({ length: cards.length }, (_, i) => i)
    for (let i = indices.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[indices[i], indices[j]] = [indices[j], indices[i]]
    }
    setShuffledIndices(indices)
    setCurrentIndex(0)
    setIsFlipped(false)
  }, [cards.length])

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  const playFrontAudio = () => {
    if (currentCard.frontAudio) {
      stopSpeaking()
      const audio = new Audio(currentCard.frontAudio)
      audio.play()
    } else {
      speak(currentCard.front)
    }
  }

  const playBackAudio = () => {
    if (currentCard.backAudio) {
      stopSpeaking()
      const audio = new Audio(currentCard.backAudio)
      audio.play()
    } else {
      speak(currentCard.back)
    }
  }

  if (showResults) {
    return (
      <div className="space-y-6 animate-in">
        <div className="text-center mb-8">
          <div className="w-20 h-20 mx-auto mb-4 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
            <Trophy className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Flashcards Complete!</h2>
          <p className="text-gray-600">Great job reviewing all {cards.length} cards.</p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-8">
          <Card variant="hover" className="p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{knownCards.length}</p>
            <p className="text-sm text-gray-500">Known</p>
          </Card>
          <Card variant="hover" className="p-4 text-center">
            <p className="text-3xl font-bold text-red-600">{unknownCards.length}</p>
            <p className="text-sm text-gray-500">Need Review</p>
          </Card>
          <Card variant="hover" className="p-4 text-center">
            <p className="text-3xl font-bold text-primary-600">{Math.round((knownCards.length / cards.length) * 100)}%</p>
            <p className="text-sm text-gray-500">Mastery</p>
          </Card>
        </div>

        <div className="flex gap-4 justify-center">
          <Button variant="secondary" onClick={handleRetry} leftIcon={<RotateCcw className="w-4 h-4" />}>
            Review Again
          </Button>
          <Button variant="primary" onClick={() => onComplete(Math.round((knownCards.length / cards.length) * 100))} rightIcon={<ArrowRight className="w-4 h-4" />}>
            Continue
          </Button>
        </div>

        {/* Show unknown cards for review */}
        {unknownCards.length > 0 && (
          <div className="mt-8">
            <h3 className="font-semibold text-gray-900 mb-4">Cards to Review</h3>
            <div className="space-y-2">
              {unknownCards.map(cardId => {
                const card = cards.find(c => c.id === cardId)
                if (!card) return null
                return (
                  <Card key={card.id} variant="hover" className="p-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-red-100 text-red-600 flex items-center justify-center">
                        <XCircle className="w-5 h-5" />
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-gray-900">{card.front}</p>
                        <p className="text-gray-600 text-sm">{card.back}</p>
                      </div>
                    </div>
                  </Card>
                )
              })}
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-2">
          <span className="text-gray-600">Card {currentIndex + 1} of {cards.length}</span>
          <span className="font-medium text-gray-900">{Math.round(progress)}% complete</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Mode Selector */}
      <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
        {(['learn', 'review', 'test'] as const).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={cn(
              'flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all',
              mode === m
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            {m.charAt(0).toUpperCase() + m.slice(1)}
          </button>
        ))}
      </div>

      {/* Flashcard */}
      <div className="perspective-1000">
        <div
          className={cn(
            'relative w-full aspect-[4/3] max-w-2xl mx-auto cursor-pointer transform transition-transform duration-300',
            isFlipped ? 'rotate-y-180' : ''
          )}
          onClick={mode === 'learn' ? handleFlip : undefined}
        >
          {/* Front */}
          <div className={cn(
            'absolute inset-0 w-full h-full rounded-2xl backface-hidden shadow-xl flex flex-col items-center justify-center p-8',
            'bg-gradient-to-br from-white to-gray-50 border border-gray-100'
          )}>
            {currentCard.frontImage && (
              <img
                src={currentCard.frontImage}
                alt=""
                className="max-h-40 mb-4 rounded-xl object-cover w-full"
              />
            )}
            <p className="text-2xl lg:text-3xl font-medium text-gray-900 text-center leading-relaxed mb-4">
              {currentCard.front}
            </p>
            {currentCard.tags && currentCard.tags.length > 0 && (
              <div className="flex gap-1 mb-4">
                {currentCard.tags.map((tag, i) => (
                  <span key={i} className="badge text-xs bg-primary-100 text-primary-700">{tag}</span>
                ))}
              </div>
            )}
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" onClick={playFrontAudio} className="text-primary-600">
                <Volume2 className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => copyToClipboard(currentCard.front)}>
                <Copy className="w-5 h-5" />
              </Button>
              <span className="text-sm text-gray-500">Click to flip</span>
            </div>
          </div>

          {/* Back */}
          <div className={cn(
            'absolute inset-0 w-full h-full rounded-2xl backface-hidden shadow-xl flex flex-col items-center justify-center p-8 transform rotate-y-180',
            'bg-gradient-to-br from-primary-50 to-accent-50 border border-primary-100'
          )}>
            {currentCard.backImage && (
              <img
                src={currentCard.backImage}
                alt=""
                className="max-h-40 mb-4 rounded-xl object-cover w-full"
              />
            )}
            <p className="text-2xl lg:text-3xl font-medium text-primary-900 text-center leading-relaxed mb-4">
              {currentCard.back}
            </p>
            <div className="flex items-center gap-4 mb-4">
              <Button variant="ghost" size="icon" onClick={playBackAudio} className="text-primary-600">
                <Volume2 className="w-5 h-5" />
              </Button>
              <Button variant="ghost" size="icon" onClick={() => copyToClipboard(currentCard.back)}>
                <Copy className="w-5 h-5" />
              </Button>
              <span className="text-sm text-primary-600">{targetLanguage}</span>
            </div>

            {/* Known/Unknown Buttons */}
            {mode !== 'test' && (
              <div className="flex gap-4 mt-4">
                <Button
                  variant="secondary"
                  onClick={handleUnknown}
                  leftIcon={<XCircle className="w-4 h-4" />}
                  className="flex-1"
                >
                  Don't Know
                </Button>
                <Button
                  variant="primary"
                  onClick={handleKnown}
                  rightIcon={<CheckCircle className="w-4 h-4" />}
                  className="flex-1"
                >
                  Know It
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setCurrentIndex(prev => Math.max(0, prev - 1))
            setIsFlipped(false)
            setCardRotation(0)
          }}
          disabled={currentIndex === 0}
          leftIcon={<ChevronLeft className="w-4 h-4" />}
        >
          Previous
        </Button>

        <div className="flex items-center gap-4 text-sm text-gray-500">
          <Button variant="ghost" size="icon" onClick={handleShuffle} leftIcon={<Shuffle className="w-4 h-4" />}>
            Shuffle
          </Button>
          <span>✓ {knownCards.length}  ✗ {unknownCards.length}</span>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            setCurrentIndex(prev => Math.min(cards.length - 1, prev + 1))
            setIsFlipped(false)
            setCardRotation(0)
          }}
          disabled={currentIndex >= cards.length - 1}
          rightIcon={<ChevronRight className="w-4 h-4" />}
        >
          Next
        </Button>
      </div>

      {/* Keyboard Shortcuts Hint */}
      <div className="text-center text-xs text-gray-500">
        <kbd className="px-2 py-0.5 bg-gray-100 rounded mx-1">Space</kbd> Flip
        <kbd className="px-2 py-0.5 bg-gray-100 rounded mx-1">→</kbd> Next
        <kbd className="px-2 py-0.5 bg-gray-100 rounded mx-1">←</kbd> Previous
        <kbd className="px-2 py-0.5 bg-gray-100 rounded mx-1">K</kbd> Know
        <kbd className="px-2 py-0.5 bg-gray-100 rounded mx-1">D</kbd> Don't Know
      </div>
    </div>
  )
}