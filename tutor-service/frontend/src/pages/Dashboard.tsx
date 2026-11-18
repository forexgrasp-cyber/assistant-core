import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpen,
  Mic,
  BarChart,
  Target,
  Flame,
  Award,
  ArrowRight,
  Clock,
  Zap,
  Trophy,
  TrendingUp,
  Calendar,
  MessageSquare,
  Headphones,
  PenTool,
  Globe,
  Crown,
  Sparkles,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useTutorStore } from '@/stores/tutorStore'
import { useAuth } from '@/contexts/AuthContext'
import { cn, formatDuration, formatXP, getLevelFromXP, getCEFRGradient } from '@/lib/utils'
import type { Lesson, FocusArea } from '@/types'

// Mock data - replace with API calls
const mockLessons: Lesson[] = [
  {
    id: 'lesson-1',
    title: 'Greetings & Introductions',
    description: 'Learn essential greetings, farewells, and how to introduce yourself in Spanish.',
    language: 'es',
    level: 'A1',
    focusArea: 'conversation',
    duration: 15,
    xpReward: 50,
    content: [],
    tags: ['basics', 'greetings', 'conversation'],
    order: 1,
  },
  {
    id: 'lesson-2',
    title: 'Numbers 1-100',
    description: 'Master Spanish numbers from 1 to 100 with pronunciation practice.',
    language: 'es',
    level: 'A1',
    focusArea: 'vocabulary',
    duration: 20,
    xpReward: 75,
    content: [],
    tags: ['numbers', 'pronunciation', 'vocabulary'],
    order: 2,
  },
  {
    id: 'lesson-3',
    title: 'Present Tense -AR Verbs',
    description: 'Conjugate and use regular -AR verbs in the present tense.',
    language: 'es',
    level: 'A1',
    focusArea: 'grammar',
    duration: 25,
    xpReward: 100,
    content: [],
    tags: ['grammar', 'verbs', 'conjugation'],
    order: 3,
  },
  {
    id: 'lesson-4',
    title: 'Ordering at a Restaurant',
    description: 'Practice real-world dialogue for ordering food and drinks.',
    language: 'es',
    level: 'A2',
    focusArea: 'conversation',
    duration: 20,
    xpReward: 80,
    content: [],
    tags: ['food', 'restaurant', 'practical'],
    order: 4,
  },
  {
    id: 'lesson-5',
    title: 'Spanish Pronunciation: Vowels',
    description: 'Perfect your Spanish vowel sounds with native speaker examples.',
    language: 'es',
    level: 'A1',
    focusArea: 'pronunciation',
    duration: 15,
    xpReward: 50,
    content: [],
    tags: ['pronunciation', 'vowels', 'basics'],
    order: 5,
  },
  {
    id: 'lesson-6',
    title: 'Writing: Self Introduction',
    description: 'Learn to write a formal and informal self-introduction in Spanish.',
    language: 'es',
    level: 'A1',
    focusArea: 'writing',
    duration: 20,
    xpReward: 75,
    content: [],
    tags: ['writing', 'formal', 'informal'],
    order: 6,
  },
]

const focusAreas: { value: FocusArea; label: string; icon: React.ComponentType<{ className?: string }>; color: string }[] = [
  { value: 'conversation', label: 'Conversation', icon: MessageSquare, color: 'bg-blue-500' },
  { value: 'grammar', label: 'Grammar', icon: BookOpen, color: 'bg-green-500' },
  { value: 'vocabulary', label: 'Vocabulary', icon: PenTool, color: 'bg-purple-500' },
  { value: 'pronunciation', label: 'Pronunciation', icon: Mic, color: 'bg-orange-500' },
  { value: 'writing', label: 'Writing', icon: PenTool, color: 'bg-pink-500' },
  { value: 'reading', label: 'Reading', icon: BookOpen, color: 'bg-indigo-500' },
  { value: 'listening', label: 'Listening', icon: Headphones, color: 'bg-teal-500' },
  { value: 'culture', label: 'Culture', icon: Globe, color: 'bg-amber-500' },
]

const achievements = [
  { id: 'first-lesson', title: 'First Steps', description: 'Complete your first lesson', icon: Sparkles, unlocked: true, category: 'lessons' as const },
  { id: 'week-streak', title: 'Week Warrior', description: 'Maintain a 7-day streak', icon: Flame, unlocked: true, category: 'streak' as const },
  { id: 'level-a2', title: 'Elementary Achiever', description: 'Reach A2 level', icon: Trophy, unlocked: false, progress: 65, target: 100, category: 'mastery' as const },
  { id: 'pronunciation-pro', title: 'Pronunciation Pro', description: 'Score 90%+ on 10 pronunciation exercises', icon: Mic, unlocked: false, progress: 3, target: 10, category: 'special' as const },
  { id: 'conversation-master', title: 'Conversation Master', description: 'Complete 50 conversation lessons', icon: MessageSquare, unlocked: false, progress: 12, target: 50, category: 'lessons' as const },
  { id: 'xp-10k', title: 'XP Collector', description: 'Earn 10,000 total XP', icon: Zap, unlocked: false, progress: 1250, target: 10000, category: 'xp' as const },
]

export function Dashboard() {
  const { user, userProgress, lessonProgress, lessons: userLessons, setLessons, targetLanguage, nativeLanguage, streak, xp } = useTutorStore()
  const { user: authUser } = useAuth()
  const [currentLessonIndex, setCurrentLessonIndex] = useState(0)
  const [showAllLessons, setShowAllLessons] = useState(false)

  // Initialize lessons on mount
  useEffect(() => {
    if (userLessons.length === 0) {
      setLessons(mockLessons)
    }
  }, [userLessons.length, setLessons])

  // Calculate stats
  const completedLessons = Object.values(lessonProgress).filter(p => p.status === 'completed' || p.status === 'mastered').length
  const masteredLessons = Object.values(lessonProgress).filter(p => p.status === 'mastered').length
  const totalTimeSpent = userProgress?.totalTimeSpent || 0
  const { level, progress: levelProgress, nextLevelXP } = getLevelFromXP(xp)

  // Get next recommended lesson
  const nextLesson = mockLessons.find(l => {
    const prog = lessonProgress[l.id]
    return !prog || prog.status === 'not_started'
  })

  const inProgressLesson = mockLessons.find(l => {
    const prog = lessonProgress[l.id]
    return prog?.status === 'in_progress'
  })

  return (
    <div className="space-y-6 animate-in">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className={`absolute inset-0 bg-gradient-to-br ${getCEFRGradient(userProgress?.currentLevel || 'A1')} opacity-10`} />
        <div className="relative p-6 lg:p-8 rounded-3xl bg-white shadow-xl border border-gray-100">
          <div className="grid lg:grid-cols-3 gap-6 items-center">
            {/* User Profile & Streak */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-2xl font-bold text-white">
                  {authUser?.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div>
                  <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">
                    Welcome back, {authUser?.name || 'Learner'}! 👋
                  </h1>
                  <p className="text-gray-600 mt-1">
                    Ready to continue your {nativeLanguage} → {targetLanguage} journey?
                  </p>
                </div>
              </div>

              {/* Streak & Level */}
              <div className="flex flex-wrap items-center gap-4 mt-4">
                <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 rounded-xl border border-amber-100">
                  <Flame className="w-5 h-5 text-amber-500" />
                  <span className="font-bold text-amber-700 text-lg">{streak}</span>
                  <span className="text-amber-600">day streak</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl text-white">
                  <Crown className="w-5 h-5" />
                  <span className="font-semibold">Level {level}</span>
                  <span className="px-2 py-0.5 bg-white/20 rounded-full text-xs">{userProgress?.currentLevel || 'A1'}</span>
                </div>
                <div className="flex items-center gap-2 px-4 py-2 bg-green-50 rounded-xl border border-green-100">
                  <Zap className="w-5 h-5 text-green-500" />
                  <span className="font-bold text-green-700">{formatXP(xp)}</span>
                  <span className="text-green-600">XP</span>
                </div>
              </div>

              {/* Level Progress Bar */}
              <div className="max-w-md">
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-600">Progress to Level {level + 1}</span>
                  <span className="font-semibold text-gray-900">{Math.round(levelProgress)}%</span>
                </div>
                <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-700"
                    style={{ width: `${levelProgress}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Quick Stats Cards */}
            <div className="grid grid-cols-2 gap-4">
              <StatCard icon={BookOpen} value={completedLessons} label="Lessons Done" color="blue" />
              <StatCard icon={Trophy} value={masteredLessons} label="Mastered" color="amber" />
              <StatCard icon={Clock} value={formatDuration(totalTimeSpent / 60)} label="Time Spent" color="green" />
              <StatCard icon={TrendingUp} value={`${userProgress?.weeklyStats?.streakDays || 0}/7`} label="This Week" color="purple" />
            </div>
          </div>
        </div>
      </section>

      {/* Continue Learning / Start Next Lesson */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Continue Learning</h2>
          <Link to="/curriculum" className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center gap-1">
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {(inProgressLesson || nextLesson) ? (
          <div className="grid lg:grid-cols-2 gap-4">
            {inProgressLesson && (
              <ContinueLessonCard
                lesson={inProgressLesson}
                progress={lessonProgress[inProgressLesson.id]}
              />
            )}
            {nextLesson && !inProgressLesson && (
              <NextLessonCard lesson={nextLesson} />
            )}
            {nextLesson && inProgressLesson && (
              <NextLessonCard lesson={nextLesson} />
            )}
          </div>
        ) : (
          <Card variant="gradient" className="text-center py-12">
            <Trophy className="w-16 h-16 mx-auto text-primary-500/80 mb-4" />
            <h3 className="text-xl font-bold text-gray-900 mb-2">All caught up!</h3>
            <p className="text-gray-600 mb-4">You've completed all available lessons. Check back soon for new content!</p>
            <Link to="/practice">
              <Button variant="primary" leftIcon={<Mic />}>
                Practice Instead
              </Button>
            </Link>
          </Card>
        )}
      </section>

      {/* Focus Areas Progress */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Skill Progress</h2>
          <Link to="/progress" className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center gap-1">
            Details <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
          {focusAreas.map((area) => {
            const areaProgress = userProgress?.focusAreaProgress?.[area.value] || 0
            return (
              <FocusAreaCard
                key={area.value}
                area={area}
                progress={areaProgress}
              />
            )
          })}
        </div>
      </section>

      {/* Achievements */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Achievements</h2>
          <Link to="/progress?tab=achievements" className="text-primary-600 hover:text-primary-700 text-sm font-medium flex items-center gap-1">
            View all <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {achievements.slice(0, 6).map((achievement) => (
            <AchievementCard key={achievement.id} achievement={achievement} />
          ))}
        </div>
      </section>

      {/* Weekly Activity */}
      <section className="space-y-4">
        <h2 className="text-xl font-bold text-gray-900">This Week</h2>
        <WeeklyActivityChart />
      </section>
    </div>
  )
}

// Stat Card Component
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

// Continue Lesson Card
function ContinueLessonCard({ lesson, progress }: { lesson: Lesson; progress?: any }) {
  const currentContent = lesson.content[progress?.currentContentIndex || 0]
  const completionPercent = progress?.masteryLevel || 0

  return (
    <Card variant="hover" className="relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 to-accent-500/5" />
      <CardContent className="p-6 relative">
        <div className="flex items-start justify-between mb-4">
          <div>
            <span className="badge-primary text-sm mb-2 block w-fit">In Progress</span>
            <h3 className="text-lg font-bold text-gray-900">{lesson.title}</h3>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold gradient-text">{completionPercent}%</p>
            <p className="text-xs text-gray-500">Complete</p>
          </div>
        </div>

        <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-500"
            style={{ width: `${completionPercent}%` }}
          />
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {formatDuration(lesson.duration)}
          </span>
          <span className="flex items-center gap-1 text-primary-600 font-medium">
            <Zap className="w-4 h-4" />
            +{lesson.xpReward} XP
          </span>
        </div>

        <Button variant="primary" className="w-full" leftIcon={<ArrowRight />}>
          {currentContent ? `Continue: ${currentContent.title}` : 'Continue Lesson'}
        </Button>
      </CardContent>
    </Card>
  )
}

// Next Lesson Card
function NextLessonCard({ lesson }: { lesson: Lesson }) {
  return (
    <Card variant="hover">
      <CardContent className="p-6">
        <div className="mb-4">
          <span className="badge text-sm mb-2 block w-fit bg-primary-100 text-primary-700">Up Next</span>
          <h3 className="text-lg font-bold text-gray-900">{lesson.title}</h3>
          <p className="text-gray-600 text-sm mt-1 line-clamp-2">{lesson.description}</p>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            {formatDuration(lesson.duration)}
          </span>
          <span className="flex items-center gap-1 text-primary-600 font-medium">
            <Zap className="w-4 h-4" />
            +{lesson.xpReward} XP
          </span>
          <span className="badge text-xs bg-gray-100 text-gray-600">{lesson.focusArea}</span>
        </div>

        <Button variant="outline" className="w-full" leftIcon={<ArrowRight />}>
          Start Lesson
        </Button>
      </CardContent>
    </Card>
  )
}

// Focus Area Card
function FocusAreaCard({ area, progress }: { area: typeof focusAreas[0]; progress: number }) {
  return (
    <Card variant="hover" className="p-4 text-center">
      <div className={`w-10 h-10 rounded-xl ${area.color} flex items-center justify-center mx-auto mb-3`}>
        <area.icon className="w-5 h-5 text-white" />
      </div>
      <h4 className="font-medium text-gray-900 text-sm">{area.label}</h4>
      <div className="mt-3">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, background: `linear-gradient(90deg, ${area.color.replace('bg-', '')} 0%, ${area.color.replace('bg-', '').replace('500', '400')} 100%)` }}
          />
        </div>
        <p className="text-xs font-semibold text-gray-900 mt-1">{progress}%</p>
      </div>
    </Card>
  )
}

// Achievement Card
function AchievementCard({ achievement }: { achievement: typeof achievements[0] }) {
  const Icon = achievement.icon
  const isUnlocked = achievement.unlocked

  return (
    <Card variant={isUnlocked ? 'hover' : 'default'} className={!isUnlocked ? 'opacity-60 grayscale' : ''}>
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className={cn(
            'w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0',
            isUnlocked ? 'bg-gradient-to-br from-amber-500 to-orange-500' : 'bg-gray-200'
          )}>
            <Icon className={cn('w-7 h-7', isUnlocked ? 'text-white' : 'text-gray-400')} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className={cn('font-semibold text-gray-900', !isUnlocked && 'text-gray-500')}>
              {achievement.title}
              {!isUnlocked && <Crown className="w-4 h-4 ml-2 text-amber-500" />}
            </h4>
            <p className={cn('text-sm text-gray-600 mt-1', !isUnlocked && 'text-gray-400')}>
              {achievement.description}
            </p>
            {achievement.progress && !isUnlocked && (
              <div className="mt-3">
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-500">Progress</span>
                  <span className="font-medium text-gray-900">{achievement.progress}/{achievement.target}</span>
                </div>
                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                    style={{ width: `${(achievement.progress / achievement.target) * 100}%` }}
                  />
                </div>
              </div>
            )}
            {isUnlocked && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-2 font-medium">
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"/></svg>
                Unlocked
              </span>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Weekly Activity Chart
function WeeklyActivityChart() {
  const days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const data = [15, 20, 0, 30, 15, 45, 20] // minutes per day
  const maxValue = Math.max(...data)

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-end justify-around h-48 gap-2 px-2">
          {days.map((day, index) => (
            <div key={day} className="flex-1 flex flex-col items-center gap-2 max-w-[60px]">
              <div
                className="w-full bg-gradient-to-t from-primary-500 to-accent-500 rounded-t-lg transition-all duration-500"
                style={{
                  height: `${(data[index] / maxValue) * 100}%`,
                  minHeight: data[index] > 0 ? '4px' : 0,
                }}
              />
              <span className="text-xs font-medium text-gray-900">{data[index]}m</span>
              <span className="text-xs text-gray-500">{day}</span>
            </div>
          ))}
        </div>
        <div className="flex justify-center gap-6 mt-4 text-sm">
          <span className="flex items-center gap-1 text-gray-600">
            <span className="w-3 h-3 rounded-full bg-primary-500" />
            This week
          </span>
          <span className="flex items-center gap-1 text-gray-600">
            <span className="w-3 h-3 rounded-full bg-gray-200" />
            Average: 21 min/day
          </span>
        </div>
      </CardContent>
    </Card>
  )
}