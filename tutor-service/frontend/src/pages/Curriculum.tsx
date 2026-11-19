import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  BookOpen,
  Mic,
  PenTool,
  Headphones,
  Globe,
  FileText,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Lock,
  CheckCircle,
  Star,
  Target,
  ArrowRight,
  Layers,
  List,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Input'
import { useTutorStore } from '@/stores/tutorStore'
import { cn, formatDuration, getCEFRColor, getCEFRGradient } from '@/lib/utils'
import type { Lesson, FocusArea, CEFRLevel } from '@/types'

// Extended mock lessons with full content
const allLessons: Lesson[] = [
  // A1 - Beginner
  {
    id: 'a1-greetings',
    title: 'Greetings & Introductions',
    description: 'Learn essential greetings, farewells, and how to introduce yourself naturally.',
    language: 'es',
    level: 'A1',
    focusArea: 'conversation',
    duration: 15,
    xpReward: 50,
    content: [
      { id: 'c1', type: 'dialogue', title: 'Meeting Someone New', data: {}, order: 1, estimatedTime: 5 },
      { id: 'c2', type: 'exercise', title: 'Greeting Practice', data: {}, order: 2, estimatedTime: 5 },
      { id: 'c3', type: 'pronunciation', title: 'Vowel Sounds in Greetings', data: {}, order: 3, estimatedTime: 5 },
    ],
    prerequisites: [],
    tags: ['basics', 'greetings', 'conversation', 'formal', 'informal'],
    order: 1,
  },
  {
    id: 'a1-numbers',
    title: 'Numbers 1-100',
    description: 'Master Spanish numbers from 1 to 100 with pronunciation and listening practice.',
    language: 'es',
    level: 'A1',
    focusArea: 'vocabulary',
    duration: 20,
    xpReward: 75,
    content: [
      { id: 'c1', type: 'audio', title: 'Numbers 1-20', data: {}, order: 1, estimatedTime: 7 },
      { id: 'c2', type: 'exercise', title: 'Number Recognition', data: {}, order: 2, estimatedTime: 6 },
      { id: 'c3', type: 'pronunciation', title: 'Number Pronunciation Patterns', data: {}, order: 3, estimatedTime: 7 },
    ],
    prerequisites: ['a1-greetings'],
    tags: ['numbers', 'pronunciation', 'vocabulary', 'listening'],
    order: 2,
  },
  {
    id: 'a1-ar-verbs',
    title: 'Present Tense -AR Verbs',
    description: 'Conjugate and use regular -AR verbs in the present tense with confidence.',
    language: 'es',
    level: 'A1',
    focusArea: 'grammar',
    duration: 25,
    xpReward: 100,
    content: [
      { id: 'c1', type: 'text', title: 'AR Verb Conjugation Rules', data: {}, order: 1, estimatedTime: 8 },
      { id: 'c2', type: 'exercise', title: 'Conjugation Drills', data: {}, order: 2, estimatedTime: 10 },
      { id: 'c3', type: 'writing', title: 'Write Your Daily Routine', data: {}, order: 3, estimatedTime: 7 },
    ],
    prerequisites: ['a1-greetings'],
    tags: ['grammar', 'verbs', 'conjugation', 'present tense', 'writing'],
    order: 3,
  },
  {
    id: 'a1-pronunciation-vowels',
    title: 'Spanish Pronunciation: Vowels',
    description: 'Perfect your Spanish vowel sounds with native speaker examples and feedback.',
    language: 'es',
    level: 'A1',
    focusArea: 'pronunciation',
    duration: 15,
    xpReward: 50,
    content: [
      { id: 'c1', type: 'video', title: 'Vowel Sounds Overview', data: {}, order: 1, estimatedTime: 5 },
      { id: 'c2', type: 'pronunciation', title: 'Practice Each Vowel', data: {}, order: 2, estimatedTime: 5 },
      { id: 'c3', type: 'exercise', title: 'Minimal Pairs', data: {}, order: 3, estimatedTime: 5 },
    ],
    prerequisites: [],
    tags: ['pronunciation', 'vowels', 'basics', 'native-speaker'],
    order: 4,
  },
  {
    id: 'a1-family',
    title: 'Family & Relationships',
    description: 'Talk about your family, describe people, and express relationships.',
    language: 'es',
    level: 'A1',
    focusArea: 'vocabulary',
    duration: 20,
    xpReward: 80,
    content: [
      { id: 'c1', type: 'flashcard', title: 'Family Vocabulary', data: {}, order: 1, estimatedTime: 8 },
      { id: 'c2', type: 'dialogue', title: 'Describing Your Family', data: {}, order: 2, estimatedTime: 7 },
      { id: 'c3', type: 'exercise', title: 'Family Tree Practice', data: {}, order: 3, estimatedTime: 5 },
    ],
    prerequisites: ['a1-greetings', 'a1-numbers'],
    tags: ['family', 'vocabulary', 'descriptions', 'conversation'],
    order: 5,
  },
  {
    id: 'a1-food',
    title: 'Food & Dining',
    description: 'Essential vocabulary and phrases for ordering food and dining out.',
    language: 'es',
    level: 'A1',
    focusArea: 'conversation',
    duration: 20,
    xpReward: 80,
    content: [
      { id: 'c1', type: 'dialogue', title: 'At the Restaurant', data: {}, order: 1, estimatedTime: 8 },
      { id: 'c2', type: 'vocabulary', title: 'Menu Items & Dietary Needs', data: {}, order: 2, estimatedTime: 6 },
      { id: 'c3', type: 'pronunciation', title: 'Food Pronunciation', data: {}, order: 3, estimatedTime: 6 },
    ],
    prerequisites: ['a1-greetings'],
    tags: ['food', 'restaurant', 'practical', 'ordering'],
    order: 6,
  },
  // A2 - Elementary
  {
    id: 'a2-past-tense',
    title: 'Preterite vs Imperfect',
    description: 'Master the two main past tenses and when to use each one.',
    language: 'es',
    level: 'A2',
    focusArea: 'grammar',
    duration: 30,
    xpReward: 150,
    content: [
      { id: 'c1', type: 'video', title: 'Preterite vs Imperfect Explained', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'exercise', title: 'Tense Selection Practice', data: {}, order: 2, estimatedTime: 10 },
      { id: 'c3', type: 'writing', title: 'Write a Childhood Memory', data: {}, order: 3, estimatedTime: 10 },
    ],
    prerequisites: ['a1-ar-verbs'],
    tags: ['grammar', 'past tense', 'preterite', 'imperfect', 'advanced'],
    order: 7,
  },
  {
    id: 'a2-subjunctive-intro',
    title: 'Introduction to Subjunctive',
    description: 'Learn when and how to use the present subjunctive mood.',
    language: 'es',
    level: 'A2',
    focusArea: 'grammar',
    duration: 25,
    xpReward: 125,
    content: [
      { id: 'c1', type: 'text', title: 'WEIRDO Triggers', data: {}, order: 1, estimatedTime: 8 },
      { id: 'c2', type: 'exercise', title: 'Subjunctive Conjugation', data: {}, order: 2, estimatedTime: 10 },
      { id: 'c3', type: 'dialogue', title: 'Expressing Wishes & Doubts', data: {}, order: 3, estimatedTime: 7 },
    ],
    prerequisites: ['a2-past-tense'],
    tags: ['grammar', 'subjunctive', 'mood', 'advanced'],
    order: 8,
  },
  {
    id: 'a2-travel',
    title: 'Travel & Transportation',
    description: 'Navigate airports, trains, taxis, and ask for directions like a local.',
    language: 'es',
    level: 'A2',
    focusArea: 'conversation',
    duration: 25,
    xpReward: 100,
    content: [
      { id: 'c1', type: 'dialogue', title: 'At the Airport', data: {}, order: 1, estimatedTime: 8 },
      { id: 'c2', type: 'vocabulary', title: 'Transportation Terms', data: {}, order: 2, estimatedTime: 7 },
      { id: 'c3', type: 'listening', title: 'Announcements & Directions', data: {}, order: 3, estimatedTime: 10 },
    ],
    prerequisites: ['a1-food'],
    tags: ['travel', 'transportation', 'airport', 'directions', 'practical'],
    order: 9,
  },
  // B1 - Intermediate
  {
    id: 'b1-conditionals',
    title: 'Conditional Tense & If Clauses',
    description: 'Express hypothetical situations, make polite requests, and discuss possibilities.',
    language: 'es',
    level: 'B1',
    focusArea: 'grammar',
    duration: 30,
    xpReward: 200,
    content: [
      { id: 'c1', type: 'video', title: 'Conditionals Explained', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'exercise', title: 'First & Second Conditionals', data: {}, order: 2, estimatedTime: 12 },
      { id: 'c3', type: 'conversation', title: 'What Would You Do?', data: {}, order: 3, estimatedTime: 8 },
    ],
    prerequisites: ['a2-subjunctive-intro'],
    tags: ['grammar', 'conditionals', 'hypothetical', 'polite-requests'],
    order: 10,
  },
  {
    id: 'b1-work',
    title: 'Professional Spanish',
    description: 'Business vocabulary, formal emails, meetings, and workplace conversations.',
    language: 'es',
    level: 'B1',
    focusArea: 'conversation',
    duration: 35,
    xpReward: 250,
    content: [
      { id: 'c1', type: 'text', title: 'Formal vs Informal Register', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'writing', title: 'Professional Email Templates', data: {}, order: 2, estimatedTime: 15 },
      { id: 'c3', type: 'dialogue', title: 'Meeting Roleplay', data: {}, order: 3, estimatedTime: 10 },
    ],
    prerequisites: ['b1-conditionals'],
    tags: ['business', 'formal', 'workplace', 'emails', 'meetings'],
    order: 11,
  },
  {
    id: 'b1-news',
    title: 'News & Current Events',
    description: 'Understand news broadcasts, read articles, and discuss current events.',
    language: 'es',
    level: 'B1',
    focusArea: 'listening',
    duration: 30,
    xpReward: 200,
    content: [
      { id: 'c1', type: 'audio', title: 'News Segment: Technology', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'reading', title: 'News Article Analysis', data: {}, order: 2, estimatedTime: 12 },
      { id: 'c3', type: 'conversation', title: 'Discussing Headlines', data: {}, order: 3, estimatedTime: 8 },
    ],
    prerequisites: ['b1-work'],
    tags: ['news', 'current events', 'listening', 'reading', 'discussion'],
    order: 12,
  },
  // B2 - Upper Intermediate
  {
    id: 'b2-subjunctive-advanced',
    title: 'Advanced Subjunctive Uses',
    description: 'Master imperfect subjunctive, past perfect subjunctive, and complex structures.',
    language: 'es',
    level: 'B2',
    focusArea: 'grammar',
    duration: 40,
    xpReward: 300,
    content: [
      { id: 'c1', type: 'video', title: 'Imperfect Subjunctive Formation', data: {}, order: 1, estimatedTime: 12 },
      { id: 'c2', type: 'exercise', title: 'Subjunctive in Complex Sentences', data: {}, order: 2, estimatedTime: 15 },
      { id: 'c3', type: 'writing', title: 'Hypothetical Scenarios', data: {}, order: 3, estimatedTime: 13 },
    ],
    prerequisites: ['b1-conditionals'],
    tags: ['grammar', 'advanced subjunctive', 'imperfect', 'perfect', 'complex-sentences'],
    order: 13,
  },
  {
    id: 'b2-idioms',
    title: 'Idioms & Colloquial Expressions',
    description: 'Sound like a native with common idioms, slang, and regional expressions.',
    language: 'es',
    level: 'B2',
    focusArea: 'vocabulary',
    duration: 30,
    xpReward: 250,
    content: [
      { id: 'c1', type: 'video', title: 'Top 50 Spanish Idioms', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'exercise', title: 'Idiom Matching & Context', data: {}, order: 2, estimatedTime: 12 },
      { id: 'c3', type: 'conversation', title: 'Natural Conversation Practice', data: {}, order: 3, estimatedTime: 8 },
    ],
    prerequisites: ['b2-subjunctive-advanced'],
    tags: ['idioms', 'slang', 'colloquial', 'native-speaker', 'culture'],
    order: 14,
  },
  {
    id: 'b2-debate',
    title: 'Debate & Argumentation',
    description: 'Structure arguments, express opinions, and participate in formal debates.',
    language: 'es',
    level: 'B2',
    focusArea: 'conversation',
    duration: 35,
    xpReward: 300,
    content: [
      { id: 'c1', type: 'text', title: 'Argument Structure & Connectors', data: {}, order: 1, estimatedTime: 10 },
      { id: 'c2', type: 'exercise', title: 'Building Your Case', data: {}, order: 2, estimatedTime: 12 },
      { id: 'c3', type: 'conversation', title: 'Live Debate Practice', data: {}, order: 3, estimatedTime: 13 },
    ],
    prerequisites: ['b2-idioms'],
    tags: ['debate', 'argumentation', 'critical-thinking', 'formal-speech'],
    order: 15,
  },
  // C1 - Advanced
  {
    id: 'c1-literature',
    title: 'Spanish Literature & Analysis',
    description: 'Read and analyze works by Cervantes, Borges, García Márquez, and more.',
    language: 'es',
    level: 'C1',
    focusArea: 'reading',
    duration: 45,
    xpReward: 400,
    content: [
      { id: 'c1', type: 'reading', title: 'Don Quixote - Excerpts', data: {}, order: 1, estimatedTime: 15 },
      { id: 'c2', type: 'reading', title: 'Borges & Magical Realism', data: {}, order: 2, estimatedTime: 15 },
      { id: 'c3', type: 'writing', title: 'Literary Analysis Essay', data: {}, order: 3, estimatedTime: 15 },
    ],
    prerequisites: ['b2-debate'],
    tags: ['literature', 'analysis', 'classics', 'culture', 'advanced-reading'],
    order: 16,
  },
  {
    id: 'c1-academic',
    title: 'Academic & Technical Writing',
    description: 'Write research papers, technical reports, and formal academic Spanish.',
    language: 'es',
    level: 'C1',
    focusArea: 'writing',
    duration: 40,
    xpReward: 350,
    content: [
      { id: 'c1', type: 'text', title: 'Academic Register & Structure', data: {}, order: 1, estimatedTime: 12 },
      { id: 'c2', type: 'writing', title: 'Research Paper Workshop', data: {}, order: 2, estimatedTime: 16 },
      { id: 'c3', type: 'exercise', title: 'Citation & Referencing', data: {}, order: 3, estimatedTime: 12 },
    ],
    prerequisites: ['c1-literature'],
    tags: ['academic', 'technical', 'research', 'formal-writing', 'citations'],
    order: 17,
  },
  // C2 - Proficient
  {
    id: 'c2-native',
    title: 'Native-Level Mastery',
    description: 'Refine your Spanish to native-like fluency across all registers and contexts.',
    language: 'es',
    level: 'C2',
    focusArea: 'conversation',
    duration: 60,
    xpReward: 500,
    content: [
      { id: 'c1', type: 'conversation', title: 'Register Switching Practice', data: {}, order: 1, estimatedTime: 20 },
      { id: 'c2', type: 'pronunciation', title: 'Regional Accent Mastery', data: {}, order: 2, estimatedTime: 20 },
      { id: 'c3', type: 'video', title: 'Cultural Nuances & Humor', data: {}, order: 3, estimatedTime: 20 },
    ],
    prerequisites: ['c1-academic'],
    tags: ['native-level', 'fluency', 'accents', 'culture', 'mastery'],
    order: 18,
  },
]

const levels: CEFRLevel[] = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const focusAreaOptions: FocusArea[] = ['conversation', 'grammar', 'vocabulary', 'pronunciation', 'writing', 'reading', 'listening', 'culture']

function getLevelLabel(level: CEFRLevel): string {
  const labels: Record<CEFRLevel, string> = {
    A1: 'Beginner',
    A2: 'Elementary',
    B1: 'Intermediate',
    B2: 'Upper Intermediate',
    C1: 'Advanced',
    C2: 'Proficient',
  }
  return labels[level]
}

function getLevelGradient(level: CEFRLevel): string {
  const gradients: Record<CEFRLevel, string> = {
    A1: 'linear-gradient(90deg, #22c55e 0%, #16a34a 100%)',
    A2: 'linear-gradient(90deg, #84cc16 0%, #65a30d 100%)',
    B1: 'linear-gradient(90deg, #eab308 0%, #ca8a04 100%)',
    B2: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)',
    C1: 'linear-gradient(90deg, #f97316 0%, #ea580c 100%)',
    C2: 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)',
  }
  return gradients[level]
}

export function CurriculumPage() {
  const { userProgress, lessonProgress, completeLesson } = useTutorStore()
  const xp = userProgress?.xp ?? 0
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLevel, setSelectedLevel] = useState<CEFRLevel | 'all'>('all')
  const [selectedFocusArea, setSelectedFocusArea] = useState<FocusArea | 'all'>('all')
  const [showLocked, setShowLocked] = useState(true)

  const filteredLessons = useMemo(() => {
    return allLessons.filter(lesson => {
      const matchesSearch = lesson.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lesson.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        lesson.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      const matchesLevel = selectedLevel === 'all' || lesson.level === selectedLevel
      const matchesFocus = selectedFocusArea === 'all' || lesson.focusArea === selectedFocusArea
      const isUnlocked = lesson.prerequisites.every(prereq => 
        lessonProgress[prereq]?.status === 'completed' || lessonProgress[prereq]?.status === 'mastered'
      )
      const matchesLocked = showLocked || isUnlocked
      return matchesSearch && matchesLevel && matchesFocus && matchesLocked
    })
  }, [searchQuery, selectedLevel, selectedFocusArea, showLocked, lessonProgress])

  const lessonsByLevel = useMemo(() => {
    const grouped: Record<CEFRLevel, Lesson[]> = {
      A1: [], A2: [], B1: [], B2: [], C1: [], C2: []
    }
    allLessons.forEach(lesson => {
      grouped[lesson.level].push(lesson)
    })
    return grouped
  }, [])

  const getLessonStatus = (lesson: Lesson): string => {
    const progress = lessonProgress[lesson.id]
    if (!progress) {
      const isUnlocked = lesson.prerequisites.every(prereq => 
        lessonProgress[prereq]?.status === 'completed' || lessonProgress[prereq]?.status === 'mastered'
      )
      return isUnlocked ? 'not_started' : 'locked'
    }
    return progress.status
  }

  const isUnlocked = (lesson: Lesson): boolean => {
    return lesson.prerequisites.every(prereq => 
      lessonProgress[prereq]?.status === 'completed' || lessonProgress[prereq]?.status === 'mastered'
    )
  }

  const levelCards = levels.map(level => {
    const levelLessons = lessonsByLevel[level]
    const completed = levelLessons.filter(l => lessonProgress[l.id]?.status === 'completed' || lessonProgress[l.id]?.status === 'mastered').length
    const mastered = levelLessons.filter(l => lessonProgress[l.id]?.status === 'mastered').length
    const percent = levelLessons.length > 0 ? Math.round((completed / levelLessons.length) * 100) : 0
    const isCurrentLevel = userProgress?.currentLevel === level
    const gradient = isCurrentLevel ? 'linear-gradient(90deg, #fff 0%, #e0e7ff 100%)' : getLevelGradient(level)
    
    const percentClassName = isCurrentLevel ? 'text-white' : 'font-semibold text-gray-900'
    const textClassName = isCurrentLevel ? 'text-white/80' : 'text-gray-500'
    const levelClassName = isCurrentLevel ? 'text-white' : 'text-gray-900'
    const labelClassName = isCurrentLevel ? 'text-white/80' : 'text-gray-500'

    return (
      <Card key={level} variant={isCurrentLevel ? 'gradient' : 'hover'} className="overflow-hidden">
        <div className="p-6">
          <div className="relative">
            {isCurrentLevel && (
              <div className="absolute top-2 right-2">
                <Target className="w-4 h-4 text-primary-500" />
              </div>
            )}
            <div className={`text-3xl font-bold ${levelClassName}`}>
              {level}
            </div>
            <div className={`text-sm ${labelClassName}`}>
              {getLevelLabel(level)}
            </div>
            <div className="mt-3">
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${percent}%`,
                    background: gradient
                  }}
                />
              </div>
              <div className="flex justify-between text-xs mt-1">
                <span className={textClassName}>✓ {completed}</span>
                <span className={percentClassName}>{percent}%</span>
                <span className={textClassName}>★ {mastered}</span>
              </div>
            </div>
          </div>
        </div>
      </Card>
    )
  })

  return (
    <div className="space-y-8 animate-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Curriculum</h1>
          <p className="text-gray-600 mt-1">Structured learning path from beginner to native-level mastery</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => setViewMode('grid')} className={viewMode === 'grid' ? 'bg-primary-600 text-white' : ''}>
            <Layers className="w-4 h-4 mr-1" /> Grid
          </Button>
          <Button variant="outline" size="sm" onClick={() => setViewMode('list')} className={viewMode === 'list' ? 'bg-primary-600 text-white' : ''}>
            <List className="w-4 h-4 mr-1" /> List
          </Button>
        </div>
      </div>

      {/* Progress Overview */}
      <Card variant="glass" className="overflow-hidden">
        <CardContent className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Your Progress by Level</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {levelCards}
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      <Card variant="glass">
        <CardContent className="p-4 sm:p-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <Input
                placeholder="Search lessons..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={selectedLevel}
              onChange={(e) => setSelectedLevel(e.target.value as CEFRLevel | 'all')}
              className="w-full sm:w-40"
              options={[{ value: 'all', label: 'All Levels' }, ...levels.map(l => ({ value: l, label: l }))]}
            />
            <Select
              value={selectedFocusArea}
              onChange={(e) => setSelectedFocusArea(e.target.value as FocusArea | 'all')}
              className="w-full sm:w-48"
              options={[{ value: 'all', label: 'All Topics' }, ...focusAreaOptions.map(f => ({ value: f, label: f.charAt(0).toUpperCase() + f.slice(1) }))]}
            />
            <Button variant="outline" onClick={() => setShowLocked(!showLocked)} className={showLocked ? 'bg-primary-50 border-primary-200 text-primary-700' : ''}>
              <Lock className="w-4 h-4 mr-2" />
              {showLocked ? 'Show Locked' : 'Hide Locked'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Lessons by Level */}
      <div className="space-y-8">
        {levels.map(level => {
          const levelLessons = lessonsByLevel[level]
          if (levelLessons.length === 0) return null

          return (
            <section key={level} className="animate-in stagger-1">
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-white ${getCEFRColor(level)} opacity-90`}>
                  {level}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">{level} - {getLevelLabel(level)}</h2>
                  <p className="text-sm text-gray-500">{levelLessons.length} lessons • {levelLessons.reduce((sum, l) => sum + l.duration, 0)} min total</p>
                </div>
              </div>

              {viewMode === 'grid' ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                  {levelLessons.map(lesson => (
                    <LessonCard
                      key={lesson.id}
                      lesson={lesson}
                      status={getLessonStatus(lesson)}
                      progress={lessonProgress[lesson.id]}
                      isUnlocked={isUnlocked(lesson)}
                    />
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  {levelLessons.map(lesson => (
                    <LessonListItem
                      key={lesson.id}
                      lesson={lesson}
                      status={getLessonStatus(lesson)}
                      progress={lessonProgress[lesson.id]}
                      isUnlocked={isUnlocked(lesson)}
                    />
                  ))}
                </div>
              )}
            </section>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredLessons.length === 0 && (
        <Card variant="gradient" className="text-center py-16">
          <Search className="w-16 h-16 mx-auto text-primary-500/80 mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">No lessons found</h3>
          <p className="text-gray-600 mb-4">Try adjusting your filters or search query</p>
          <Button variant="secondary" onClick={() => { setSearchQuery(''); setSelectedLevel('all'); setSelectedFocusArea('all'); setShowLocked(true) }}>
            Clear Filters
          </Button>
        </Card>
      )}
    </div>
  )
}

// Lesson Card Component
function LessonCard({ lesson, status, progress, isUnlocked }: { lesson: Lesson; status: string; progress?: any; isUnlocked: boolean }) {
  const statusConfig = {
    locked: { color: 'gray', icon: Lock, label: 'Locked', bg: 'bg-gray-100 text-gray-500' },
    not_started: { color: 'gray', icon: ChevronRight, label: 'Not Started', bg: 'bg-gray-100 text-gray-500' },
    in_progress: { color: 'primary', icon: BookOpen, label: 'In Progress', bg: 'bg-primary-100 text-primary-700' },
    completed: { color: 'green', icon: CheckCircle, label: 'Completed', bg: 'bg-green-100 text-green-700' },
    mastered: { color: 'amber', icon: Star, label: 'Mastered', bg: 'bg-amber-100 text-amber-700' },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.not_started
  const StatusIcon = config.icon

  const focusAreaIcons: Record<FocusArea, any> = {
    conversation: Mic,
    grammar: FileText,
    vocabulary: BookOpen,
    pronunciation: Mic,
    writing: PenTool,
    reading: FileText,
    listening: Headphones,
    culture: Globe,
  }
  const FocusIcon = focusAreaIcons[lesson.focusArea] || BookOpen

  return (
    <Link to={`/lesson/${lesson.id}`} className={cn('block', !isUnlocked && 'opacity-50')}>
      <Card variant="hover" className="p-4 flex flex-col h-full">
        <div className="flex items-start gap-3 mb-3">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${getCEFRColor(lesson.level).replace('500', '100')} text-gray-700`}>
            <FocusIcon className="w-5 h-5" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className={`badge text-xs ${getCEFRColor(lesson.level).replace('500', '100')} text-gray-700`}>{lesson.level}</span>
              <span className="badge text-xs bg-gray-100 text-gray-600">{lesson.focusArea}</span>
              {progress?.status === 'mastered' && <span className="badge-accent text-xs">Mastered</span>}
              {!isUnlocked && <span className="badge-warning text-xs">Locked</span>}
            </div>
            <h3 className="font-semibold text-gray-900 mb-1 truncate">{lesson.title}</h3>
            <p className="text-gray-600 text-sm mb-3 line-clamp-2">{lesson.description}</p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="flex items-center gap-3 text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {lesson.duration} min
            </span>
            <span className="flex items-center gap-1 text-primary-600 font-medium">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
              +{lesson.xpReward} XP
            </span>
          </div>
          <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg}`}>
            <StatusIcon className="w-3 h-3" />
            <span className="hidden sm:block">{config.label}</span>
          </div>
        </div>

        {progress?.score && (
          <div className="mt-3">
            <div className="flex justify-between text-xs mb-1">
              <span className="text-gray-500">Progress</span>
              <span className="font-medium text-gray-900">{progress.masteryLevel || progress.score}%</span>
            </div>
            <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full"
                style={{ width: `${progress.masteryLevel || progress.score}%` }}
              />
            </div>
          </div>
        )}
      </Card>
    </Link>
  )
}

// Lesson List Item Component
function LessonListItem({ lesson, status, progress, isUnlocked }: { lesson: Lesson; status: string; progress?: any; isUnlocked: boolean }) {
  const statusConfig = {
    locked: { color: 'gray', icon: Lock, label: 'Locked', bg: 'bg-gray-100 text-gray-500' },
    not_started: { color: 'gray', icon: ChevronRight, label: 'Not Started', bg: 'bg-gray-100 text-gray-500' },
    in_progress: { color: 'primary', icon: BookOpen, label: 'In Progress', bg: 'bg-primary-100 text-primary-700' },
    completed: { color: 'green', icon: CheckCircle, label: 'Completed', bg: 'bg-green-100 text-green-700' },
    mastered: { color: 'amber', icon: Star, label: 'Mastered', bg: 'bg-amber-100 text-amber-700' },
  }

  const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.not_started
  const StatusIcon = config.icon

  const focusAreaIcons: Record<FocusArea, any> = {
    conversation: Mic,
    grammar: FileText,
    vocabulary: BookOpen,
    pronunciation: Mic,
    writing: PenTool,
    reading: FileText,
    listening: Headphones,
    culture: Globe,
  }
  const FocusIcon = focusAreaIcons[lesson.focusArea] || BookOpen

  return (
    <Link to={`/lesson/${lesson.id}`} className={cn('block', !isUnlocked && 'opacity-50')}>
      <Card variant="hover" className="p-4 flex items-center gap-4">
        <div className="w-12 flex items-center justify-center">
          <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium ${config.bg}`}>
            <StatusIcon className="w-3 h-3" />
            {status !== 'locked' && status !== 'not_started' && <span className="hidden sm:block">{config.label}</span>}
          </span>
        </div>

        <div className="w-24 flex flex-col items-center justify-center text-center">
          <span className={`badge text-xs ${getCEFRColor(lesson.level).replace('500', '100')} text-gray-700`}>{lesson.level}</span>
          <span className="badge text-xs bg-gray-100 text-gray-600 mt-1">{lesson.focusArea}</span>
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{lesson.title}</h3>
          <p className="text-gray-600 text-sm truncate">{lesson.description}</p>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span className="flex items-center gap-1">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {lesson.duration} min
          </span>
          <span className="flex items-center gap-1 text-primary-600 font-medium">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            +{lesson.xpReward} XP
          </span>
        </div>

        <ArrowRight className="w-5 h-5 text-gray-400 flex-shrink-0" />
      </Card>
    </Link>
  )
}

export default CurriculumPage