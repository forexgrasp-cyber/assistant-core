import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  SkipBack,
  SkipForward,
  Maximize2,
  Minimize2,
  RotateCcw,
  Globe,
  Subtitles,
  Sparkles,
  CheckCircle,
  Settings,
  Turtle as SlowMo,
  FastForward,
} from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Card, CardContent } from '@/components/ui/Card'
import { cn } from '@/lib/utils'
import type { LessonContent } from '@/types'

interface VideoPlayerProps {
  content: LessonContent
  targetLanguage: string
  nativeLanguage: string
  playbackSpeed: number
  onComplete: (score?: number) => void
  speak: (text: string) => void
  stopSpeaking: () => void
  isSpeaking: boolean
}

export function VideoPlayer({
  content,
  targetLanguage,
  nativeLanguage,
  playbackSpeed,
  onComplete,
  speak,
  stopSpeaking,
  isSpeaking,
}: VideoPlayerProps) {
  const data = content.data as {
    url: string
    title: string
    duration: number
    subtitles?: { start: number; end: number; text: string; translation?: string }[]
    transcript?: string
    chapters?: { time: number; title: string }[]
    poster?: string
  }

  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(data.duration)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [showSubtitles, setShowSubtitles] = useState(true)
  const [subtitleLanguage, setSubtitleLanguage] = useState<'target' | 'native' | 'both'>('target')
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [currentSubtitle, setCurrentSubtitle] = useState<string>('')
  const [currentTranslation, setCurrentTranslation] = useState<string>('')
  const [completed, setCompleted] = useState(false)
  const [watchProgress, setWatchProgress] = useState(0)

  const videoRef = useRef<HTMLVideoElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Initialize video
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = playbackSpeed
      videoRef.current.volume = volume
    }
  }, [playbackSpeed, volume])

  // Time update
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime)
      setWatchProgress((video.currentTime / video.duration) * 100)

      // Update subtitles
      if (data.subtitles && showSubtitles) {
        const sub = data.subtitles.find(s => video.currentTime >= s.start && video.currentTime <= s.end)
        setCurrentSubtitle(sub?.text || '')
        setCurrentTranslation(sub?.translation || '')
      }

      // Auto-complete at 95%
      if (video.currentTime / video.duration >= 0.95 && !completed) {
        setCompleted(true)
        onComplete(90)
      }
    }

    const handleEnded = () => {
      setIsPlaying(false)
      if (!completed) {
        setCompleted(true)
        onComplete(90)
      }
    }

    video.addEventListener('timeupdate', handleTimeUpdate)
    video.addEventListener('ended', handleEnded)
    video.addEventListener('loadedmetadata', () => setDuration(video.duration))

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
      video.removeEventListener('ended', handleEnded)
    }
  }, [data.subtitles, showSubtitles, completed, onComplete])

  // Fullscreen handling
  const toggleFullscreen = useCallback(async () => {
    if (!containerRef.current) return

    try {
      if (!isFullscreen) {
        await containerRef.current.requestFullscreen()
        setIsFullscreen(true)
      } else {
        await document.exitFullscreen()
        setIsFullscreen(false)
      }
    } catch (error) {
      console.error('Fullscreen error:', error)
    }
  }, [isFullscreen])

  const togglePlayPause = useCallback(() => {
    const video = videoRef.current
    if (!video) return

    if (isPlaying) {
      video.pause()
      setIsPlaying(false)
    } else {
      video.play()
      setIsPlaying(true)
    }
  }, [isPlaying])

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current
    if (video) {
      video.currentTime = Number(e.target.value)
      setCurrentTime(Number(e.target.value))
    }
  }, [])

  const skipTime = useCallback((seconds: number) => {
    const video = videoRef.current
    if (video) {
      video.currentTime = Math.max(0, Math.min(video.duration, video.currentTime + seconds))
    }
  }, [])

  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const video = videoRef.current
    const newVolume = Number(e.target.value)
    setVolume(newVolume)
    setIsMuted(newVolume === 0)
    if (video) video.volume = newVolume
  }, [])

  const toggleMute = useCallback(() => {
    const video = videoRef.current
    if (video) {
      video.muted = !isMuted
      setIsMuted(!isMuted)
      setVolume(isMuted ? volume : 0)
    }
  }, [isMuted, volume])

  const handleSpeedChange = useCallback((speed: number) => {
    const video = videoRef.current
    if (video) {
      video.playbackRate = speed
    }
  }, [])

  const formatTime = (seconds: number): string => {
    if (isNaN(seconds)) return '0:00'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-4">
      {/* Video Player */}
      <div
        ref={containerRef}
        className={cn(
          'relative rounded-2xl overflow-hidden bg-black',
          isFullscreen ? 'fixed inset-0 z-50 max-w-none max-h-none rounded-none' : ''
        )}
      >
        <video
          ref={videoRef}
          src={data.url}
          poster={data.poster}
          className="w-full h-auto"
          playsInline
          onClick={togglePlayPause}
        />

        {/* Subtitles Overlay */}
        {showSubtitles && currentSubtitle && (
          <div className="absolute bottom-20 left-4 right-4 z-10 animate-in">
            <div className="max-w-4xl mx-auto">
              <p className="text-white text-lg text-center px-4 py-2 bg-black/80 rounded-lg backdrop-blur-sm">
                {currentSubtitle}
              </p>
              {subtitleLanguage !== 'target' && currentTranslation && (
                <p className="text-primary-200 text-sm text-center px-4 py-1 bg-black/60 rounded-lg backdrop-blur-sm mt-1">
                  {currentTranslation}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Play/Pause Overlay */}
        {!isPlaying && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-sm z-10">
            <Button
              variant="primary"
              size="lg"
              onClick={togglePlayPause}
              className="bg-white/90 text-black hover:bg-white"
            >
              <Play className="w-8 h-8 ml-1" />
            </Button>
          </div>
        )}

        {/* Loading */}
        {isPlaying && (
          <div className="absolute inset-0 flex items-center justify-center z-10 pointer-events-none">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-white border-t-transparent" />
          </div>
        )}

        {/* Controls Bar - Bottom */}
        <div className={cn(
          'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4',
          isFullscreen ? 'hidden' : ''
        )}>
          <div className="max-w-4xl mx-auto">
            {/* Progress Bar */}
            <div className="mb-3">
              <input
                type="range"
                min={0}
                max={duration || 100}
                value={currentTime}
                onChange={handleSeek}
                className="w-full h-1 bg-white/30 rounded-full appearance-none cursor-pointer accent-white"
              />
              <div className="flex justify-between text-xs text-white/70 mt-1">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* Main Controls */}
            <div className="flex items-center justify-between gap-4">
              {/* Left Controls */}
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" onClick={() => skipTime(-10)} leftIcon={<SkipBack className="w-5 h-5" />} />
                <Button variant="ghost" size="icon" onClick={togglePlayPause} leftIcon={isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5" />} />
                <Button variant="ghost" size="icon" onClick={() => skipTime(10)} rightIcon={<SkipForward className="w-5 h-5" />} />
              </div>

              {/* Volume */}
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" onClick={toggleMute} leftIcon={isMuted || volume === 0 ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />} />
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.1}
                  value={volume}
                  onChange={handleVolumeChange}
                  className="w-20 h-1 bg-white/30 rounded-full appearance-none cursor-pointer accent-white"
                />
              </div>

              {/* Right Controls */}
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setShowSubtitles(!showSubtitles)}
                  leftIcon={<Subtitles className="w-5 h-5" />}
                  className={showSubtitles ? 'text-primary-400' : 'text-white/70'}
                />
                {data.subtitles && (
                  <select
                    value={subtitleLanguage}
                    onChange={(e) => setSubtitleLanguage(e.target.value as 'target' | 'native' | 'both')}
                    className="px-2 py-1 bg-white/20 rounded text-white text-xs"
                  >
                    <option value="target">Target Only</option>
                    <option value="native">Native Only</option>
                    <option value="both">Both</option>
                  </select>
                )}

                <div className="relative">
                  <Button variant="ghost" size="icon" onClick={() => setShowSettings(!showSettings)} leftIcon={<Settings className="w-5 h-5" />} />
                  {showSettings && (
                    <div className="absolute bottom-full right-0 mb-2 p-3 bg-black/90 rounded-xl text-white min-w-[180px] animate-in">
                      <div className="space-y-3">
                        <div>
                          <p className="text-xs text-white/60 mb-2">Playback Speed</p>
                          <div className="flex gap-1">
                            {[0.5, 0.75, 1, 1.25, 1.5, 2].map(speed => (
                              <button
                                key={speed}
                                onClick={() => handleSpeedChange(speed)}
                                className={cn(
                                  'px-2 py-1 text-xs rounded text-white transition-colors',
                                  playbackSpeed === speed ? 'bg-primary-500' : 'bg-white/20 hover:bg-white/30'
                                )}
                              >
                                {speed}x
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleFullscreen}
                  leftIcon={isFullscreen ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Fullscreen Controls */}
        {isFullscreen && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 to-transparent p-4">
            <div className="max-w-4xl mx-auto">
              <div className="mb-3">
                <input
                  type="range"
                  min={0}
                  max={duration || 100}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-2 bg-white/30 rounded-full appearance-none cursor-pointer accent-white"
                />
              </div>
              <div className="flex items-center justify-center gap-6">
                <Button variant="ghost" size="icon" onClick={() => skipTime(-10)} leftIcon={<SkipBack className="w-6 h-6" />} />
                <Button variant="primary" size="lg" onClick={togglePlayPause} leftIcon={isPlaying ? <Pause className="w-8 h-8" /> : <Play className="w-8 h-8 ml-1" />} className="bg-white text-black" />
                <Button variant="ghost" size="icon" onClick={() => skipTime(10)} rightIcon={<SkipForward className="w-6 h-6" />} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Transcript */}
      {data.transcript && (
        <Card variant="glass">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold text-gray-900">Full Transcript</h3>
              <Button variant="ghost" size="sm" onClick={() => speak(data.transcript!)} leftIcon={<Volume2 className="w-4 h-4" />}>
                Listen
              </Button>
            </div>
            <div className="prose prose-sm max-h-64 overflow-y-auto">
              <p className="text-gray-700">{data.transcript}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chapters */}
      {data.chapters && data.chapters.length > 0 && (
        <Card variant="glass">
          <CardContent className="p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Chapters</h3>
            <div className="space-y-2">
              {data.chapters.map((chapter, index) => (
                <Button
                  key={index}
                  variant="ghost"
                  className="w-full justify-start text-left"
                  onClick={() => {
                    if (videoRef.current) {
                      videoRef.current.currentTime = chapter.time
                    }
                  }}
                >
                  <span className="text-sm text-gray-500 w-12 text-right mr-3">{formatTime(chapter.time)}</span>
                  <span className="text-gray-900 font-medium">{chapter.title}</span>
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Completion */}
      {completed && (
        <div className="p-6 bg-gradient-to-r from-green-50 to-emerald-50 rounded-2xl border border-green-100 text-center animate-in">
          <CheckCircle className="w-12 h-12 mx-auto text-green-500 mb-3" />
          <h3 className="text-lg font-bold text-green-800 mb-1">Video Complete!</h3>
          <p className="text-green-600">Great job watching the entire video.</p>
        </div>
      )}

      {/* Watch Progress */}
      <div className="mb-4">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-gray-600">Watch Progress</span>
          <span className="font-medium text-gray-900">{Math.round(watchProgress)}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-300"
            style={{ width: `${watchProgress}%` }}
          />
        </div>
      </div>
    </div>
  )
}

export default VideoPlayer