import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'
import { useTutorStore } from '@/stores/tutorStore'
import type { ChatMessage, LessonContent, TutorResponse } from '@/types'

interface TutorContextType {
  // Connection state
  isConnected: boolean
  connectionError: string | null

  // Chat
  sendMessage: (content: string, type?: ChatMessage['type'], audioBlob?: Blob) => Promise<void>
  sendVoiceMessage: (audioBlob: Blob) => Promise<void>

  // Lesson interaction
  startLesson: (lessonId: string) => Promise<void>
  completeContent: (contentId: string, score?: number) => Promise<void>
  requestHint: (contentId: string) => Promise<string>
  submitExercise: (contentId: string, answer: string | string[]) => Promise<{ correct: boolean; feedback: string }>

  // Pronunciation
  evaluatePronunciation: (audioBlob: Blob, targetText: string) => Promise<{
    score: number
    feedback: string
    phonemeScores: Array<{ phoneme: string; score: number }>
  }>

  // Writing
  evaluateWriting: (text: string, criteria: string[]) => Promise<{
    score: number
    corrections: Array<{
      original: string
      corrected: string
      type: string
      explanation: string
    }>
    feedback: string
  }>

  // Tutor state
  tutorState: 'idle' | 'listening' | 'thinking' | 'speaking' | 'waiting'
  setTutorState: (state: TutorContextType['tutorState']) => void
}

const TutorContext = createContext<TutorContextType | undefined>(undefined)

export function TutorProvider({ children }: { children: ReactNode }) {
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [tutorState, setTutorState] = useState<TutorContextType['tutorState']>('idle')

  const {
    session,
    setSession,
    updateSession,
    addMessage,
    currentLesson,
    currentContentIndex,
    setCurrentContentIndex,
    completeLesson,
    userProgress,
    updateProgress,
    targetLanguage,
    nativeLanguage,
  } = useTutorStore()

  // Initialize connection
  useEffect(() => {
    const connect = async () => {
      try {
        // In a real app, this would establish WebSocket connection to tutor agent
        await new Promise((resolve) => setTimeout(resolve, 500))
        setIsConnected(true)
        setConnectionError(null)
      } catch (error) {
        setConnectionError('Failed to connect to tutor')
        setIsConnected(false)
      }
    }

    connect()
  }, [])

  const sendMessage = useCallback(
    async (content: string, type: ChatMessage['type'] = 'text', audioBlob?: Blob) => {
      if (!session) return

      const userMessage: ChatMessage = {
        id: `msg-${Date.now()}`,
        role: 'user',
        content,
        type,
        timestamp: new Date().toISOString(),
        metadata: audioBlob
          ? { audioUrl: URL.createObjectURL(audioBlob) }
          : undefined,
      }

      addMessage(userMessage)
      setTutorState('thinking')

      try {
        // In a real app, this would call the tutor agent API
        const response = await callTutorAgent(userMessage, audioBlob)

        const tutorMessage: ChatMessage = {
          id: `msg-${Date.now() + 1}`,
          role: 'assistant',
          content: response.message,
          type: response.message.includes('[AUDIO]') ? 'mixed' : 'text',
          timestamp: new Date().toISOString(),
          metadata: {
            audioUrl: response.audioUrl,
            corrections: response.corrections,
            suggestions: response.suggestions,
          },
        }

        addMessage(tutorMessage)
        setTutorState('speaking')

        // Simulate tutor speaking duration
        await new Promise((resolve) => setTimeout(resolve, 2000))
        setTutorState('waiting')
      } catch (error) {
        console.error('Failed to send message:', error)
        setTutorState('waiting')
      }
    },
    [session, addMessage]
  )

  const sendVoiceMessage = useCallback(
    async (audioBlob: Blob) => {
      // Convert speech to text, then send as message
      // This would use a speech-to-text service
      const transcript = await speechToText(audioBlob)
      await sendMessage(transcript, 'audio', audioBlob)
    },
    [sendMessage]
  )

  const startLesson = useCallback(
    async (lessonId: string) => {
      setTutorState('thinking')

      // Initialize lesson session
      const newSession = {
        sessionId: `session-${Date.now()}`,
        lessonId,
        startTime: new Date().toISOString(),
        messages: [] as ChatMessage[],
        currentExercise: currentLesson?.content[currentContentIndex],
        userInput: '',
        isRecording: false,
        isProcessing: false,
        tutorState: 'listening' as const,
      }

      setSession(newSession)
      setTutorState('listening')

      // Send lesson start message to tutor
      await sendMessage(
        `I'd like to start the lesson: ${currentLesson?.title}. Let's begin!`,
        'text'
      )
    },
    [currentLesson, currentContentIndex, setSession, sendMessage]
  )

  const completeContent = useCallback(
    async (contentId: string, score?: number) => {
      // Update lesson progress
      const nextIndex = currentContentIndex + 1

      if (currentLesson && nextIndex >= currentLesson.content.length) {
        // Lesson complete
        const avgScore = score || 85
        completeLesson(currentLesson.id, avgScore)

        // Update user progress
        if (userProgress) {
          updateProgress({
            totalTimeSpent: userProgress.totalTimeSpent + (currentLesson.duration * 60),
          })
        }

        setCurrentContentIndex(0)
      } else {
        setCurrentContentIndex(nextIndex)
      }
    },
    [currentLesson, currentContentIndex, completeLesson, userProgress, updateProgress, setCurrentContentIndex]
  )

  const requestHint = useCallback(async (contentId: string): Promise<string> => {
    // Request hint from tutor
    const hint = await callTutorAgent({
      id: `hint-${Date.now()}`,
      role: 'user',
      content: `Give me a hint for this exercise: ${contentId}`,
      type: 'text',
      timestamp: new Date().toISOString(),
    })

    return hint.message
  }, [])

  const submitExercise = useCallback(
    async (contentId: string, answer: string | string[]) => {
      const result = await callTutorAgent({
        id: `exercise-${Date.now()}`,
        role: 'user',
        content: `Exercise answer: ${JSON.stringify(answer)}`,
        type: 'exercise',
        timestamp: new Date().toISOString(),
      })

      return {
        correct: result.message.toLowerCase().includes('correct'),
        feedback: result.message,
      }
    },
    []
  )

  const evaluatePronunciation = useCallback(
    async (audioBlob: Blob, targetText: string) => {
      // In real app, this would call pronunciation evaluation API
      await new Promise((resolve) => setTimeout(resolve, 1000))

      // Mock result
      return {
        score: Math.floor(Math.random() * 30) + 70,
        feedback: 'Good pronunciation! Work on the "th" sound.',
        phonemeScores: [
          { phoneme: 'θ', score: 65 },
          { phoneme: 'ð', score: 70 },
          { phoneme: 'r', score: 85 },
        ],
      }
    },
    []
  )

  const evaluateWriting = useCallback(
    async (text: string, criteria: string[]) => {
      await new Promise((resolve) => setTimeout(resolve, 1500))

      return {
        score: Math.floor(Math.random() * 25) + 75,
        corrections: [
          { original: 'I am go to store', corrected: 'I am going to the store', type: 'grammar', explanation: 'Use present continuous for actions happening now' },
        ],
        feedback: 'Good effort! Remember to use articles and correct verb forms.',
      }
    },
    []
  )

  return (
    <TutorContext.Provider
      value={{
        isConnected,
        connectionError,
        sendMessage,
        sendVoiceMessage,
        startLesson,
        completeContent,
        requestHint,
        submitExercise,
        evaluatePronunciation,
        evaluateWriting,
        tutorState,
        setTutorState,
      }}
    >
      {children}
    </TutorContext.Provider>
  )
}

export function useTutor() {
  const context = useContext(TutorContext)
  if (!context) {
    throw new Error('useTutor must be used within a TutorProvider')
  }
  return context
}

// Mock API calls - replace with real API in production
async function callTutorAgent(message: ChatMessage, audioBlob?: Blob): Promise<TutorResponse> {
  await new Promise((resolve) => setTimeout(resolve, 1000 + Math.random() * 1000))

  const responses = [
    "That's a great start! Let me help you with that. In Spanish, you would say '¿Cómo estás?' which means 'How are you?'.",
    "Excellent! You're getting the hang of it. Remember, the verb 'estar' is used for temporary states and locations.",
    "Good try! The correct form is 'estás' (with accent on the á). The accent changes the pronunciation slightly.",
    "Perfect! Now let's practice a dialogue. Imagine you're meeting a friend at a café...",
    "I notice you're having trouble with the rolled 'r'. Let's practice: 'perro' (dog), 'carro' (car), 'ferrocarril' (railroad).",
  ]

  return {
    message: responses[Math.floor(Math.random() * responses.length)],
    suggestions: ['Tell me more', 'Give me an example', 'Practice pronunciation', 'Explain the grammar'],
    audioUrl: undefined,
    corrections: [],
  }
}

async function speechToText(audioBlob: Blob): Promise<string> {
  // In real app, use Web Speech API or send to STT service
  await new Promise((resolve) => setTimeout(resolve, 500))
  return "I'd like to practice Spanish conversation"
}