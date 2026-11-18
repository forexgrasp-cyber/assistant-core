import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import type {
  User,
  Lesson,
  LessonProgress,
  UserProgress,
  ChatMessage,
  SessionState,
  CEFRLevel,
  FocusArea,
  Language,
  Achievement,
} from '@/types'

interface TutorState {
  // User & Auth
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  updateUser: (updates: Partial<User>) => void

  // Current Session
  session: SessionState | null
  setSession: (session: SessionState | null) => void
  updateSession: (updates: Partial<SessionState>) => void
  addMessage: (message: ChatMessage) => void
  clearSession: () => void

  // Lessons & Curriculum
  lessons: Lesson[]
  setLessons: (lessons: Lesson[]) => void
  currentLesson: Lesson | null
  setCurrentLesson: (lesson: Lesson | null) => void
  currentContentIndex: number
  setCurrentContentIndex: (index: number) => void
  nextContent: () => void
  prevContent: () => void

  // Progress
  userProgress: UserProgress | null
  setUserProgress: (progress: UserProgress | null) => void
  updateProgress: (updates: Partial<UserProgress>) => void
  lessonProgress: Record<string, LessonProgress>
  updateLessonProgress: (lessonId: string, progress: Partial<LessonProgress>) => void
  completeLesson: (lessonId: string, score: number) => void

  // Achievements
  achievements: Achievement[]
  setAchievements: (achievements: Achievement[]) => void
  unlockAchievement: (achievementId: string) => void

  // UI State
  view: 'dashboard' | 'curriculum' | 'lesson' | 'practice' | 'progress' | 'settings' | 'generator'
  setView: (view: TutorState['view']) => void
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void

  // Settings
  targetLanguage: string
  setTargetLanguage: (lang: string) => void
  nativeLanguage: string
  setNativeLanguage: (lang: string) => void
  cefrLevel: CEFRLevel
  setCefrLevel: (level: CEFRLevel) => void
  dailyGoalMinutes: number
  setDailyGoalMinutes: (minutes: number) => void
  autoPlayAudio: boolean
  setAutoPlayAudio: (enabled: boolean) => void
  showTranslations: boolean
  setShowTranslations: (enabled: boolean) => void
  enableHaptics: boolean
  setEnableHaptics: (enabled: boolean) => void

  // Audio/Voice
  isRecording: boolean
  setIsRecording: (recording: boolean) => void
  isTutorSpeaking: boolean
  setIsTutorSpeaking: (speaking: boolean) => void
  playbackSpeed: number
  setPlaybackSpeed: (speed: number) => void

  // Practice Mode
  practiceMode: 'conversation' | 'pronunciation' | 'vocabulary' | 'grammar' | 'writing' | 'listening'
  setPracticeMode: (mode: TutorState['practiceMode']) => void
  practiceHistory: ChatMessage[]
  addToPracticeHistory: (message: ChatMessage) => void
}

const defaultUserProgress: UserProgress = {
  userId: '',
  language: 'en',
  currentLevel: 'A1',
  xp: 0,
  levelProgress: 0,
  streak: 0,
  longestStreak: 0,
  totalTimeSpent: 0,
  lessonsCompleted: 0,
  lessonsMastered: 0,
  focusAreaProgress: {
    conversation: 0,
    grammar: 0,
    vocabulary: 0,
    pronunciation: 0,
    writing: 0,
    reading: 0,
    listening: 0,
    culture: 0,
  },
  weakAreas: [],
  strongAreas: [],
  achievements: [],
  dailyGoal: {
    targetMinutes: 15,
    completedMinutes: 0,
    streak: 0,
    lastCompleted: null,
  },
  weeklyStats: {
    weekStart: new Date().toISOString(),
    minutes: 0,
    lessons: 0,
    xp: 0,
    streakDays: 0,
  },
}

export const useTutorStore = create<TutorState>()(
  persist(
    (set, get) => ({
      // User & Auth
      user: null,
      isAuthenticated: false,
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),

      // Session
      session: null,
      setSession: (session) => set({ session }),
      updateSession: (updates) =>
        set((state) => ({
          session: state.session ? { ...state.session, ...updates } : null,
        })),
      addMessage: (message) =>
        set((state) => ({
          session: state.session
            ? { ...state.session, messages: [...state.session.messages, message] }
            : null,
        })),
      clearSession: () => set({ session: null }),

      // Lessons
      lessons: [],
      setLessons: (lessons) => set({ lessons }),
      currentLesson: null,
      setCurrentLesson: (lesson) => set({ currentLesson: lesson, currentContentIndex: 0 }),
      currentContentIndex: 0,
      setCurrentContentIndex: (index) => set({ currentContentIndex: index }),
      nextContent: () =>
        set((state) => ({
          currentContentIndex: Math.min(
            state.currentContentIndex + 1,
            state.currentLesson?.content.length - 1 || 0
          ),
        })),
      prevContent: () =>
        set((state) => ({
          currentContentIndex: Math.max(state.currentContentIndex - 1, 0),
        })),

      // Progress
      userProgress: defaultUserProgress,
      setUserProgress: (progress) => set({ userProgress: progress }),
      updateProgress: (updates) =>
        set((state) => ({
          userProgress: state.userProgress ? { ...state.userProgress, ...updates } : null,
        })),
      lessonProgress: {},
      updateLessonProgress: (lessonId, progress) =>
        set((state) => ({
          lessonProgress: {
            ...state.lessonProgress,
            [lessonId]: { ...state.lessonProgress[lessonId], ...progress },
          },
        })),
      completeLesson: (lessonId, score) =>
        set((state) => {
          const lesson = state.lessons.find((l) => l.id === lessonId)
          if (!lesson) return state

          const newXP = (state.userProgress?.xp || 0) + lesson.xpReward
          const { level, progress } = getLevelFromXP(newXP)

          return {
            userProgress: state.userProgress
              ? {
                  ...state.userProgress,
                  xp: newXP,
                  levelProgress: progress,
                  lessonsCompleted: state.userProgress.lessonsCompleted + 1,
                  lessonsMastered:
                    score >= 90
                      ? state.userProgress.lessonsMastered + 1
                      : state.userProgress.lessonsMastered,
                  dailyGoal: {
                    ...state.userProgress.dailyGoal,
                    completedMinutes:
                      state.userProgress.dailyGoal.completedMinutes + lesson.duration,
                  },
                }
              : null,
            lessonProgress: {
              ...state.lessonProgress,
              [lessonId]: {
                lessonId,
                userId: state.user?.id || '',
                status: score >= 80 ? 'mastered' : 'completed',
                currentContentIndex: lesson.content.length,
                completedContent: lesson.content.map((c) => c.id),
                score,
                attempts: (state.lessonProgress[lessonId]?.attempts || 0) + 1,
                timeSpent: lesson.duration * 60,
                lastAccessed: new Date().toISOString(),
                masteryLevel: score,
              },
            },
          }
        }),

      // Achievements
      achievements: [],
      setAchievements: (achievements) => set({ achievements }),
      unlockAchievement: (achievementId) =>
        set((state) => ({
          achievements: state.achievements.map((a) =>
            a.id === achievementId ? { ...a, unlockedAt: new Date().toISOString() } : a
          ),
        })),

      // UI State
      view: 'dashboard',
      setView: (view) => set({ view }),
      sidebarOpen: true,
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      // Settings
      targetLanguage: 'es',
      setTargetLanguage: (lang) => set({ targetLanguage: lang }),
      nativeLanguage: 'en',
      setNativeLanguage: (lang) => set({ nativeLanguage: lang }),
      cefrLevel: 'A1',
      setCefrLevel: (level) => set({ cefrLevel: level }),
      dailyGoalMinutes: 15,
      setDailyGoalMinutes: (minutes) => set({ dailyGoalMinutes: minutes }),
      autoPlayAudio: true,
      setAutoPlayAudio: (enabled) => set({ autoPlayAudio: enabled }),
      showTranslations: true,
      setShowTranslations: (enabled) => set({ showTranslations: enabled }),
      enableHaptics: true,
      setEnableHaptics: (enabled) => set({ enableHaptics: enabled }),

      // Audio
      isRecording: false,
      setIsRecording: (recording) => set({ isRecording: recording }),
      isTutorSpeaking: false,
      setIsTutorSpeaking: (speaking) => set({ isTutorSpeaking: speaking }),
      playbackSpeed: 1,
      setPlaybackSpeed: (speed) => set({ playbackSpeed: speed }),

      // Practice Mode
      practiceMode: 'conversation',
      setPracticeMode: (mode) => set({ practiceMode: mode }),
      practiceHistory: [],
      addToPracticeHistory: (message) =>
        set((state) => ({
          practiceHistory: [...state.practiceHistory.slice(-49), message], // Keep last 50
        })),
    }),
    {
      name: 'tutor-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        targetLanguage: state.targetLanguage,
        nativeLanguage: state.nativeLanguage,
        cefrLevel: state.cefrLevel,
        dailyGoalMinutes: state.dailyGoalMinutes,
        autoPlayAudio: state.autoPlayAudio,
        showTranslations: state.showTranslations,
        enableHaptics: state.enableHaptics,
        playbackSpeed: state.playbackSpeed,
        userProgress: state.userProgress,
        lessonProgress: state.lessonProgress,
        achievements: state.achievements,
        practiceMode: state.practiceMode,
      }),
    }
  )
)

// Helper function for XP calculation (moved from utils to avoid circular deps)
function getLevelFromXP(xp: number): { level: number; progress: number; nextLevelXP: number } {
  let level = 1
  let totalXP = 0
  let nextLevelXP = 100

  while (totalXP + nextLevelXP <= xp) {
    totalXP += nextLevelXP
    level++
    nextLevelXP = level * level * 100
  }

  const progress = ((xp - totalXP) / nextLevelXP) * 100
  return { level, progress: Math.min(100, Math.max(0, progress)), nextLevelXP }
}