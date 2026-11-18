import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Trophy,
  Target,
  BarChart,
  TrendingUp,
  Calendar,
  Clock,
  Zap,
  Flame,
  Crown,
  BookOpen,
  Mic,
  PenTool,
  Headphones,
  Globe,
  Layers,
  CheckCircle,
  Star,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  Download,
  Share2,
  Print,
  Mail,
  Copy,
  Settings,
  Sparkles,
  Medal,
  Award,
  Flag,
  Heart,
  Bookmark,
  RotateCcw,
  RefreshCw,
  Maximize2,
  Minimize2,
  BarChart2,
  LineChart,
  PieChart,
  Activity,
  DollarSign,
  Users,
  Globe as GlobeIcon,
  Shield,
  Clock as ClockIcon,
  Star as StarIcon,
  Trophy as TrophyIcon,
  Medal as MedalIcon,
  Award as AwardIcon,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { useTutorStore } from '@/stores/tutorStore'
import { cn, formatDuration, formatXP, getLevelFromXP, getCEFRColor, getCEFRGradient } from '@/lib/utils'
import confetti from 'canvas-confetti'
import type { CEFRLevel, FocusArea } from '@/types'

export function Progress() {
  const { user, userProgress, lessonProgress, lessons, targetLanguage, nativeLanguage, streak, xp, achievements } = useTutorStore()
  const [activeTab, setActiveTab] = useState<'overview' | 'skills' | 'achievements' | 'activity' | 'reports'>('overview')
  const [dateRange, setDateRange] = useState<'week' | 'month' | 'quarter' | 'year' | 'all'>('month')
  const [showExportModal, setShowExportModal] = useState(false)
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'pdf' | 'html'>('json')
  const [confettiTrigger, setConfettiTrigger] = useState(0)

  // Confetti for milestones
  useState(() => {
    if (confettiTrigger > 0) {
      confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#0ea5e9', '#d946ef', '#10b981', '#f59e0b'],
      })
    }
  }, [confettiTrigger])

  // Calculate stats
  const totalLessons = lessons.length
  const completedLessons = Object.values(lessonProgress).filter(p => p.status === 'completed' || p.status === 'mastered').length
  const masteredLessons = Object.values(lessonProgress).filter(p => p.status === 'mastered').length
  const inProgressLessons = Object.values(lessonProgress).filter(p => p.status === 'in_progress').length
  const totalTimeSpent = userProgress?.totalTimeSpent || 0
  const currentLevel = userProgress?.currentLevel || 'A1'
  const { level, progress: levelProgress, nextLevelXP } = getLevelFromXP(xp)
  const xpToNextLevel = nextLevelXP - (xp - (level - 1) * (level - 1) * 100)

  // Weekly data (mock)
  const weeklyData = [
    { day: 'Mon', minutes: 25, lessons: 2, xp: 180 },
    { day: 'Tue', minutes: 20, lessons: 1, xp: 120 },
    { day: 'Wed', minutes: 30, lessons: 3, xp: 250 },
    { day: 'Thu', minutes: 15, lessons: 1, xp: 80 },
    { day: 'Fri', minutes: 45, lessons: 4, xp: 380 },
    { day: 'Sat', minutes: 35, lessons: 2, xp: 220 },
    { day: 'Sun', minutes: 40, lessons: 3, xp: 300 },
  ]

  // Monthly data (mock)
  const monthlyData = [
    { week: 'Week 1', minutes: 120, lessons: 8, xp: 850 },
    { week: 'Week 2', minutes: 165, lessons: 12, xp: 1200 },
    { week: 'Week 3', minutes: 95, lessons: 6, xp: 680 },
    { week: 'Week 4', minutes: 180, lessons: 14, xp: 1450 },
  ]

  // Focus area progress
  const focusAreas: { key: FocusArea; label: string; icon: React.ComponentType<{ className?: string }>; color: string }[] = [
    { key: 'conversation', label: 'Conversation', icon: MessageSquare, color: 'bg-blue-500' },
    { key: 'grammar', label: 'Grammar', icon: BookOpen, color: 'bg-green-500' },
    { key: 'vocabulary', label: 'Vocabulary', icon: PenTool, color: 'bg-purple-500' },
    { key: 'pronunciation', label: 'Pronunciation', icon: Mic, color: 'bg-orange-500' },
    { key: 'writing', label: 'Writing', icon: PenTool, color: 'bg-pink-500' },
    { key: 'reading', label: 'Reading', icon: BookOpen, color: 'bg-indigo-500' },
    { key: 'listening', label: 'Listening', icon: Headphones, color: 'bg-teal-500' },
    { key: 'culture', label: 'Culture', icon: GlobeIcon, color: 'bg-amber-500' },
  ]

  // Achievements
  const allAchievements = [
    { id: 'first-lesson', title: 'First Steps', description: 'Complete your first lesson', icon: Sparkles, category: 'lessons' as const, unlocked: true, unlockedAt: '2026-01-15', xpReward: 50 },
    { id: 'week-streak', title: 'Week Warrior', description: 'Maintain a 7-day streak', icon: Flame, category: 'streak' as const, unlocked: true, unlockedAt: '2026-01-22', xpReward: 100 },
    { id: 'month-streak', title: 'Monthly Master', description: 'Maintain a 30-day streak', icon: Crown, category: 'streak' as const, unlocked: false, progress: 15, target: 30, xpReward: 500 },
    { id: 'level-a2', title: 'Elementary Achiever', description: 'Reach A2 level', icon: Trophy, category: 'mastery' as const, unlocked: false, progress: 65, target: 100, xpReward: 200 },
    { id: 'level-b1', title: 'Intermediate Speaker', description: 'Reach B1 level', icon: Medal, category: 'mastery' as const, unlocked: false, progress: 0, target: 100, xpReward: 500 },
    { id: 'pronunciation-pro', title: 'Pronunciation Pro', description: 'Score 90%+ on 10 pronunciation exercises', icon: Mic, category: 'special' as const, unlocked: false, progress: 3, target: 10, xpReward: 300 },
    { id: 'conversation-master', title: 'Conversation Master', description: 'Complete 50 conversation lessons', icon: MessageSquare, category: 'lessons' as const, unlocked: false, progress: 12, target: 50, xpReward: 400 },
    { id: 'vocabulary-virtuoso', title: 'Vocabulary Virtuoso', description: 'Learn 500 words', icon: BookOpen, category: 'mastery' as const, unlocked: false, progress: 245, target: 500, xpReward: 300 },
    { id: 'grammar-guru', title: 'Grammar Guru', description: 'Master all A1-A2 grammar points', icon: BookOpen, category: 'mastery' as const, unlocked: false, progress: 60, target: 100, xpReward: 400 },
    { id: 'xp-10k', title: 'XP Collector', description: 'Earn 10,000 total XP', icon: Zap, category: 'xp' as const, unlocked: false, progress: 1250, target: 10000, xpReward: 100 },
    { id: 'perfect-week', title: 'Perfect Week', description: 'Practice every day for a week with 80%+ average', icon: Target, category: 'special' as const, unlocked: false, progress: 5, target: 7, xpReward: 300 },
    { id: 'polyglot-dream', title: 'Polyglot Dream', description: 'Reach B2 in 2 languages', icon: GlobeIcon, category: 'special' as const, unlocked: false, progress: 1, target: 2, xpReward: 1000 },
  ]

  const unlockedAchievements = allAchievements.filter(a => a.unlocked).length
  const totalAchievements = allAchievements.length

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">Progress</h1>
          <p className="text-gray-600 mt-1">
            Track your {nativeLanguage} → {targetLanguage} learning journey
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setShowExportModal(true)} leftIcon={<Download className="w-4 h-4" />}>
            Export Report
          </Button>
          <Button variant="ghost" size="sm" leftIcon={<Share2 className="w-4 h-4" />}>
            Share Progress
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 p-1 bg-gray-100 rounded-xl">
        {(['overview', 'skills', 'achievements', 'activity', 'reports'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab
                ? 'bg-white text-primary-600 shadow-sm'
                : 'text-gray-600 hover:text-gray-900'
            )}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Level & XP Card */}
          <Card className="relative overflow-hidden">
            <div className={`absolute inset-0 bg-gradient-to-br ${getCEFRGradient(currentLevel)} opacity-10`} />
            <CardContent className="p-6 lg:p-8 relative">
              <div className="grid lg:grid-cols-3 gap-8 items-center">
                {/* Level Display */}
                <div className="lg:col-span-2 space-y-4">
                  <div className="flex items-center gap-4">
                    <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                      <span className="text-3xl font-bold text-white">{currentLevel}</span>
                    </div>
                    <div>
                      <h2 className="text-2xl lg:text-3xl font-bold text-gray-900">
                        {user?.name || 'Learner'}
                      </h2>
                      <p className="text-gray-600">
                        {nativeLanguage} → {targetLanguage} • Level {level}
                      </p>
                    </div>
                  </div>

                  {/* XP Progress */}
                  <div className="max-w-xl">
                    <div className="flex justify-between text-sm mb-2">
                      <span className="text-gray-600">Progress to Level {level + 1}</span>
                      <span className="font-semibold text-gray-900">{formatXP(xp)} / {formatXP(xp + xpToNextLevel)} XP</span>
                    </div>
                    <div className="h-4 bg-gray-200 rounded-full overflow-hidden mb-2">
                      <div
                        className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-700"
                        style={{ width: `${levelProgress}%` }}
                      />
                    </div>
                    <div className="flex justify-between text-xs text-gray-500">
                      <span>Level {level} (0 XP)</span>
                      <span>Level {level + 1} ({formatXP(xp + xpToNextLevel)} XP)</span>
                    </div>
                  </div>

                  {/* Milestone */}
                  {levelProgress >= 100 && (
                    <div className="p-4 bg-gradient-to-r from-green-50 to-emerald-50 rounded-xl border border-green-100 animate-in">
                      <div className="flex items-center gap-3">
                        <Trophy className="w-8 h-8 text-green-500" />
                        <div>
                          <p className="font-semibold text-green-800">Level Up Available!</p>
                          <p className="text-sm text-green-700">You've earned enough XP to reach Level {level + 1}</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Quick Stats */}
                <div className="space-y-4">
                  <StatItem icon={BookOpen} value={completedLessons} label="Lessons Completed" color="blue" />
                  <StatItem icon={Star} value={masteredLessons} label="Lessons Mastered" color="amber" />
                  <StatItem icon={Clock} value={formatDuration(totalTimeSpent / 60)} label="Total Time" color="green" />
                  <StatItem icon={Zap} value={formatXP(xp)} label="Total XP" color="purple" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Streak & Activity */}
          <div className="grid lg:grid-cols-2 gap-6">
            {/* Streak Card */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Flame className="w-5 h-5 text-amber-500" />
                  Learning Streak
                </CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="text-center mb-6">
                  <div className="w-32 h-32 mx-auto mb-4 relative">
                    <svg className="w-full h-full transform -rotate-90">
                      <circle
                        cx="64"
                        cy="64"
                        r="50"
                        fill="none"
                        stroke="#e5e7eb"
                        strokeWidth="8"
                      />
                      <circle
                        cx="64"
                        cy="64"
                        r="50"
                        fill="none"
                        stroke="url(#streak-gradient)"
                        strokeWidth="8"
                        strokeLinecap="round"
                        strokeDasharray={314}
                        strokeDashoffset={314 * (1 - Math.min(streak / 30, 1))}
                      />
                      <defs>
                        <linearGradient id="streak-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#fbbf24" />
                          <stop offset="100%" stopColor="#f59e0b" />
                        </linearGradient>
                      </defs>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-4xl font-bold text-gray-900">{streak}</span>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-gray-900">Day Streak</p>
                  <p className="text-gray-500">Keep it going!</p>
                </div>

                <div className="grid grid-cols-3 gap-4 text-center">
                  <div className="p-3 bg-gray-50 rounded-xl">
                    <p className="text-xl font-bold text-gray-900">{streak}</p>
                    <p className="text-xs text-gray-500">Current</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-xl">
                    <p className="text-xl font-bold text-amber-600">{userProgress?.longestStreak || 0}</p>
                    <p className="text-xs text-gray-500">Longest</p>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-xl">
                    <p className="text-xl font-bold text-primary-600">{userProgress?.dailyGoal?.targetMinutes || 15}</p>
                    <p className="text-xs text-gray-500">Daily Goal</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* This Week */}
            <Card>
              <CardHeader className="flex items-center justify-between">
                <CardTitle>This Week's Activity</CardTitle>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value as any)}
                  className="text-sm px-3 py-1.5 rounded-lg border border-gray-200"
                >
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                  <option value="year">This Year</option>
                </select>
              </CardHeader>
              <CardContent className="p-6">
                <ActivityChart data={dateRange === 'week' ? weeklyData : monthlyData} />
              </CardContent>
            </Card>
          </div>

          {/* Focus Areas */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Skill Progress</span>
                <Button variant="ghost" size="sm" leftIcon={<Target className="w-4 h-4" />}>
                  Practice Weak Areas
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3">
                {focusAreas.map((area) => {
                  const areaProgress = userProgress?.focusAreaProgress?.[area.key] || 0
                  const isWeak = userProgress?.weakAreas?.includes(area.key)
                  const isStrong = userProgress?.strongAreas?.includes(area.key)

                  return (
                    <FocusAreaProgressCard
                      key={area.key}
                      area={area}
                      progress={areaProgress}
                      isWeak={isWeak}
                      isStrong={isStrong}
                    />
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Skills Tab */}
      {activeTab === 'skills' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Skill Radar */}
            <Card>
              <CardHeader>
                <CardTitle>Skill Profile</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <SkillRadarChart areas={focusAreas.map(f => ({
                  name: f.label,
                  value: userProgress?.focusAreaProgress?.[f.key] || 0,
                }))} />
              </CardContent>
            </Card>

            {/* Weak & Strong Areas */}
            <Card>
              <CardHeader>
                <CardTitle>Areas to Focus</CardTitle>
              </CardHeader>
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-red-700 mb-3 flex items-center gap-2">
                      <ArrowUpRight className="w-4 h-4" />
                      Weak Areas
                    </h4>
                    {userProgress?.weakAreas?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {userProgress.weakAreas.map(area => {
                          const focusArea = focusAreas.find(f => f.key === area)
                          const Icon = focusArea?.icon
                          return (
                            <Button
                              key={area}
                              variant="outline"
                              size="sm"
                              onClick={() => {}}
                              className="border-red-200 text-red-700 hover:bg-red-50"
                              leftIcon={Icon ? <Icon className="w-4 h-4" /> : undefined}
                            >
                              {focusArea?.label}
                            </Button>
                          )
                        })}
                      </div>
                    ) : (
                      <p className="text-green-600">No weak areas identified yet!</p>
                    )}
                  </div>

                  <div>
                    <h4 className="font-medium text-green-700 mb-3 flex items-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Strong Areas
                    </h4>
                    {userProgress?.strongAreas?.length ? (
                      <div className="flex flex-wrap gap-2">
                        {userProgress.strongAreas.map(area => {
                          const focusArea = focusAreas.find(f => f.key === area)
                          const Icon = focusArea?.icon
                          return (
                            <Button
                              key={area}
                              variant="outline"
                              size="sm"
                              className="border-green-200 text-green-700 hover:bg-green-50"
                              leftIcon={Icon ? <Icon className="w-4 h-4" /> : undefined}
                            >
                              {focusArea?.label}
                            </Button>
                          )
                        })}
                      </div>
                    ) : (
                      <p className="text-gray-500">Complete more lessons to identify strengths.</p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Detailed Skill Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Detailed Skill Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <div className="space-y-4">
                {focusAreas.map((area) => {
                  const progress = userProgress?.focusAreaProgress?.[area.key] || 0
                  return (
                    <SkillDetailRow
                      key={area.key}
                      area={area}
                      progress={progress}
                    />
                  )
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Achievements Tab */}
      {activeTab === 'achievements' && (
        <div className="space-y-6">
          {/* Summary */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <StatCard icon={Trophy} value={unlockedAchievements} label="Unlocked" color="amber" />
            <StatCard icon={Flag} value={totalAchievements} label="Total" color="blue" />
            <StatCard icon={Zap} value={allAchievements.filter(a => a.unlocked).reduce((sum, a) => sum + (a.xpReward || 0), 0)} label="Achievement XP" color="purple" />
            <StatCard icon={Target} value={`${Math.round((unlockedAchievements / totalAchievements) * 100)}%`} label="Completion" color="green" />
          </div>

          {/* Achievements Grid */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {allAchievements.map((achievement) => (
              <AchievementDetailCard
                key={achievement.id}
                achievement={achievement}
              />
            ))}
          </div>
        </div>
      )}

      {/* Activity Tab */}
      {activeTab === 'activity' && (
        <div className="space-y-6">
          {/* Calendar Heatmap */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Activity Calendar</span>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value as any)}
                  className="text-sm px-3 py-1.5 rounded-lg border border-gray-200"
                >
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                  <option value="quarter">This Quarter</option>
                  <option value="year">This Year</option>
                </select>
              </CardTitle>
            </CardHeader>
              <CardContent className="p-6">
                <ActivityCalendar />
              </CardContent>
            </Card>

            {/* Session History */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Sessions</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <SessionHistoryTable />
              </CardContent>
            </Card>
          </div>
      )}

      {/* Reports Tab */}
      {activeTab === 'reports' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Progress Reports</span>
                <Button variant="primary" size="sm" leftIcon={<Download className="w-4 h-4" />} onClick={() => setShowExportModal(true)}>
                  Generate Report
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6">
              <ReportGenerator />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Export Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <Card className="w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">Export Progress Report</h2>
              <Button variant="ghost" size="icon" onClick={() => setShowExportModal(false)}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Format</label>
                <div className="grid grid-cols-2 gap-2">
                  {(['json', 'csv', 'pdf', 'html'] as const).map(format => (
                    <button
                      key={format}
                      onClick={() => setExportFormat(format)}
                      className={cn(
                        'p-4 rounded-xl border-2 text-center transition-all',
                        exportFormat === format
                          ? 'border-primary-500 bg-primary-50'
                          : 'border-gray-200 hover:border-primary-300'
                      )}
                    >
                      <p className="font-semibold text-gray-900 capitalize">{format.toUpperCase()}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {format === 'json' && 'Raw data for developers'}
                        {format === 'csv' && 'Spreadsheet compatible'}
                        {format === 'pdf' && 'Professional report'}
                        {format === 'html' && 'Web-friendly format'}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Date Range</label>
                <select
                  value={dateRange}
                  onChange={(e) => setDateRange(e.target.value as any)}
                  className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <option value="week">Last Week</option>
                  <option value="month">Last Month</option>
                  <option value="quarter">Last Quarter</option>
                  <option value="year">Last Year</option>
                  <option value="all">All Time</option>
                </select>
              </div>

              <div className="flex gap-3">
                <Button variant="secondary" className="flex-1" onClick={() => setShowExportModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" className="flex-1" onClick={() => { generateReport(); setShowExportModal(false); }}>
                  Generate & Download
                </Button>
              </div>
            </div>
          </Card>
        </div>
      )}
    </div>
  )
}

// Helper Components
function StatItem({ icon: Icon, value, label, color }: { icon: React.ComponentType<{ className?: string }>; value: string | number; label: string; color: string }) {
  const colors = {
    blue: 'bg-blue-50 border-blue-100 text-blue-600',
    green: 'bg-green-50 border-green-100 text-green-600',
    amber: 'bg-amber-50 border-amber-100 text-amber-600',
    purple: 'bg-purple-50 border-purple-100 text-purple-600',
  }

  return (
    <div className={`p-4 rounded-xl border ${colors[color as keyof typeof colors] || colors.blue}`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xl font-bold text-gray-900">{value}</p>
          <p className="text-xs text-gray-500">{label}</p>
        </div>
        <Icon className="w-6 h-6 opacity-50" />
      </div>
    </div>
  )
}

function FocusAreaProgressCard({ area, progress, isWeak, isStrong }: { area: any; progress: number; isWeak: boolean; isStrong: boolean }) {
  const Icon = area.icon
  return (
    <div className={cn(
      'p-4 rounded-xl text-center transition-all',
      isWeak ? 'bg-red-50 border border-red-200' :
      isStrong ? 'bg-green-50 border border-green-200' :
      'bg-gray-50 border border-gray-100'
    )}>
      <div className={cn('w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3', `${area.color}`)}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <h4 className="font-medium text-gray-900 text-sm">{area.label}</h4>
      <div className="mt-2">
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-1">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, backgroundColor: area.color.replace('bg-', '').replace('500', '') }}
          />
        </div>
        <p className="text-sm font-semibold text-gray-900">{progress}%</p>
      </div>
      {isWeak && <span className="inline-flex items-center gap-1 text-xs text-red-600 mt-1"><ArrowUpRight className="w-3 h-3" /> Focus needed</span>}
      {isStrong && <span className="inline-flex items-center gap-1 text-xs text-green-600 mt-1"><CheckCircle className="w-3 h-3" /> Strong area</span>}
    </div>
  )
}

function SkillDetailRow({ area, progress }: { area: any; progress: number }) {
  const Icon = area.icon
  return (
    <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl">
      <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', `${area.color}`)}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1">
        <div className="flex justify-between text-sm mb-1">
          <span className="font-medium text-gray-900">{area.label}</span>
          <span className="font-bold text-gray-900">{progress}%</span>
        </div>
        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${progress}%`, backgroundColor: area.color.replace('bg-', '').replace('500', '') }}
          />
        </div>
      </div>
    </div>
  )
}

function ActivityChart({ data }: { data: any[] }) {
  const maxValue = Math.max(...data.map(d => d.minutes))
  return (
    <div className="h-64 flex items-end justify-around gap-2 px-2">
      {data.map((item, index) => (
        <div key={index} className="flex-1 flex flex-col items-center gap-2 max-w-[80px]">
          <div className="relative w-full">
            <div
              className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-primary-500 to-accent-500 rounded-t-lg transition-all duration-500"
              style={{ height: `${(item.minutes / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gray-900">{item.minutes}m</span>
          <span className="text-xs text-gray-500">{item.day || item.week}</span>
        </div>
      ))}
    </div>
  )
}

function SkillRadarChart({ areas }: { areas: { name: string; value: number }[] }) {
  // Simplified radar chart using bars
  return (
    <div className="space-y-3">
      {areas.map((area, index) => (
        <div key={index}>
          <div className="flex justify-between text-sm mb-1">
            <span className="font-medium text-gray-900">{area.name}</span>
            <span className="font-bold text-primary-600">{area.value}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
              style={{ width: `${area.value}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

function ActivityCalendar() {
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const weeks = 4
  const cellsPerWeek = 7

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-gray-500 mb-2">
        {days.map(d => <div key={d}>{d}</div>)}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: weeks * cellsPerWeek }, (_, i) => {
          const hasActivity = i > 5 && i < 23 // Mock pattern
          const intensity = hasActivity ? Math.floor(Math.random() * 4) + 1 : 0
          return (
            <div
              key={i}
              className={cn(
                'aspect-square rounded transition-colors',
                intensity === 0 && 'bg-gray-100',
                intensity === 1 && 'bg-green-200',
                intensity === 2 && 'bg-green-400',
                intensity === 3 && 'bg-green-600',
                intensity === 4 && 'bg-green-800'
              )}
              title={hasActivity ? `${intensity * 15} minutes` : 'No activity'}
            />
          )
        })}
      </div>
      <div className="flex justify-center gap-4 text-xs text-gray-500 mt-2">
        <span className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-gray-100" /> Less</span>
        <span className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-green-200" /></span>
        <span className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-green-400" /></span>
        <span className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-green-600" /></span>
        <span className="flex items-center gap-1"><span className="w-4 h-4 rounded bg-green-800" /> More</span>
      </div>
    </div>
  )
}

function SessionHistoryTable() {
  const sessions = [
    { date: '2026-01-15', lesson: 'Greetings & Introductions', duration: '15 min', xp: 50, status: 'completed', score: 92 },
    { date: '2026-01-14', lesson: 'Numbers 1-100', duration: '20 min', xp: 75, status: 'mastered', score: 95 },
    { date: '2026-01-13', lesson: 'Present -AR Verbs', duration: '25 min', xp: 100, status: 'completed', score: 88 },
    { date: '2026-01-12', lesson: 'Restaurant Dialogue', duration: '20 min', xp: 80, status: 'completed', score: 90 },
    { date: '2026-01-11', lesson: 'Spanish Vowels', duration: '15 min', xp: 50, status: 'mastered', score: 85 },
  ]

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="bg-gray-50 text-left text-sm font-medium text-gray-700">
            <th className="p-4">Date</th>
            <th className="p-4">Lesson</th>
            <th className="p-4">Duration</th>
            <th className="p-4">XP</th>
            <th className="p-4">Status</th>
            <th className="p-4">Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {sessions.map((session, index) => (
            <tr key={index} className="hover:bg-gray-50 transition-colors">
              <td className="p-4 text-sm text-gray-900">{session.date}</td>
              <td className="p-4 text-sm text-gray-900 font-medium">{session.lesson}</td>
              <td className="p-4 text-sm text-gray-600">{session.duration}</td>
              <td className="p-4 text-sm text-primary-600 font-semibold">+{session.xp}</td>
              <td className="p-4">
                <span className={cn(
                  'inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium',
                  session.status === 'mastered' ? 'bg-amber-100 text-amber-700' :
                  'bg-green-100 text-green-700'
                )}>
                  {session.status === 'mastered' && <Star className="w-3 h-3" />}
                  {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                </span>
              </td>
              <td className="p-4 text-sm font-medium text-gray-900">{session.score}%</td>
            </tr>
          ))}
        </tbody>
        </table>
    </div>
  )
}

function ReportGenerator() {
  return (
    <div className="space-y-6">
      <p className="text-gray-600">Generate comprehensive progress reports for sharing with teachers, parents, or for your own records.</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <ReportTypeCard
          title="Weekly Summary"
          description="One-page overview of this week's progress"
          icon={<Calendar className="w-6 h-6" />}
          formats={['PDF', 'HTML']}
        />
        <ReportTypeCard
          title="Monthly Deep Dive"
          description="Detailed analysis with skill breakdowns"
          icon={<BarChart2 className="w-6 h-6" />}
          formats={['PDF', 'HTML', 'CSV']}
        />
        <ReportTypeCard
          title="Full History Export"
          description="Complete learning data for portability"
          icon={<Download className="w-6 h-6" />}
          formats={['JSON', 'CSV']}
        />
      </div>

      <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
        <h4 className="font-medium text-gray-900 mb-2">Scheduled Reports</h4>
        <div className="space-y-2 text-sm text-gray-600">
          <div className="flex justify-between">
            <span>Weekly Progress Email</span>
            <span className="text-green-600 font-medium">Active • Every Monday</span>
          </div>
          <div className="flex justify-between">
            <span>Monthly Summary PDF</span>
            <span className="text-green-600 font-medium">Active • 1st of month</span>
          </div>
        </div>
      </div>
    </div>
  )
}

function ReportTypeCard({ title, description, icon, formats }: { title: string; description: string; icon: React.ReactNode; formats: string[] }) {
  return (
    <Card variant="hover" className="p-6">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-10 h-10 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center">
          {icon}
        </div>
        <div>
          <h4 className="font-semibold text-gray-900">{title}</h4>
          <p className="text-sm text-gray-600">{description}</p>
        </div>
      </div>
      <div className="flex gap-2">
        {formats.map(f => (
          <span key={f} className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 rounded">{f}</span>
        ))}
      </div>
    </Card>
  )
}

function AchievementDetailCard({ achievement }: { achievement: any }) {
  const Icon = achievement.icon
  const categoryColors = {
    lessons: 'bg-blue-500',
    streak: 'bg-amber-500',
    mastery: 'bg-purple-500',
    special: 'bg-pink-500',
    xp: 'bg-green-500',
  }

  return (
    <Card variant={achievement.unlocked ? 'hover' : 'default'} className={!achievement.unlocked ? 'opacity-60 grayscale' : ''}>
      <CardContent className="p-5">
        <div className="flex items-start gap-4">
          <div className={cn(
            'w-14 h-14 rounded-2xl flex items-center justify-center flex-shrink-0',
            achievement.unlocked ? categoryColors[achievement.category] : 'bg-gray-200'
          )}>
            <Icon className={cn('w-7 h-7', achievement.unlocked ? 'text-white' : 'text-gray-400')} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <h4 className={cn('font-semibold text-gray-900', !achievement.unlocked && 'text-gray-500')}>
                {achievement.title}
              </h4>
              {achievement.unlocked && <Medal className="w-4 h-4 text-amber-500" />}
              <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-600 capitalize">
                {achievement.category}
              </span>
            </div>
            <p className={cn('text-sm text-gray-600', !achievement.unlocked && 'text-gray-400')}>
              {achievement.description}
            </p>
            {achievement.progress !== undefined && !achievement.unlocked && (
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
            {achievement.unlocked && achievement.unlockedAt && (
              <p className="text-xs text-green-600 mt-2">
                Unlocked {new Date(achievement.unlockedAt).toLocaleDateString()}
              </p>
            )}
            {achievement.xpReward && (
              <p className="text-xs text-primary-600 font-medium mt-1">
                +{achievement.xpReward} XP reward
              </p>
            )}
          </div>
        </div>
        </CardContent>
    </Card>
  )
}

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

// Import MessageSquare
import { MessageSquare } from 'lucide-react'