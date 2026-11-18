import { useState, useRef, useEffect, useImperativeHandle, forwardRef } from 'react'
import {
  Send,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Copy,
  Flag,
  ArrowUp,
  ArrowDown,
  Sparkles,
  MessageSquare,
  X,
  CheckCircle,
  XCircle,
  HelpCircle,
  RotateCcw,
  Image,
  Paperclip,
  Smile,
  Settings,
  Languages,
  Globe,
  Trash2,
  Save,
  Share2,
  Download,
  Copy as CopyIcon,
  Mic2,
  Keyboard,
  Bot,
  User,
  Zap,
  Shield,
  Clock,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'
import type { ChatMessage, Correction } from '@/types'

interface ChatInterfaceProps {
  messages: ChatMessage[]
  onSendMessage: (content: string, type?: ChatMessage['type']) => Promise<void>
  onSendVoice: (audioBlob: Blob) => Promise<void>
  targetLanguage: string
  nativeLanguage: string
  tutorState: 'idle' | 'listening' | 'thinking' | 'speaking' | 'waiting'
  isRecording: boolean
  onStartRecording: () => void
  onStopRecording: () => void
  transcript: string
  interimTranscript: string
  confidence: number
  browserSupportsSpeechRecognition: boolean
}

export const ChatInterface = forwardRef<HTMLDivElement, ChatInterfaceProps>(
  (
    {
      messages,
      onSendMessage,
      onSendVoice,
      targetLanguage,
      nativeLanguage,
      tutorState,
      isRecording,
      onStartRecording,
      onStopRecording,
      transcript,
      interimTranscript,
      confidence,
      browserSupportsSpeechRecognition,
    },
    ref
  ) => {
    const [inputValue, setInputValue] = useState('')
    const [showSuggestions, setShowSuggestions] = useState(false)
    const [suggestions, setSuggestions] = useState<string[]>([])
    const [isSending, setIsSending] = useState(false)
    const [recordingBlob, setRecordingBlob] = useState<Blob | null>(null)
    const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null)
    const [showEmojiPicker, setShowEmojiPicker] = useState(false)
    const [messageToCopy, setMessageToCopy] = useState<string | null>(null)
    const [showTranslate, setShowTranslate] = useState<string | null>(null)

    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLTextAreaElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    // Focus management
    useImperativeHandle(ref, () => ({
      focus: () => inputRef.current?.focus(),
    }))

    // Auto-scroll to bottom
    useEffect(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Handle keyboard shortcuts
    useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault()
          handleSend()
        }
        if (e.key === '/' && e.ctrlKey) {
          e.preventDefault()
          inputRef.current?.focus()
        }
      }

      window.addEventListener('keydown', handleKeyDown)
      return () => window.removeEventListener('keydown', handleKeyDown)
    }, [])

    const handleSend = async () => {
      const content = inputValue.trim() || transcript.trim()
      if (!content || isSending) return

      setIsSending(true)
      setInputValue('')
      setShowSuggestions(false)

      try {
        await onSendMessage(content, 'text')
      } catch (error) {
        console.error('Failed to send message:', error)
      } finally {
        setIsSending(false)
      }
    }

    const handleVoiceSend = async () => {
      if (recordingBlob) {
        setIsSending(true)
        try {
          await onSendVoice(recordingBlob)
        } catch (error) {
          console.error('Failed to send voice:', error)
        } finally {
          setIsSending(false)
          setRecordingBlob(null)
        }
      } else if (!isRecording) {
        onStartRecording()
      }
    }

    const handleRecordingComplete = (blob: Blob) => {
      setRecordingBlob(blob)
    }

    const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const value = e.target.value
      setInputValue(value)

      // Auto-grow textarea
      const textarea = e.target
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`

      // Show suggestions when typing
      if (value.length > 2 && value.endsWith(' ')) {
        // In real app, fetch suggestions from API
        setShowSuggestions(true)
        setSuggestions([
          'How do I say...?',
          'Can you explain...?',
          'Give me an example',
          'Practice with me',
          'Correct my grammar',
        ])
      }
    }

    const handleSuggestionClick = (suggestion: string) => {
      setInputValue(suggestion)
      setShowSuggestions(false)
      inputRef.current?.focus()
    }

    const copyMessage = (text: string) => {
      navigator.clipboard.writeText(text)
      setMessageToCopy(text)
      setTimeout(() => setMessageToCopy(null), 2000)
    }

    const formatTime = (dateString: string): string => {
      const date = new Date(dateString)
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }

    const getMessageAvatar = (role: string) => {
      if (role === 'assistant') {
        return (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
        )
      }
      if (role === 'system') {
        return (
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
        )
      }
      return (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
      )
    }

    const renderMessageContent = (message: ChatMessage) => {
      const isUser = message.role === 'user'
      const isAssistant = message.role === 'assistant'
      const isSystem = message.role === 'system'

      return (
        <div className={cn(
          'max-w-[85%]',
          isUser && 'ml-auto',
          isAssistant && 'mr-auto'
        )}>
          <div className={cn(
            'rounded-2xl p-4 animate-in',
            isUser
              ? 'bg-primary-600 text-white rounded-tr-md'
              : isAssistant
              ? 'bg-white text-gray-900 border border-gray-100 rounded-tl-md shadow-sm'
              : 'bg-amber-50 text-amber-900 border border-amber-100 rounded'
          )}>
            {/* Message Type Badge */}
            {message.type !== 'text' && (
              <div className="mb-2 flex items-center gap-1 text-xs">
                <span className={cn(
                  'px-2 py-0.5 rounded-full text-xs font-medium',
                  isUser ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-700'
                )}>
                  {message.type === 'audio' && <Mic2 className="w-3 h-3 mr-1" />}
                  {message.type === 'mixed' && <MessageSquare className="w-3 h-3 mr-1" />}
                  {message.type === 'exercise' && <HelpCircle className="w-3 h-3 mr-1" />}
                  {message.type === 'correction' && <RotateCcw className="w-3 h-3 mr-1" />}
                  {message.type === 'explanation' && <Globe className="w-3 h-3 mr-1" />}
                  {message.type.charAt(0).toUpperCase() + message.type.slice(1)}
                </span>
              </div>
            )}

            {/* Main Content */}
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{message.content}</p>
            </div>

            {/* Audio Player */}
            {message.metadata?.audioUrl && (
              <div className="mt-3">
                <audio controls src={message.metadata.audioUrl} className="w-full" />
              </div>
            )}

            {/* Transcript for audio messages */}
            {message.type === 'audio' && message.metadata?.transcript && (
              <details className="mt-2 group">
                <summary className="text-xs font-medium text-gray-500 cursor-pointer flex items-center gap-1">
                  <ChevronDown className="w-4 h-4 transition-transform group-open:rotate-180" />
                  Show transcript
                </summary>
                <p className="mt-2 text-sm text-gray-600 bg-gray-50 p-3 rounded-lg">
                  {message.metadata.transcript}
                </p>
              </details>
            )}

            {/* Corrections */}
            {message.metadata?.corrections && message.metadata.corrections.length > 0 && (
              <div className="mt-3 space-y-2">
                {message.metadata.corrections.map((correction: Correction, index: number) => (
                  <div
                    key={index}
                    className={cn(
                      'p-3 rounded-xl text-sm',
                      correction.severity === 'critical' ? 'bg-red-50 border border-red-200' :
                      correction.severity === 'major' ? 'bg-amber-50 border border-amber-200' :
                      'bg-gray-50 border border-gray-200'
                    )}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-mono text-red-600 line-through">{correction.original}</span>
                      <span className="font-mono text-green-600">{correction.corrected}</span>
                      <span className={cn(
                        'text-xs px-1.5 py-0.5 rounded',
                        correction.type === 'grammar' ? 'bg-blue-100 text-blue-700' :
                        correction.type === 'vocabulary' ? 'bg-green-100 text-green-700' :
                        correction.type === 'pronunciation' ? 'bg-purple-100 text-purple-700' :
                        correction.type === 'spelling' ? 'bg-red-100 text-red-700' :
                        'bg-gray-100 text-gray-700'
                      )}>
                        {correction.type}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">{correction.explanation}</p>
                  </div>
                ))}
              </div>
            )}

            {/* Confidence indicator for speech recognition */}
            {message.metadata?.confidence !== undefined && (
              <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
                <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                className="h-full bg-primary-500 rounded-full"
                style={{ width: `${(message.metadata.confidence || 0) * 100}%` }}
              />
                </div>
                <span>{Math.round((message.metadata.confidence || 0) * 100)}% confident</span>
              </div>
            )}

            {/* Actions */}
            <div className="mt-3 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {message.role !== 'system' && (
                <>
                  <button
                    onClick={() => copyMessage(message.content)}
                    className="p-1.5 rounded-lg hover:bg-black/10 text-gray-400 hover:text-gray-600 transition-colors"
                    title="Copy"
                  >
                    <CopyIcon className="w-4 h-4" />
                  </button>
                  {message.metadata?.audioUrl && (
                    <button className="p-1.5 rounded-lg hover:bg-black/10 text-gray-400 hover:text-gray-600 transition-colors" title="Replay">
                      <Volume2 className="w-4 h-4" />
                    </button>
                  )}
                  <button className="p-1.5 rounded-lg hover:bg-black/10 text-gray-400 hover:text-gray-600 transition-colors" title="Flag">
                    <Flag className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
          </div>

          <div className={cn('mt-1 text-xs text-gray-400', isUser ? 'text-right' : 'text-left')}>
            {formatTime(message.timestamp)}
            {message.metadata?.duration && (
              <span className="ml-2">{formatTime(message.metadata.duration + '')}</span>
            )}
          </div>
        </div>
      )
    }

    return (
      <div className="flex flex-col h-full">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={messagesEndRef}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 py-12">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center mb-4 mx-auto">
                <MessageSquare className="w-8 h-8 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">Start a conversation</h3>
              <p className="text-sm text-gray-500 max-w-xs">
                Ask me anything about {targetLanguage}, practice speaking, or get help with your lesson!
              </p>
              <div className="mt-4 flex gap-2">
                <Button variant="outline" size="sm" onClick={() => setInputValue('How do I say hello?')}>
                  <Sparkles className="w-4 h-4 mr-1" />
                  Greetings
                </Button>
                <Button variant="outline" size="sm" onClick={() => setInputValue('Practice pronunciation with me')}>
                  <Mic className="w-4 h-4 mr-1" />
                  Pronunciation
                </Button>
                <Button variant="outline" size="sm" onClick={() => setInputValue('Explain this grammar point')}>
                  <BookOpen className="w-4 h-4 mr-1" />
                  Grammar
                </Button>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div key={`${index}-${message.id}`} className="group">
                  <div className="flex items-start gap-3">
                    {!message.role === 'user' && getMessageAvatar(message.role)}
                    <div className="flex-1">
                      {message.role === 'assistant' && (
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-primary-600">AI Tutor</span>
                          <span className="text-xs text-gray-400">·</span>
                          <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
                        </div>
                      )}
                      {renderMessageContent(message)}
                    </div>
                    {message.role === 'user' && getMessageAvatar(message.role)}
                  </div>
                </div>
              ))}

              {/* Typing Indicator */}
              {tutorState === 'thinking' && (
                <div className="flex items-start gap-3 animate-in">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div className="bg-white rounded-2xl border border-gray-100 p-4 shadow-sm">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-primary-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="p-4 border-t border-gray-100 animate-in">
            <p className="text-xs font-medium text-gray-500 mb-2">Suggestions</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  size="sm"
                  onClick={() => handleSuggestionClick(suggestion)}
                  className="text-left"
                >
                  {suggestion}
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Input Area */}
        <div className="p-4 border-t border-gray-100 bg-white/50 backdrop-blur-sm">
          {/* Voice Input Status */}
          {(isRecording || transcript || interimTranscript) && (
            <div className="mb-3 p-3 rounded-xl bg-primary-50 border border-primary-100 animate-in">
              <div className="flex items-center gap-3">
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center',
                  isRecording ? 'bg-red-500 animate-pulse' : 'bg-primary-500'
                )}>
                  {isRecording ? <Mic className="w-5 h-5 text-white" /> : <MicOff className="w-5 h-5 text-white" />}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900">
                      {isRecording ? 'Listening...' : 'Processing...'}
                    </span>
                    {confidence > 0 && (
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <Shield className="w-3 h-3" />
                        {Math.round(confidence * 100)}% confident
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-gray-600 font-mono max-h-16 overflow-auto">
                    {(transcript || '') + (interimTranscript ? `<span className="text-gray-400 italic">${interimTranscript}</span>` : '')}
                  </div>
                </div>
                {!isRecording && transcript && (
                  <Button variant="primary" size="sm" onClick={handleSend}>
                    Send
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Main Input */}
          <div className="relative">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={handleInputChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={`Message AI Tutor... (Ctrl+/ to focus}`}
              rows={1}
              className={cn(
                'w-full px-4 py-3 pr-28 rounded-xl border bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all resize-none',
                'min-h-[52px] max-h-[150px]'
              )}
              style={{ height: '52px' }}
              disabled={isSending}
            />

            {/* Input Actions */}
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowEmojiPicker(!showEmojiPicker)}
                className="text-gray-400 hover:text-primary-600"
              >
                <Smile className="w-5 h-5" />
              </Button>

              <Button
                variant="ghost"
                size="icon"
                onClick={handleVoiceSend}
                className={cn(
                  'text-gray-400 hover:text-primary-600 transition-colors',
                  isRecording ? 'text-red-500 animate-pulse' : ''
                )}
              >
                {isRecording ? <MicOff className="w-5 h-5" /> : <Mic2 className="w-5 h-5" />}
              </Button>

              <Button
                variant="primary"
                size="icon"
                onClick={handleSend}
                disabled={!inputValue.trim() && !transcript.trim() || isSending}
                className="text-white"
              >
                {isSending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
              </Button>
            </div>
          </div>

          {/* Hint */}
          <p className="text-xs text-gray-400 text-center mt-2">
            Press <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Enter</kbd> to send ·
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Shift+Enter</kbd> for new line ·
            <kbd className="px-1.5 py-0.5 bg-gray-100 rounded text-gray-700">Ctrl+/</kbd> to focus
          </p>
        </div>
      </div>
    )
  }
)

ChatInterface.displayName = 'ChatInterface'