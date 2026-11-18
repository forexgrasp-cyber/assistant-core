import { useState, useEffect } from 'react'
import {
  User,
  Bell,
  Globe,
  Shield,
  Palette,
  Moon,
  Sun,
  Key,
  Mail,
  Phone,
  Trash2,
  Download,
  Share2,
  RotateCcw,
  Save,
  Loader2,
  LayoutDashboard,
  Lightbulb,
  Bug,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  HelpCircle,
  Sparkles,
  Mic,
  Volume2,
  Languages,
  Target,
  Trophy,
  Clock,
  Zap,
  Flame,
  Crown,
  BookOpen,
  PenTool,
  Headphones,
  Layers,
  Globe as GlobeIcon,
  Image,
  Film,
  FileText,
  Mic2,
  Keyboard,
  Settings as SettingsIcon,
  CreditCard,
  LogOut,
  AlertTriangle,
  Info,
  Link2,
  QrCode,
  Smartphone,
  Tablet,
  Monitor,
  Wifi,
  Bluetooth,
  Battery,
  Cpu,
  HardDrive,
  Database,
  Cloud,
  Lock,
  Unlock,
  Eye,
  EyeOff,
  Fingerprint,
  FaceId,
  Voice,
  Keyboard as KeyboardIcon,
  Mouse,
  Touchpad,
  Display,
  Speaker,
  Headphones as HeadphonesIcon,
  Video,
  Camera,
  Mic as MicIcon,
  VolumeX,
  Volume1,
  Volume2 as Volume2Icon,
  Repeat,
  Shuffle,
  SkipBack,
  SkipForward,
  FastForward,
  SlowMo,
  Pause,
  Play,
  StopCircle,
  RecordCircle,
  Circle,
  Square,
  Triangle,
  Hexagon,
  Star,
  Heart,
  Bookmark,
  Flag,
  Tag,
  Filter,
  Search,
  MoreHorizontal,
  MoreVertical,
  Grid,
  List,
  Columns,
  Rows,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Justify,
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Code,
  Code2,
  Terminal,
  Server,
  Zap as ZapIcon,
  Activity,
  TrendingUp,
  TrendingDown,
  BarChart,
  LineChart,
  PieChart,
  AreaChart,
  ScatterChart,
  Radar,
  Gauge,
  Thermometer,
  Compass,
  Navigation,
  Map,
  MapPin,
  Navigation2,
  Route,
  Waypoints,
  Layers as LayersIcon,
  Stack,
  Split,
  Merge,
  Fork,
  Branch,
  Commit,
  Push,
  Pull,
  Merge as MergeIcon,
  Rebase,
  CherryPick,
  Stash,
  Tag as TagIcon,
  Release,
  Issue,
  PullRequest,
  Review,
  Approve,
  Reject,
  Comment,
  Mention,
  Assign,
  Label,
  Milestone,
  Project,
  Organization,
  Team,
  User as UserIcon,
  Users,
  Group,
  Crowd,
  UserPlus,
  UserMinus,
  UserCheck,
  UserX,
  UserCog,
  Shield as ShieldIcon,
  Lock as LockIcon,
  Key as KeyIcon,
  Unlock as UnlockIcon,
  Fingerprint as FingerprintIcon,
  FaceId as FaceIdIcon,
  Voice as VoiceIcon,
  Keyboard as KeyboardIcon,
  Mouse as MouseIcon,
  Touchpad as TouchpadIcon,
  Display as DisplayIcon,
  Speaker as SpeakerIcon,
  Headphones as HeadphonesIcon,
  Video as VideoIcon,
  Camera as CameraIcon,
  Mic as MicIcon,
  VolumeX as VolumeXIcon,
  Volume1 as Volume1Icon,
  Volume2 as Volume2Icon,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input, Textarea, Select } from '@/components/ui/Input'
import { useTutorStore } from '@/stores/tutorStore'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'
import type { CEFRLevel } from '@/types'

export function Settings() {
  const { user, targetLanguage, nativeLanguage, cefrLevel, dailyGoalMinutes, autoPlayAudio, showTranslations, enableHaptics, playbackSpeed, updateUser, setTargetLanguage, setNativeLanguage, setCefrLevel, setDailyGoalMinutes, setAutoPlayAudio, setShowTranslations, setEnableHaptics, setPlaybackSpeed } = useTutorStore()
  const { user: authUser, logout, updateProfile } = useAuth()
  const [activeTab, setActiveTab] = useState<'profile' | 'learning' | 'notifications' | 'appearance' | 'audio' | 'privacy' | 'account' | 'advanced'>('profile')
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'learning', label: 'Learning', icon: Target },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'audio', label: 'Audio & Speech', icon: Volume2 },
    { id: 'privacy', label: 'Privacy', icon: Shield },
    { id: 'account', label: 'Account', icon: SettingsIcon },
    { id: 'advanced', label: 'Advanced', icon: MoreHorizontal },
  ]

  const languages = [
    { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
    { code: 'es', name: 'Spanish', nativeName: 'Español', flag: '🇪🇸' },
    { code: 'fr', name: 'French', nativeName: 'Français', flag: '🇫🇷' },
    { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
    { code: 'it', name: 'Italian', nativeName: 'Italiano', flag: '🇮🇹' },
    { code: 'pt', name: 'Portuguese', nativeName: 'Português', flag: '🇵🇹' },
    { code: 'ja', name: 'Japanese', nativeName: '日本語', flag: '🇯🇵' },
    { code: 'ko', name: 'Korean', nativeName: '한국어', flag: '🇰🇷' },
    { code: 'zh', name: 'Chinese', nativeName: '中文', flag: '🇨🇳' },
    { code: 'ru', name: 'Russian', nativeName: 'Русский', flag: '🇷🇺' },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦' },
    { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', flag: '🇮🇳' },
  ]

  const levels: CEFRLevel[] = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']

  const handleSave = async () => {
    setIsSaving(true)
    await new Promise(resolve => setTimeout(resolve, 1000))
    setIsSaving(false)
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  return (
    <div className="space-y-6 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl lg:text-3xl font-bold text-gray-900">Settings</h1>
          <p className="text-gray-600 mt-1">Customize your learning experience</p>
        </div>
        <Button
          variant="primary"
          onClick={handleSave}
          disabled={isSaving}
          leftIcon={isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
        >
          {isSaving ? 'Saving...' : 'Save Changes'}
        </Button>
      </div>

      {saveSuccess && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-xl flex items-center gap-3 animate-in">
          <CheckCircle className="w-5 h-5 text-green-500" />
          <span className="text-green-800 font-medium">Settings saved successfully!</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex flex-wrap gap-1 p-1 bg-gray-100 rounded-xl">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
                activeTab === tab.id
                  ? 'bg-white text-primary-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              )}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5 text-primary-600" />
                Profile Information
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="flex items-center gap-6">
                <div className="w-24 h-24 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center text-3xl font-bold text-white">
                  {authUser?.name?.charAt(0).toUpperCase() || 'U'}
                </div>
                <div className="flex-1">
                  <Input
                    label="Display Name"
                    value={authUser?.name || ''}
                    onChange={(e) => updateProfile({ name: e.target.value })}
                    placeholder="Your name"
                  />
                  <Input
                    label="Email"
                    value={authUser?.email || ''}
                    onChange={(e) => updateProfile({ email: e.target.value })}
                    type="email"
                    placeholder="you@example.com"
                  />
                </div>
              </div>

              <div className="grid sm:grid-cols-2 gap-4 pt-4 border-t border-gray-100">
                <Select
                  label="Native Language"
                  value={nativeLanguage}
                  onChange={(e) => setNativeLanguage(e.target.value)}
                  options={languages.map(l => ({ value: l.code, label: `${l.flag} ${l.name}` }))}
                />
                <Select
                  label="Target Language"
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  options={languages.filter(l => l.code !== nativeLanguage).map(l => ({ value: l.code, label: `${l.flag} ${l.name}` }))}
                />
              </div>

              <Select
                label="Current CEFR Level"
                value={cefrLevel}
                onChange={(e) => setCefrLevel(e.target.value as CEFRLevel)}
                options={levels.map(l => ({ value: l, label: l }))}
              />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-primary-600" />
                Learning Goals
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Daily Goal: {dailyGoalMinutes} minutes</label>
                  <input
                    type="range"
                    min="5"
                    max="60"
                    step="5"
                    value={dailyGoalMinutes}
                    onChange={(e) => setDailyGoalMinutes(Number(e.target.value))}
                    className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Weekly Target: {dailyGoalMinutes * 7} minutes</label>
                  <div className="h-2 bg-gray-200 rounded-lg overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                      style={{ width: '65%' }}
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Learning Tab */}
      {activeTab === 'learning' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5 text-primary-600" />
                Learning Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="grid sm:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">Focus Areas</h4>
                  <p className="text-sm text-gray-600">Select skills you want to prioritize</p>
                  <div className="grid grid-cols-2 gap-3">
                    {[
                      { id: 'conversation', label: 'Conversation', icon: MessageSquare },
                      { id: 'grammar', label: 'Grammar', icon: BookOpen },
                      { id: 'vocabulary', label: 'Vocabulary', icon: PenTool },
                      { id: 'pronunciation', label: 'Pronunciation', icon: Mic },
                      { id: 'writing', label: 'Writing', icon: PenTool },
                      { id: 'reading', label: 'Reading', icon: BookOpen },
                      { id: 'listening', label: 'Listening', icon: Headphones },
                      { id: 'culture', label: 'Culture', icon: GlobeIcon },
                    ].map(area => (
                      <label key={area.id} className="flex items-center gap-3 p-3 rounded-xl border border-gray-200 hover:border-primary-300 cursor-pointer transition-colors">
                        <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                        <span className="flex items-center gap-2">
                          <area.icon className="w-5 h-5 text-primary-600" />
                          <span className="font-medium text-gray-900">{area.label}</span>
                        </span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-semibold text-gray-900">Lesson Settings</h4>
                  <div className="space-y-4">
                    <label className="flex items-center gap-3">
                      <input type="checkbox" checked={autoPlayAudio} onChange={(e) => setAutoPlayAudio(e.target.checked)} className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                      <span className="text-gray-700">Auto-play audio content</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" checked={showTranslations} onChange={(e) => setShowTranslations(e.target.checked)} className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                      <span className="text-gray-700">Show translations by default</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" checked={enableHaptics} onChange={(e) => setEnableHaptics(e.target.checked)} className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                      <span className="text-gray-700">Enable haptic feedback (mobile)</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                      <span className="text-gray-700">Adaptive difficulty</span>
                    </label>
                    <label className="flex items-center gap-3">
                      <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                      <span className="text-gray-700">Spaced repetition for vocabulary</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <h4 className="font-semibold text-gray-900 mb-4">Playback Speed</h4>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0.5"
                    max="2"
                    step="0.25"
                    value={playbackSpeed}
                    onChange={(e) => setPlaybackSpeed(Number(e.target.value))}
                    className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                  />
                  <span className="text-lg font-bold text-gray-900 w-16 text-right">{playbackSpeed}x</span>
                </div>
                <div className="flex gap-2 mt-3">
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map(speed => (
                    <button
                      key={speed}
                      onClick={() => setPlaybackSpeed(speed)}
                      className={cn(
                        'px-3 py-1.5 text-sm rounded-lg text-gray-700 transition-colors',
                        playbackSpeed === speed ? 'bg-primary-100 text-primary-700 font-medium' : 'bg-gray-100 hover:bg-gray-200'
                      )}
                    >
                      {speed}x
                    </button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="w-5 h-5 text-primary-600" />
                Difficulty & Adaptivity
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Adaptive Difficulty Level</label>
                <select className="w-full max-w-xs px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                  <option>Automatic (Recommended)</option>
                  <option>Fixed - Easy</option>
                  <option>Fixed - Medium</option>
                  <option>Fixed - Hard</option>
                </select>
              </div>
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Adjust based on performance</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Reduce difficulty after mistakes</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Increase difficulty after mastery</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Personalized review scheduling</span>
                </label>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === 'notifications' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-primary-600" />
                Notification Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-4">
                {[
                  { id: 'daily-reminder', title: 'Daily Practice Reminder', description: 'Get reminded to practice at your preferred time', icon: Clock, defaultChecked: true },
                  { id: 'streak-alert', title: 'Streak Alerts', description: 'Notifications when your streak is at risk', icon: Flame, defaultChecked: true },
                  { id: 'lesson-complete', title: 'Lesson Completion', description: 'Celebrate when you finish a lesson', icon: CheckCircle, defaultChecked: true },
                  { id: 'achievement', title: 'Achievement Unlocked', description: 'Get notified when you earn achievements', icon: Trophy, defaultChecked: true },
                  { id: 'weekly-report', title: 'Weekly Progress Report', description: 'Summary of your weekly activity', icon: BarChart, defaultChecked: false },
                  { id: 'new-content', title: 'New Content', description: 'Be the first to know about new lessons', icon: Sparkles, defaultChecked: false },
                  { id: 'tips', title: 'Learning Tips', description: 'Occasional tips to improve your learning', icon: Lightbulb, defaultChecked: false },
                  { id: 'social', title: 'Social Activity', description: 'When friends complete lessons or earn achievements', icon: Users, defaultChecked: false },
                ].map(item => (
                  <label key={item.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-xl bg-primary-100 text-primary-600 flex items-center justify-center">
                        <item.icon className="w-5 h-5" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{item.title}</p>
                        <p className="text-sm text-gray-500">{item.description}</p>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      defaultChecked={item.defaultChecked}
                      className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mail className="w-5 h-5 text-primary-600" />
                Email Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <p className="text-gray-600">Manage how often you receive email updates</p>
              <div className="space-y-3">
                {[
                  { label: 'Daily practice reminder', frequency: 'Daily at 9:00 AM' },
                  { label: 'Weekly progress summary', frequency: 'Weekly on Monday' },
                  { label: 'Monthly achievement report', frequency: 'Monthly on 1st' },
                  { label: 'New content announcements', frequency: 'As available' },
                  { label: 'Account & security updates', frequency: 'As needed' },
                ].map((item, index) => (
                  <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <div>
                      <p className="font-medium text-gray-900">{item.label}</p>
                      <p className="text-sm text-gray-500">{item.frequency}</p>
                    </div>
                    <select className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm">
                      <option>Enabled</option>
                      <option>Disabled</option>
                      <option>Digest only</option>
                    </select>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Appearance Tab */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Palette className="w-5 h-5 text-primary-600" />
                Theme & Display
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-4">Theme</label>
                <div className="grid grid-cols-3 gap-4">
                  {['light', 'dark', 'system'].map(theme => (
                    <button
                      key={theme}
                      className={cn(
                        'p-4 rounded-xl border-2 text-center transition-all',
                        theme === 'system' ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:border-primary-300'
                      )}
                    >
                      <div className={cn('w-12 h-12 rounded-xl mx-auto mb-2 flex items-center justify-center',
                        theme === 'light' && 'bg-white border border-gray-200',
                        theme === 'dark' && 'bg-gray-900',
                        theme === 'system' && 'bg-gradient-to-br from-white to-gray-900'
                      )}>
                        {theme === 'light' && <Sun className="w-6 h-6 text-amber-500" />}
                        {theme === 'dark' && <Moon className="w-6 h-6 text-blue-400" />}
                        {theme === 'system' && <Monitor className="w-6 h-6 text-gray-600" />}
                      </div>
                      <p className="font-medium text-gray-900 capitalize">{theme}</p>
                      <p className="text-xs text-gray-500">
                        {theme === 'light' && 'Always light'}
                        {theme === 'dark' && 'Always dark'}
                        {theme === 'system' && 'Follow system'}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700 mb-4">Color Theme</label>
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { name: 'Ocean', primary: '#0ea5e9', accent: '#d946ef' },
                    { name: 'Forest', primary: '#10b981', accent: '#059669' },
                    { name: 'Sunset', primary: '#f97316', accent: '#ec4899' },
                    { name: 'Violet', primary: '#8b5cf6', accent: '#06b6d4' },
                    { name: 'Rose', primary: '#ec4899', accent: '#f97316' },
                  ].map(color => (
                    <button
                      key={color.name}
                      className={cn(
                        'p-3 rounded-xl border-2 text-center transition-all',
                        color.name === 'Ocean' ? 'border-primary-500' : 'border-gray-200'
                      )}
                    >
                      <div className="w-full h-8 rounded-lg mb-2 bg-gradient-to-r" style={{ background: `linear-gradient(to right, ${color.primary}, ${color.accent})` }} />
                      <p className="text-sm font-medium text-gray-900">{color.name}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Compact mode (denser UI)</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Reduce animations</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">High contrast mode</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Dyslexia-friendly font</span>
                </label>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LayoutDashboard className="w-5 h-5 text-primary-600" />
                Dashboard Layout
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <p className="text-gray-600">Customize what appears on your dashboard</p>
              <div className="space-y-3">
                {[
                  { label: 'Streak & XP counters', enabled: true },
                  { label: 'Current lesson progress', enabled: true },
                  { label: 'Skill progress bars', enabled: true },
                  { label: 'Weekly activity chart', enabled: true },
                  { label: 'Upcoming achievements', enabled: true },
                  { label: 'Recommended next lesson', enabled: true },
                  { label: 'Leaderboard', enabled: false },
                  { label: 'Study time heatmap', enabled: false },
                ].map((item, index) => (
                  <label key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                    <span className="text-gray-700">{item.label}</span>
                    <input
                      type="checkbox"
                      defaultChecked={item.enabled}
                      className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                    />
                  </label>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Audio & Speech Tab */}
      {activeTab === 'audio' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Volume2 className="w-5 h-5 text-primary-600" />
                Audio Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="grid sm:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Default TTS Voice</label>
                  <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                    <option>Auto-detect (Recommended)</option>
                    <option>Google Spanish (es-ES)</option>
                    <option>Google Mexican Spanish (es-MX)</option>
                    <option>Microsoft Spanish (es-ES)</option>
                    <option>Amazon Polly Spanish (es-ES)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Speech Recognition Language</label>
                  <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                    <option>Spanish (Spain) - es-ES</option>
                    <option>Spanish (Mexico) - es-MX</option>
                    <option>Spanish (Argentina) - es-AR</option>
                    <option>Spanish (Colombia) - es-CO</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700 mb-2">Microphone Sensitivity</label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={50}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Low</span>
                  <span>Medium</span>
                  <span>High</span>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Noise cancellation</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Auto-gain control</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Echo cancellation</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Play button click sounds</span>
                </label>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Mic className="w-5 h-5 text-primary-600" />
                Pronunciation Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Real-time feedback during recording</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Show phoneme-level scoring</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Compare with native speaker</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Require minimum score to continue</span>
                </label>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <label className="block text-sm font-medium text-gray-700 mb-2">Minimum Passing Score: 70%</label>
                <input
                  type="range"
                  min="50"
                  max="95"
                  step="5"
                  value={70}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Headphones className="w-5 h-5 text-primary-600" />
                Audio Quality
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Streaming Quality</label>
                  <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                    <option>High (128 kbps)</option>
                    <option>Medium (64 kbps)</option>
                    <option>Low (32 kbps) - Data saver</option>
                    <option>Auto (Adaptive)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">Download Quality</label>
                  <select className="w-full px-4 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-500">
                    <option>High (256 kbps)</option>
                    <option>Medium (128 kbps)</option>
                    <option>Low (64 kbps)</option>
                  </select>
                </div>
              </div>
              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Preload next audio</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Cache for offline use</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" defaultChecked />
                  <span className="text-gray-700">Background playback</span>
                </label>
                <label className="flex items-center gap-3">
                  <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  <span className="text-gray-700">Download on WiFi only</span>
                </label>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Privacy Tab */}
      {activeTab === 'privacy' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-primary-600" />
                Data & Privacy
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-4">
                {[
                  { title: 'Profile Visibility', description: 'Who can see your profile and progress', options: ['Public', 'Friends only', 'Private'] },
                  { title: 'Learning Activity', description: 'Share your streak and completions', options: ['Public', 'Friends only', 'Private'] },
                  { title: 'Achievement Sharing', description: 'Auto-share achievements on social', options: ['Enabled', 'Disabled'] },
                  { title: 'Data Analytics', description: 'Allow anonymous usage analytics', options: ['Enabled', 'Disabled'] },
                ].map((item, index) => (
                  <div key={index} className="p-4 bg-gray-50 rounded-xl">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <p className="font-medium text-gray-900">{item.title}</p>
                        <p className="text-sm text-gray-500">{item.description}</p>
                      </div>
                      <select className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm">
                        {item.options.map(opt => <option key={opt}>{opt}</option>)}
                      </select>
                    </div>
                  </div>
                ))}
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <Button variant="outline" leftIcon={<Download className="w-4 h-4" />}>Export My Data</Button>
                <Button variant="outline" leftIcon={<RotateCcw className="w-4 h-4" />}>Request Data Deletion</Button>
                <Button variant="outline" leftIcon={<Shield className="w-4 h-4" />}>Privacy Policy</Button>
                <Button variant="outline" leftIcon={<FileText className="w-4 h-4" />}>Terms of Service</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="w-5 h-5 text-primary-600" />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-green-100 text-green-600 flex items-center justify-center">
                      <Shield className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Two-Factor Authentication</p>
                      <p className="text-sm text-gray-500">Add an extra layer of security</p>
                    </div>
                  </div>
                  <Button variant="primary" size="sm">Enable</Button>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center">
                      <Fingerprint className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Biometric Login</p>
                      <p className="text-sm text-gray-500">Use Face ID or fingerprint</p>
                    </div>
                  </div>
                  <Button variant="primary" size="sm">Set Up</Button>
                </div>

                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center">
                      <Key className="w-5 h-5" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">Passkeys</p>
                      <p className="text-sm text-gray-500">Passwordless authentication</p>
                    </div>
                  </div>
                  <Button variant="primary" size="sm">Add Passkey</Button>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100">
                <Button variant="outline" leftIcon={<LogOut className="w-4 h-4" />}>Log out of all devices</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Account Tab */}
      {activeTab === 'account' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="w-5 h-5 text-primary-600" />
                Account Management
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Subscription</p>
                      <p className="text-sm text-gray-500">Free Plan</p>
                    </div>
                    <Button variant="primary" size="sm">Upgrade</Button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Email</p>
                      <p className="text-sm text-gray-500">{authUser?.email}</p>
                    </div>
                    <Button variant="outline" size="sm">Change</Button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Password</p>
                      <p className="text-sm text-gray-500">Last changed 30 days ago</p>
                    </div>
                    <Button variant="outline" size="sm">Change Password</Button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Connected Accounts</p>
                      <p className="text-sm text-gray-500">Google • Apple</p>
                    </div>
                    <Button variant="outline" size="sm">Manage</Button>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 space-y-3">
                <Button variant="outline" className="w-full justify-start" leftIcon={<Download className="w-4 h-4" />}>Download Account Data</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<RotateCcw className="w-4 h-4" />}>Delete Account</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-primary-600" />
                Billing & Payments
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="p-4 bg-gray-50 rounded-xl">
                <p className="font-medium text-gray-900 mb-2">No active subscription</p>
                <p className="text-sm text-gray-500">Upgrade to Pro for unlimited practice, offline mode, and advanced analytics</p>
                <Button variant="primary" className="mt-3" leftIcon={<Zap className="w-4 h-4" />}>View Plans</Button>
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <Button variant="outline" className="w-full justify-start" leftIcon={<FileText className="w-4 h-4" />}>Invoice History</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<CreditCard className="w-4 h-4" />}>Payment Methods</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<SettingsIcon className="w-4 h-4" />}>Billing Details</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<HelpCircle className="w-4 h-4" />}>Billing Support</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Advanced Tab */}
      {activeTab === 'advanced' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-primary-600" />
                Developer Options
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-6">
              <div className="space-y-4">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Debug Mode</p>
                      <p className="text-sm text-gray-500">Show debug information and logs</p>
                    </div>
                    <input type="checkbox" className="w-5 h-5 rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">API Endpoint</p>
                      <p className="text-sm text-gray-500 font-mono">https://api.linguflow.com/v1</p>
                    </div>
                    <Button variant="outline" size="sm">Change</Button>
                  </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-gray-900">Log Level</p>
                      <p className="text-sm text-gray-500">Error</p>
                    </div>
                    <select className="px-3 py-1.5 rounded-lg border border-gray-200 text-sm w-40">
                      <option>Error</option>
                      <option>Warn</option>
                      <option>Info</option>
                      <option>Debug</option>
                      <option>Trace</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-2 gap-4">
                <Button variant="outline" leftIcon={<Download className="w-4 h-4" />}>Export Logs</Button>
                <Button variant="outline" leftIcon={<RotateCcw className="w-4 h-4" />}>Clear Cache</Button>
                <Button variant="outline" leftIcon={<Database className="w-4 h-4" />}>Reset Local Data</Button>
                <Button variant="outline" leftIcon={<Bug className="w-4 h-4" />}>Report Bug</Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="w-5 h-5 text-primary-600" />
                About
              </CardTitle>
            </CardHeader>
            <CardContent className="p-6 space-y-4">
              <div className="grid sm:grid-cols-2 gap-4 text-center">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-2xl font-bold text-primary-600">2026.11.3</p>
                  <p className="text-sm text-gray-500">App Version</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-2xl font-bold text-primary-600">2026.11.3</p>
                  <p className="text-sm text-gray-500">Shared Library</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-2xl font-bold text-primary-600">React 18.2</p>
                  <p className="text-sm text-gray-500">Framework</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-2xl font-bold text-primary-600">TypeScript 5.3</p>
                  <p className="text-sm text-gray-500">Language</p>
                </div>
              </div>

              <div className="pt-4 border-t border-gray-100 grid sm:grid-cols-3 gap-4">
                <Button variant="outline" className="w-full justify-start" leftIcon={<Link2 className="w-4 h-4" />}>Open Source Licenses</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<FileText className="w-4 h-4" />}>Privacy Policy</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<FileText className="w-4 h-4" />}>Terms of Service</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<Heart className="w-4 h-4" />}>Credits</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<Mail className="w-4 h-4" />}>Contact Support</Button>
                <Button variant="outline" className="w-full justify-start" leftIcon={<Star className="w-4 h-4" />}>Rate App</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}