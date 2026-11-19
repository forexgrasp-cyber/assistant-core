/** Type definitions for the Language Tutor frontend */

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  nativeLanguage: string;
  targetLanguage: string;
  cefrLevel: CEFRLevel;
  streak: number;
  xp: number;
  createdAt: string;
}

export type CEFRLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';

export const CEFR_LEVELS: CEFRLevel[] = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];

export const CEFR_LABELS: Record<CEFRLevel, string> = {
  A1: 'Beginner',
  A2: 'Elementary',
  B1: 'Intermediate',
  B2: 'Upper Intermediate',
  C1: 'Advanced',
  C2: 'Proficient',
};

export interface Language {
  code: string;
  name: string;
  nativeName: string;
  flag: string;
  rtl?: boolean;
}

export interface Lesson {
  id: string;
  title: string;
  description: string;
  language: string;
  level: CEFRLevel;
  focusArea: FocusArea;
  duration: number; // minutes
  xpReward: number;
  content: LessonContent[];
  prerequisites?: string[];
  tags: string[];
  order: number;
}

export type FocusArea =
  | 'conversation'
  | 'grammar'
  | 'vocabulary'
  | 'pronunciation'
  | 'writing'
  | 'reading'
  | 'listening'
  | 'culture';

export const FOCUS_AREAS: { value: FocusArea; label: string; icon: string }[] = [
  { value: 'conversation', label: 'Conversation', icon: 'MessageSquare' },
  { value: 'grammar', label: 'Grammar', icon: 'BookOpen' },
  { value: 'vocabulary', label: 'Vocabulary', icon: 'FileText' },
  { value: 'pronunciation', label: 'Pronunciation', icon: 'Mic' },
  { value: 'writing', label: 'Writing', icon: 'PenTool' },
  { value: 'reading', label: 'Reading', icon: 'Book' },
  { value: 'listening', label: 'Listening', icon: 'Headphones' },
  { value: 'culture', label: 'Culture', icon: 'Globe' },
];

export type ContentType =
  | 'dialogue'
  | 'exercise'
  | 'video'
  | 'audio'
  | 'text'
  | 'quiz'
  | 'pronunciation'
  | 'writing'
  | 'flashcard'
  // Focus-area labels are also used as content kinds by the curriculum pages.
  | 'conversation'
  | 'vocabulary'
  | 'listening'
  | 'reading'
  | 'grammar'
  | 'culture';

export interface LessonContent {
  id: string;
  type: ContentType;
  title: string;
  data: Record<string, unknown>;
  order: number;
  estimatedTime: number;
  required?: boolean;
  focusArea?: FocusArea;
  xpReward?: number;
}

export interface DialogueContent {
  speaker: 'tutor' | 'user' | 'native';
  text: string;
  translation?: string;
  audioUrl?: string;
  lipSyncData?: LipSyncFrame[];
}

export interface ExerciseContent {
  question: string;
  type: 'multiple_choice' | 'fill_blank' | 'match' | 'order' | 'speak' | 'write';
  options?: string[];
  correctAnswer: string | string[];
  explanation?: string;
  hints?: string[];
  audioUrl?: string;
}

export interface VideoContent {
  url: string;
  title: string;
  duration: number;
  subtitles?: Subtitle[];
  transcript?: string;
}

export interface AudioContent {
  url: string;
  title: string;
  duration: number;
  transcript?: string;
  speed?: number;
}

export interface QuizContent {
  questions: QuizQuestion[];
  passingScore: number;
  timeLimit?: number;
}

export interface QuizQuestion {
  id: string;
  question: string;
  type: 'single' | 'multiple' | 'true_false' | 'input';
  options?: string[];
  correctAnswer: string | string[];
  explanation?: string;
}

export interface PronunciationContent {
  targetText: string;
  phonemes: Phoneme[];
  audioUrl: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface Phoneme {
  symbol: string;
  sound: string;
  example: string;
  mouthShape: string;
}

export interface WritingContent {
  prompt: string;
  minWords?: number;
  maxWords?: number;
  template?: string;
  criteria: WritingCriteria[];
  examples?: string[];
}

export interface WritingCriteria {
  name: string;
  description: string;
  weight: number;
}

export interface FlashcardContent {
  front: string;
  back: string;
  frontAudio?: string;
  backAudio?: string;
  image?: string;
  tags?: string[];
}

export interface Subtitle {
  start: number;
  end: number;
  text: string;
  translation?: string;
}

export interface LipSyncFrame {
  time: number;
  viseme: string;
  intensity: number;
}

export interface LessonProgress {
  lessonId: string;
  userId: string;
  status: 'not_started' | 'in_progress' | 'completed' | 'mastered';
  currentContentIndex: number;
  completedContent: string[];
  score?: number;
  attempts: number;
  timeSpent: number; // seconds
  lastAccessed: string;
  masteryLevel: number; // 0-100
}

export interface UserProgress {
  userId: string;
  language: string;
  currentLevel: CEFRLevel;
  xp: number;
  levelProgress: number; // 0-100
  streak: number;
  longestStreak: number;
  totalTimeSpent: number;
  lessonsCompleted: number;
  lessonsMastered: number;
  focusAreaProgress: Record<FocusArea, number>;
  weakAreas: FocusArea[];
  strongAreas: FocusArea[];
  achievements: Achievement[];
  dailyGoal: DailyGoal;
  weeklyStats: WeeklyStats;
}

export interface DailyGoal {
  targetMinutes: number;
  completedMinutes: number;
  streak: number;
  lastCompleted: string | null;
}

export interface WeeklyStats {
  weekStart: string;
  minutes: number;
  lessons: number;
  xp: number;
  streakDays: number;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  category: 'streak' | 'lessons' | 'xp' | 'mastery' | 'social' | 'special';
  unlockedAt?: string;
  progress?: number;
  target?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  type: 'text' | 'audio' | 'mixed' | 'exercise' | 'correction' | 'explanation';
  timestamp: string;
  metadata?: {
    audioUrl?: string;
    duration?: number;
    transcript?: string;
    confidence?: number;
    corrections?: Correction[];
    exerciseId?: string;
    language?: string;
  };
}

export interface Correction {
  original: string;
  corrected: string;
  type: 'grammar' | 'vocabulary' | 'pronunciation' | 'spelling' | 'style';
  explanation: string;
  position: { start: number; end: number };
  severity: 'minor' | 'major' | 'critical';
}

export interface TutorResponse {
  /** The tutor's reply text. */
  message: string;
  suggestions?: string[];
  corrections?: Correction[];
  nextExercise?: LessonContent;
  progressUpdate?: Partial<UserProgress>;
  audioUrl?: string;
}

export interface SpeechRecognitionResult {
  transcript: string;
  confidence: number;
  isFinal: boolean;
  language: string;
}

export interface PronunciationScore {
  overall: number; // 0-100
  phonemes: PhonemeScore[];
  fluency: number;
  intonation: number;
  feedback: string;
}

export interface PhonemeScore {
  phoneme: string;
  score: number;
  expected: string;
  actual: string;
}

export interface SessionState {
  sessionId: string;
  lessonId: string;
  startTime: string;
  messages: ChatMessage[];
  currentExercise?: LessonContent;
  userInput: string;
  isRecording: boolean;
  isProcessing: boolean;
  tutorState: 'listening' | 'thinking' | 'speaking' | 'waiting';
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export type ViewMode = 'dashboard' | 'curriculum' | 'lesson' | 'practice' | 'progress' | 'settings' | 'generator';

export interface AppState {
  view: ViewMode;
  sidebarOpen: boolean;
  currentLesson?: Lesson;
  currentContentIndex: number;
  session: SessionState | null;
}