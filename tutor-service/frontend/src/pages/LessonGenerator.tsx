import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Sparkles,
  Wand2 as MagicWand,
  Youtube,
  BookOpen,
  Zap,
  Save,
  Eye,
  Search,
  Layers,
  Target,
  Trophy,
  Clock,
  Globe,
  Users,
  Crown,
  Sparkle,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Info,
  Plus,
  Minus,
  Copy,
  Download,
  Share2,
  Trash2,
  Edit,
  Settings,
  RefreshCw,
  Brain,
  Film,
  FileText,
  Globe as GlobeIcon,
  Layers as LayersIcon,
  Palette,
  Wand2,
  Zap as ZapIcon,
  BarChart,
  Bookmark,
  Heart,
  Star,
  Flag,
  Volume2,
  Mic,
  PenTool,
  Headphones,
  Image,
  MessageSquare,
  Bot,
  User,
  Shield,
  Lock,
  Unlock,
  Key,
  Cloud,
  Server,
  Database,
  Network,
  Wifi,
  Bluetooth,
  Battery,
  Cpu,
  HardDrive,
  Monitor,
  Smartphone,
  Tablet,
  LayoutDashboard,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  Home,
  ArrowUpRight,
  ExternalLink,
  Filter,
  SortAsc,
  SortDesc,
  Grid,
  List,
  MapPin,
  Calendar,
  Bell,
  Mail,
  Phone,
  User as UserIcon,
  LogOut,
  Moon,
  Sun,
  Palette as PaletteIcon,
  Languages as Language,
  Mic2,
  Keyboard,
  RotateCcw,
  Maximize2,
  Minimize2,
  HelpCircle,
  HelpCircle as QuestionCircle,
  Lightbulb,
  Play,
  Database as DatabaseIcon,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/Select';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { Label } from '@/components/ui/Label';
import { Slider } from '@/components/ui/Slider';
import { useTutorStore } from '@/stores/tutorStore';
import { useAuth } from '@/contexts/AuthContext';
import { api, GenerateLessonRequest, GenerateLessonResponse, LessonBlueprint, ContentAsset, AgeGroup, GamificationLevel, ContentSource, FocusArea, CEFRLevel, SearchContentRequest, SearchContentResponse, GenerateCurriculumRequest, AvailableSourcesResponse } from '@/lib/api';
import { cn, formatDuration } from '@/lib/utils';

// Icon component map for dynamic rendering
const iconComponents: Record<string, React.ComponentType<{ className?: string }>> = {
  Sparkles,
  MagicWand,
  Youtube,
  BookOpen,
  Zap,
  Save,
  Eye,
  Search,
  Layers,
  Target,
  Trophy,
  Clock,
  Globe,
  Users,
  Crown,
  Sparkle,
  ArrowRight,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Info,
  Plus,
  Minus,
  Copy,
  Download,
  Share2,
  Trash2,
  Edit,
  Settings,
  RefreshCw,
  Brain,
  Film,
  FileText,
  GlobeIcon,
  LayersIcon,
  Palette,
  Wand2,
  ZapIcon,
  BarChart,
  Bookmark,
  Heart,
  Star,
  Flag,
  Volume2,
  Mic,
  PenTool,
  Headphones,
  Image,
  MessageSquare,
  Bot,
  User,
  Shield,
  Lock,
  Unlock,
  Key,
  Cloud,
  Server,
  Database: DatabaseIcon,
  Network,
  Wifi,
  Bluetooth,
  Battery,
  Cpu,
  HardDrive,
  Monitor,
  Smartphone,
  Tablet,
  LayoutDashboard,
  Menu,
  X,
  ChevronLeft,
  ChevronRight,
  Home,
  ArrowUpRight,
  ExternalLink,
  Filter,
  SortAsc,
  SortDesc,
  Grid,
  List,
  MapPin,
  Calendar,
  Bell,
  Mail,
  Phone,
  UserIcon,
  LogOut,
  Moon,
  Sun,
  PaletteIcon,
  Language,
  Mic2,
  Keyboard,
  RotateCcw,
  Maximize2,
  Minimize2,
  HelpCircle,
  QuestionCircle: HelpCircle,
  Lightbulb,
  Play,
};

function Icon({ name, className = 'h-4 w-4' }: { name: string; className?: string }) {
  const Component = iconComponents[name] || FileText;
  return <Component className={className} />;
}

const AGE_GROUPS: { value: AgeGroup; label: string; description: string; emoji: string }[] = [
  { value: 'child', label: 'Child (5-12)', description: 'Playful, games, songs, stories', emoji: '👶' },
  { value: 'teen', label: 'Teen (13-17)', description: 'Relatable, social media, music, gaming', emoji: '🧑' },
  { value: 'young_adult', label: 'Young Adult (18-25)', description: 'Practical, travel, career, university', emoji: '🎓' },
  { value: 'adult', label: 'Adult (26-55)', description: 'Professional, work, business, daily life', emoji: '👔' },
  { value: 'senior', label: 'Senior (55+)', description: 'Patient, clear, travel, family, hobbies', emoji: '👴' },
];

const GAMIFICATION_LEVELS: { value: GamificationLevel; label: string; description: string; features: string[] }[] = [
  { value: 'none', label: 'None', description: 'Pure learning, no game elements', features: [] },
  { value: 'light', label: 'Light', description: 'Progress bars, XP rewards', features: ['Progress bars', 'XP rewards'] },
  { value: 'medium', label: 'Medium', description: 'Badges, streaks, leaderboards', features: ['Badges', 'Streaks', 'Leaderboards'] },
  { value: 'full', label: 'Full', description: 'Quests, avatar, virtual world, AR', features: ['Quests', 'Avatar', 'Virtual world', 'AR elements'] },
];

const FOCUS_AREA_OPTIONS: { value: FocusArea; label: string; icon: string; description: string }[] = [
  { value: 'conversation', label: 'Conversation', icon: 'MessageSquare', description: 'Speaking and dialogue practice' },
  { value: 'grammar', label: 'Grammar', icon: 'BookOpen', description: 'Grammar rules and patterns' },
  { value: 'vocabulary', label: 'Vocabulary', icon: 'FileText', description: 'Word building and retention' },
  { value: 'pronunciation', label: 'Pronunciation', icon: 'Mic', description: 'Sound mastery and accent' },
  { value: 'reading', label: 'Reading', icon: 'BookOpen', description: 'Comprehension and fluency' },
  { value: 'listening', label: 'Listening', icon: 'Headphones', description: 'Audio understanding skills' },
  { value: 'writing', label: 'Writing', icon: 'PenTool', description: 'Written expression practice' },
  { value: 'culture', label: 'Culture', icon: 'Globe', description: 'Cultural context and customs' },
];

const CONTENT_SOURCE_ICONS: Record<ContentSource, string> = {
  llm_generated: 'Brain',
  youtube: 'Youtube',
  textbook: 'BookOpen',
  api_curriculum: 'Layers',
  user_created: 'User',
  community: 'Users',
  ai_curated: 'Sparkles',
};

const CONTENT_TYPE_ICONS: Record<string, string> = {
  dialogue: 'MessageSquare',
  exercise: 'FileText',
  video: 'Film',
  audio: 'Volume2',
  text: 'FileText',
  quiz: 'HelpCircle',
  pronunciation: 'Mic',
  writing: 'PenTool',
  flashcard: 'Layers',
  reading: 'BookOpen',
};

interface LessonGeneratorPageProps {}

export function LessonGeneratorPage() {
  const { user } = useAuth();
  const { user: tutorUser, targetLanguage, cefrLevel } = useTutorStore();
  
  const [activeTab, setActiveTab] = useState<'generate' | 'search' | 'curriculum' | 'sources'>('generate');
  
  const [generateRequest, setGenerateRequest] = useState<GenerateLessonRequest>({
    focus_area: 'conversation',
    age_group: 'adult',
    gamification: 'medium',
    duration_minutes: tutorUser?.dailyGoal?.targetMinutes || 15,
    language: targetLanguage || 'es',
  });
  const [generatedLesson, setGeneratedLesson] = useState<LessonBlueprint | null>(null);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);
  
  const [searchRequest, setSearchRequest] = useState<SearchContentRequest>({
    language: targetLanguage || 'es',
    level: (cefrLevel as CEFRLevel) || 'A1',
    focus_area: 'conversation',
    topic: '',
    age_groups: ['adult'],
    max_duration_minutes: 30,
    max_results: 10,
    gamification: 'medium',
    content_types: [],
    sources: ['youtube', 'textbook', 'api_curriculum'],
  });
  const [searchResults, setSearchResults] = useState<ContentAsset[]>([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [sourcesSearched, setSourcesSearched] = useState<string[]>([]);
  
  const [curriculumRequest, setCurriculumRequest] = useState<GenerateCurriculumRequest>({
    language: targetLanguage || 'es',
    age_group: 'adult',
    gamification: 'medium',
    levels: ['A1', 'A2', 'B1', 'B2'],
    focus_areas: ['conversation', 'grammar', 'vocabulary', 'pronunciation'],
  });
  const [generatedCurriculum, setGeneratedCurriculum] = useState<LessonBlueprint[]>([]);
  const [curriculumLoading, setCurriculumLoading] = useState(false);
  const [curriculumError, setCurriculumError] = useState<string | null>(null);
  
  const [sourcesInfo, setSourcesInfo] = useState<AvailableSourcesResponse | null>(null);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  
  const [showLessonPreview, setShowLessonPreview] = useState(false);
  const [previewLessonData, setPreviewLessonData] = useState<LessonBlueprint | null>(null);
  const [showAssetDetail, setShowAssetDetail] = useState<ContentAsset | null>(null);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);
  const [showCurriculumDetail, setShowCurriculumDetail] = useState<LessonBlueprint | null>(null);

  useEffect(() => {
    loadSources();
  }, []);

  const loadSources = async () => {
    setSourcesLoading(true);
    try {
      const data = await api.getAvailableSources();
      setSourcesInfo(data);
    } catch (error) {
      console.error('Failed to load sources:', error);
    } finally {
      setSourcesLoading(false);
    }
  };

  const handleGenerateLesson = async (preview = false) => {
    if (!user) return;
    setGenerateLoading(true);
    setGenerateError(null);
    try {
      const response = preview 
        ? await api.previewLesson(generateRequest)
        : await api.generateLesson(generateRequest);
      if (response.status === 'error') throw new Error(response.message);
      setGeneratedLesson(response.blueprint);
      if (preview) {
        setPreviewLessonData(response.blueprint);
        setShowLessonPreview(true);
      }
    } catch (error) {
      setGenerateError(error instanceof Error ? error.message : 'Generation failed');
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleSearchContent = async () => {
    if (!searchRequest.topic.trim()) {
      setSearchError('Please enter a topic to search');
      return;
    }
    setSearchLoading(true);
    setSearchError(null);
    try {
      const response = await api.searchContent(searchRequest);
      setSearchResults(response.assets);
      setSourcesSearched(response.sources_searched);
    } catch (error) {
      setSearchError(error instanceof Error ? error.message : 'Search failed');
    } finally {
      setSearchLoading(false);
    }
  };

  const handleGenerateCurriculum = async () => {
    if (!user) return;
    setCurriculumLoading(true);
    setCurriculumError(null);
    try {
      const response = await api.generateCurriculum(curriculumRequest);
      setGeneratedCurriculum(response.lessons);
    } catch (error) {
      setCurriculumError(error instanceof Error ? error.message : 'Curriculum generation failed');
    } finally {
      setCurriculumLoading(false);
    }
  };

  const handleSaveLesson = async () => {
    if (!generatedLesson || !user) return;
    setShowSaveConfirm(false);
  };

  const getContentTypeIcon = (type: string) => CONTENT_TYPE_ICONS[type] || 'FileText';
  const getSourceIcon = (source: ContentSource) => CONTENT_SOURCE_ICONS[source] || 'Database';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                AI Lesson Generator
              </h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">
                Create personalized, multimedia-rich lessons tailored to your learning gaps
              </p>
            </div>
            <Badge variant="outline" className="gap-1">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              AI Ready
            </Badge>
          </div>
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4 bg-gray-100 dark:bg-gray-800 p-1 rounded-xl">
            <TabsTrigger value="generate" className="gap-2"><MagicWand className="h-4 w-4" /> Generate Lesson</TabsTrigger>
            <TabsTrigger value="search" className="gap-2"><Search className="h-4 w-4" /> Search Content</TabsTrigger>
            <TabsTrigger value="curriculum" className="gap-2"><Layers className="h-4 w-4" /> Generate Curriculum</TabsTrigger>
            <TabsTrigger value="sources" className="gap-2"><DatabaseIcon className="h-4 w-4" /> Sources</TabsTrigger>
          </TabsList>

          {/* Generate Lesson Tab */}
          <TabsContent value="generate" className="mt-6 animate-fade-in">
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="lg:col-span-1 space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2"><MagicWand className="h-5 w-5 text-blue-600" /> Lesson Configuration</CardTitle>
                    <CardDescription>Customize your AI-generated lesson</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-5">
                    <div className="space-y-3">
                      <Label className="flex items-center gap-2"><Globe className="h-4 w-4" /> Language</Label>
                      <Select value={generateRequest.language} onValueChange={(v) => setGenerateRequest({...generateRequest, language: v})}>
                        <SelectTrigger><SelectValue placeholder="Select language" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="es">Spanish (Español)</SelectItem>
                          <SelectItem value="en">English</SelectItem>
                          <SelectItem value="fr">French (Français)</SelectItem>
                          <SelectItem value="de">German (Deutsch)</SelectItem>
                          <SelectItem value="it">Italian (Italiano)</SelectItem>
                          <SelectItem value="pt">Portuguese (Português)</SelectItem>
                          <SelectItem value="ja">Japanese (日本語)</SelectItem>
                          <SelectItem value="ko">Korean (한국어)</SelectItem>
                          <SelectItem value="zh">Chinese (中文)</SelectItem>
                          <SelectItem value="ar">Arabic (العربية)</SelectItem>
                          <SelectItem value="hi">Hindi (हिन्दी)</SelectItem>
                          <SelectItem value="ru">Russian (Русский)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-3">
                      <Label className="flex items-center gap-2"><Target className="h-4 w-4" /> Focus Area</Label>
                      <Select value={generateRequest.focus_area || 'conversation'} onValueChange={(v) => setGenerateRequest({...generateRequest, focus_area: v as FocusArea})}>
                        <SelectTrigger><SelectValue placeholder="Select focus area" /></SelectTrigger>
                        <SelectContent>
                          {FOCUS_AREA_OPTIONS.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              <div className="flex items-center gap-2">
                                <Icon name={opt.icon} className="h-4 w-4" />
                                <div className="flex flex-col"><span>{opt.label}</span><span className="text-xs text-gray-500">{opt.description}</span></div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-3">
                      <Label className="flex items-center gap-2"><Users className="h-4 w-4" /> Age Group</Label>
                      <Select value={generateRequest.age_group} onValueChange={(v) => setGenerateRequest({...generateRequest, age_group: v as AgeGroup})}>
                        <SelectTrigger><SelectValue placeholder="Select age group" /></SelectTrigger>
                        <SelectContent>
                          {AGE_GROUPS.map((group) => (
                            <SelectItem key={group.value} value={group.value}>
                              <div className="flex items-center gap-2">
                                <span className="text-2xl">{group.emoji}</span>
                                <div className="flex flex-col"><span>{group.label}</span><span className="text-xs text-gray-500">{group.description}</span></div>
                              </div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-3">
                      <Label className="flex items-center gap-2"><Trophy className="h-4 w-4" /> Gamification</Label>
                      <Select value={generateRequest.gamification} onValueChange={(v) => setGenerateRequest({...generateRequest, gamification: v as GamificationLevel})}>
                        <SelectTrigger><SelectValue placeholder="Select gamification level" /></SelectTrigger>
                        <SelectContent>
                          {GAMIFICATION_LEVELS.map((level) => (
                            <SelectItem key={level.value} value={level.value}>
                              <div className="flex flex-col"><span>{level.label}</span><span className="text-xs text-gray-500">{level.description}</span></div>
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-3">
                      <Label className="flex items-center gap-2"><Clock className="h-4 w-4" /> Duration: {generateRequest.duration_minutes || 15} minutes</Label>
                      <Slider value={[generateRequest.duration_minutes || 15]} onValueChange={([v]) => setGenerateRequest({...generateRequest, duration_minutes: v})} max={120} min={5} step={5} className="w-full" />
                      <div className="flex justify-between text-xs text-gray-500"><span>5 min</span><span>120 min</span></div>
                    </div>
                    <div className="space-y-3 pt-4 border-t">
                      <Button className="w-full justify-center gap-2" size="lg" onClick={() => handleGenerateLesson(true)} disabled={generateLoading}>
                        {generateLoading ? <> <Loader2 className="h-4 w-4 animate-spin" /> Generating Preview... </> : <> <Eye className="h-4 w-4" /> Preview Lesson </>}
                      </Button>
                      <Button className="w-full justify-center gap-2" size="lg" variant="default" onClick={() => handleGenerateLesson(false)} disabled={generateLoading}>
                        {generateLoading ? <> <Loader2 className="h-4 w-4 animate-spin" /> Generating & Saving... </> : <> <MagicWand className="h-4 w-4" /> Generate & Save </>}
                      </Button>
                    </div>
                    {generateError && (
                      <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 flex-shrink-0" /> {generateError}
                      </div>
                    )}
                  </CardContent>
                </Card>
                <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-3">
                      <Lightbulb className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
                      <div className="text-sm text-blue-800 dark:text-blue-200 space-y-2">
                        <p><strong>Tips for better lessons:</strong></p>
                        <ul className="list-disc list-inside space-y-1">
                          <li>Be specific about your focus area</li>
                          <li>Match age group to your learning style</li>
                          <li>Higher gamification = more engagement</li>
                          <li>AI uses your learning gaps automatically</li>
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <div className="lg:col-span-2 space-y-6">
                {generatedLesson ? (
                  <div className="space-y-6 animate-slide-up">
                    <Card className="border-blue-200 dark:border-blue-800 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20">
                      <CardContent className="p-6">
                        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                          <div>
                            <div className="flex items-center gap-3 mb-2">
                              <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium">{generatedLesson.level}</span>
                              <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full text-sm font-medium">{generatedLesson.focus_area}</span>
                              <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm font-medium">{generatedLesson.gamification_level}</span>
                              <span className="px-3 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded-full text-sm font-medium">{generatedLesson.target_age_groups[0] || 'adult'}</span>
                            </div>
                            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">{generatedLesson.title}</h2>
                            <p className="text-gray-600 dark:text-gray-400">{generatedLesson.description}</p>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                            <div className="flex items-center gap-1"><Clock className="h-4 w-4" /> <span>{formatDuration(generatedLesson.duration_minutes)}</span></div>
                            <div className="flex items-center gap-1"><Trophy className="h-4 w-4" /> <span>{generatedLesson.xp_reward} XP</span></div>
                            <div className="flex items-center gap-1"><Layers className="h-4 w-4" /> <span>{generatedLesson.content_assets.length} activities</span></div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardHeader><CardTitle className="flex items-center gap-2"><Target className="h-5 w-5" /> Learning Objectives</CardTitle></CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {generatedLesson.learning_objectives.map((obj, i) => (
                            <li key={i} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                              <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 flex items-center justify-center text-sm font-medium">{i + 1}</span>
                              <span className="text-gray-700 dark:text-gray-300">{obj}</span>
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                    <div className="grid md:grid-cols-2 gap-4">
                      {generatedLesson.vocabulary_targets.length > 0 && (
                        <Card>
                          <CardHeader><CardTitle className="flex items-center gap-2"><BookOpen className="h-5 w-5" /> Vocabulary Targets</CardTitle></CardHeader>
                          <CardContent>
                            <div className="flex flex-wrap gap-2">
                              {generatedLesson.vocabulary_targets.map((word, i) => (
                                <Badge key={i} variant="secondary" className="gap-1">{word} <Copy className="h-3 w-3 cursor-pointer hover:text-blue-600" onClick={() => navigator.clipboard.writeText(word)} title="Copy" /></Badge>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                      {generatedLesson.grammar_points.length > 0 && (
                        <Card>
                          <CardHeader><CardTitle className="flex items-center gap-2"><FileText className="h-5 w-5" /> Grammar Points</CardTitle></CardHeader>
                          <CardContent>
                            <div className="flex flex-wrap gap-2">
                              {generatedLesson.grammar_points.map((point, i) => (
                                <Badge key={i} variant="outline">{point}</Badge>
                              ))}
                            </div>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      {generatedLesson.pronunciation_focus.length > 0 && (
                        <Card>
                          <CardHeader><CardTitle className="flex items-center gap-2"><Mic className="h-5 w-5" /> Pronunciation Focus</CardTitle></CardHeader>
                          <CardContent>
                            <ul className="space-y-1">
                              {generatedLesson.pronunciation_focus.map((sound, i) => (
                                <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" /> {sound}</li>
                              ))}
                            </ul>
                          </CardContent>
                        </Card>
                      )}
                      {generatedLesson.cultural_notes.length > 0 && (
                        <Card>
                          <CardHeader><CardTitle className="flex items-center gap-2"><Globe className="h-5 w-5" /> Cultural Notes</CardTitle></CardHeader>
                          <CardContent>
                            <ul className="space-y-1">
                              {generatedLesson.cultural_notes.map((note, i) => (
                                <li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2"><MapPin className="h-4 w-4 text-orange-500" /> {note}</li>
                              ))}
                            </ul>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                    <Card>
                      <CardHeader><CardTitle className="flex items-center gap-2"><Layers className="h-5 w-5" /> Lesson Activities ({generatedLesson.content_assets.length})</CardTitle></CardHeader>
                      <CardContent>
                        <div className="space-y-3">
                          {generatedLesson.content_assets.map((asset, index) => (
                            <div key={asset.id} className="group p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700 transition-colors">
                              <div className="flex items-start gap-4">
                                <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                                  <Icon name={getContentTypeIcon(asset.type)} className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-3 mb-1">
                                    <h4 className="font-medium text-gray-900 dark:text-white">{asset.title}</h4>
                                    <Badge variant="outline" className="text-xs">{asset.type}</Badge>
                                    <Badge variant="secondary" className="text-xs flex items-center gap-1"><Icon name={getSourceIcon(asset.source)} className="h-3 w-3" /> {asset.source.replace('_', ' ')}</Badge>
                                    <span className="text-sm text-gray-500 ml-auto">~{Math.round(asset.duration_seconds / 60)} min</span>
                                  </div>
                                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{asset.description}</p>
                                  <div className="flex items-center gap-2 text-xs text-gray-500">
                                    {asset.tags.slice(0, 5).map((tag, i) => (
                                      <Badge key={i} variant="outline" className="text-xs h-5 px-2">{tag}</Badge>
                                    ))}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <Button variant="ghost" size="icon" className="h-8 w-8"><Eye className="h-4 w-4" /></Button>
                                  <Button variant="ghost" size="icon" className="h-8 w-8"><Play className="h-4 w-4" /></Button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                    <div className="flex items-center gap-4 pt-4 border-t">
                      <Button onClick={() => setShowLessonPreview(true)} variant="outline"><Eye className="h-4 w-4 mr-2" /> Full Preview</Button>
                      <Button onClick={handleSaveLesson} disabled={!user}><Save className="h-4 w-4 mr-2" /> Save to Curriculum</Button>
                      <Button variant="outline" onClick={() => setGeneratedLesson(null)}><RotateCcw className="h-4 w-4 mr-2" /> Generate Another</Button>
                    </div>
                  </div>
                ) : (
                  <Card className="border-dashed border-2 border-gray-200 dark:border-gray-700 h-[500px] flex items-center justify-center">
                    <CardContent className="text-center p-12">
                      <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 flex items-center justify-center"><MagicWand className="h-12 w-12 text-blue-600 dark:text-blue-400" /></div>
                      <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">Ready to Create Your Perfect Lesson?</h3>
                      <p className="text-gray-600 dark:text-gray-400 mb-6 max-w-md mx-auto">Configure your preferences on the left and click "Preview Lesson" to see what AI creates for you. The generator uses your learning gaps, interests, and goals to build a personalized experience.</p>
                      <div className="flex flex-wrap justify-center gap-4 text-sm text-gray-500">
                        <span className="flex items-center gap-1"><Icon name="Brain" className="h-4 w-4" /> LLM-Generated Content</span>
                        <span className="flex items-center gap-1"><Icon name="Youtube" className="h-4 w-4" /> YouTube Videos</span>
                        <span className="flex items-center gap-1"><Icon name="BookOpen" className="h-4 w-4" /> Textbook Content</span>
                        <span className="flex items-center gap-1"><Icon name="Layers" className="h-4 w-4" /> API Curriculums</span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          {/* Search Content Tab */}
          <TabsContent value="search" className="mt-6 animate-fade-in">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><Search className="h-5 w-5" /> Search Multimedia Content</CardTitle>
                  <CardDescription>Find videos, textbook chapters, and curriculum content from multiple sources</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid lg:grid-cols-4 gap-4 mb-4">
                    <div className="space-y-2"><Label>Language</Label><Select value={searchRequest.language} onValueChange={(v) => setSearchRequest({...searchRequest, language: v})}><SelectTrigger><SelectValue placeholder="Language" /></SelectTrigger><SelectContent><SelectItem value="es">Spanish</SelectItem><SelectItem value="en">English</SelectItem><SelectItem value="fr">French</SelectItem><SelectItem value="de">German</SelectItem><SelectItem value="it">Italian</SelectItem><SelectItem value="pt">Portuguese</SelectItem><SelectItem value="ja">Japanese</SelectItem><SelectItem value="ko">Korean</SelectItem><SelectItem value="zh">Chinese</SelectItem></SelectContent></Select></div>
                    <div className="space-y-2"><Label>CEFR Level</Label><Select value={searchRequest.level} onValueChange={(v) => setSearchRequest({...searchRequest, level: v as CEFRLevel})}><SelectTrigger><SelectValue placeholder="Level" /></SelectTrigger><SelectContent>{['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].map(l => <SelectItem key={l} value={l}>{l}</SelectItem>)}</SelectContent></Select></div>
                    <div className="space-y-2"><Label>Focus Area</Label><Select value={searchRequest.focus_area} onValueChange={(v) => setSearchRequest({...searchRequest, focus_area: v as FocusArea})}><SelectTrigger><SelectValue placeholder="Focus" /></SelectTrigger><SelectContent>{FOCUS_AREA_OPTIONS.map(o => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}</SelectContent></Select></div>
                    <div className="space-y-2"><Label>Age Group</Label><Select value={searchRequest.age_groups[0]} onValueChange={(v) => setSearchRequest({...searchRequest, age_groups: [v as AgeGroup]})}><SelectTrigger><SelectValue placeholder="Age" /></SelectTrigger><SelectContent>{AGE_GROUPS.map(g => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div className="grid lg:grid-cols-3 gap-4 mb-4">
                    <div className="space-y-2 lg:col-span-2"><Label>Topic / Keywords</Label><Input placeholder="e.g., greetings, past tense, restaurant vocabulary..." value={searchRequest.topic} onChange={(e) => setSearchRequest({...searchRequest, topic: e.target.value})} /></div>
                    <div className="space-y-2"><Label>Max Duration (min)</Label><Input type="number" value={searchRequest.max_duration_minutes} onChange={(e) => setSearchRequest({...searchRequest, max_duration_minutes: parseInt(e.target.value)})} min={1} max={120} /></div>
                  </div>
                  <div className="flex flex-wrap gap-4 mb-4">
                    <div className="flex items-center gap-2"><Label className="mb-0">Sources:</Label>{(['youtube', 'textbook', 'api_curriculum'] as ContentSource[]).map(source => (<label key={source} className="flex items-center gap-1 cursor-pointer"><input type="checkbox" checked={searchRequest.sources?.includes(source)} onChange={(e) => setSearchRequest({...searchRequest, sources: e.target.checked ? [...(searchRequest.sources || []), source] : (searchRequest.sources || []).filter(s => s !== source)})} className="rounded border-gray-300" /><span className="text-sm capitalize">{source.replace('_', ' ')}</span></label>))}</div>
                  </div>
                  <div className="flex gap-3">
                    <Button onClick={handleSearchContent} disabled={searchLoading || !searchRequest.topic.trim()} className="flex-1">{searchLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Search className="h-4 w-4 mr-2" />} Search Content</Button>
                    <Button variant="outline" onClick={() => setSearchRequest({...searchRequest, topic: '', age_groups: ['adult']})}><RotateCcw className="h-4 w-4 mr-2" /> Clear</Button>
                  </div>
                  {searchError && (<div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm flex items-center gap-2"><AlertCircle className="h-4 w-4 flex-shrink-0" /> {searchError}</div>)}
                </CardContent>
              </Card>
              {searchResults.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between"><h3 className="text-lg font-semibold">Results ({searchResults.length} assets from {sourcesSearched.join(', ')})</h3><Badge variant="outline">{searchResults.length} found</Badge></div>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {searchResults.map((asset) => (
                      <Card key={asset.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => setShowAssetDetail(asset)}>
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center"><Icon name={getContentTypeIcon(asset.type)} className="h-6 w-6 text-blue-600 dark:text-blue-400" /></div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1"><h4 className="font-medium text-gray-900 dark:text-white truncate">{asset.title}</h4><Badge variant="outline" className="text-xs whitespace-nowrap">{asset.type}</Badge></div>
                              <div className="flex items-center gap-2 text-xs text-gray-500 mb-2"><Badge variant="secondary" className="gap-1 h-5 px-2"><Icon name={getSourceIcon(asset.source)} className="h-3 w-3" /> {asset.source.replace('_', ' ')}</Badge><span>~{Math.round(asset.duration_seconds / 60)} min</span>{asset.metadata.difficulty && <span>Difficulty: {Math.round(asset.metadata.difficulty * 100)}%</span>}</div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">{asset.description}</p>
                              <div className="flex flex-wrap gap-1 mt-2">{asset.tags.slice(0, 4).map((tag, i) => (<Badge key={i} variant="outline" className="text-xs h-5 px-2">{tag}</Badge>))}</div>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
              {searchResults.length === 0 && !searchLoading && searchRequest.topic && (
                <Card className="border-dashed border-2 border-gray-200 dark:border-gray-700"><CardContent className="text-center py-12"><Search className="h-12 w-12 mx-auto text-gray-400 mb-4" /><h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">No results found</h3><p className="text-gray-600 dark:text-gray-400">Try adjusting your search criteria or using different keywords.</p></CardContent></Card>
              )}
            </div>
          </TabsContent>

          {/* Generate Curriculum Tab */}
          <TabsContent value="curriculum" className="mt-6 animate-fade-in">
            <div className="space-y-6">
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2"><Layers className="h-5 w-5" /> Generate Full Curriculum</CardTitle><CardDescription>Create a complete learning path across multiple levels and focus areas</CardDescription></CardHeader>
                <CardContent>
                  <div className="grid lg:grid-cols-4 gap-4 mb-4">
                    <div className="space-y-2"><Label>Language</Label><Select value={curriculumRequest.language} onValueChange={(v) => setCurriculumRequest({...curriculumRequest, language: v})}><SelectTrigger><SelectValue placeholder="Language" /></SelectTrigger><SelectContent><SelectItem value="es">Spanish</SelectItem><SelectItem value="en">English</SelectItem><SelectItem value="fr">French</SelectItem><SelectItem value="de">German</SelectItem><SelectItem value="it">Italian</SelectItem><SelectItem value="pt">Portuguese</SelectItem><SelectItem value="ja">Japanese</SelectItem><SelectItem value="ko">Korean</SelectItem><SelectItem value="zh">Chinese</SelectItem></SelectContent></Select></div>
                    <div className="space-y-2"><Label>Age Group</Label><Select value={curriculumRequest.age_group} onValueChange={(v) => setCurriculumRequest({...curriculumRequest, age_group: v as AgeGroup})}><SelectTrigger><SelectValue placeholder="Age Group" /></SelectTrigger><SelectContent>{AGE_GROUPS.map(g => <SelectItem key={g.value} value={g.value}>{g.label}</SelectItem>)}</SelectContent></Select></div>
                    <div className="space-y-2"><Label>Gamification</Label><Select value={curriculumRequest.gamification} onValueChange={(v) => setCurriculumRequest({...curriculumRequest, gamification: v as GamificationLevel})}><SelectTrigger><SelectValue placeholder="Gamification" /></SelectTrigger><SelectContent>{GAMIFICATION_LEVELS.map(l => <SelectItem key={l.value} value={l.value}>{l.label}</SelectItem>)}</SelectContent></Select></div>
                  </div>
                  <div className="grid lg:grid-cols-2 gap-6 mb-4">
                    <div className="space-y-3"><Label className="flex items-center gap-2"><Target className="h-4 w-4" /> CEFR Levels</Label><div className="flex flex-wrap gap-2">{['A1', 'A2', 'B1', 'B2', 'C1', 'C2'].map(level => (<label key={level} className="cursor-pointer"><input type="checkbox" checked={curriculumRequest.levels?.includes(level as CEFRLevel)} onChange={(e) => setCurriculumRequest({...curriculumRequest, levels: e.target.checked ? [...(curriculumRequest.levels || []), level as CEFRLevel] : (curriculumRequest.levels || []).filter(l => l !== level)})} className="sr-only peer" /><div className={`px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-all ${curriculumRequest.levels?.includes(level as CEFRLevel) ? 'bg-blue-600 text-white border-blue-600' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 peer-checked:bg-blue-600 peer-checked:text-white peer-checked:border-blue-600'}`}>{level}</div></label>))}</div></div>
                    <div className="space-y-3"><Label className="flex items-center gap-2"><BookOpen className="h-4 w-4" /> Focus Areas</Label><div className="flex flex-wrap gap-2">{FOCUS_AREA_OPTIONS.map(area => (<label key={area.value} className="cursor-pointer"><input type="checkbox" checked={curriculumRequest.focus_areas?.includes(area.value)} onChange={(e) => setCurriculumRequest({...curriculumRequest, focus_areas: e.target.checked ? [...(curriculumRequest.focus_areas || []), area.value] : (curriculumRequest.focus_areas || []).filter(f => f !== area.value)})} className="sr-only peer" /><div className={`px-3 py-1.5 rounded-lg text-sm font-medium border-2 transition-all flex items-center gap-1 ${curriculumRequest.focus_areas?.includes(area.value) ? 'bg-purple-600 text-white border-purple-600' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-gray-200 dark:border-gray-700 peer-checked:bg-purple-600 peer-checked:text-white peer-checked:border-purple-600'}`}><Icon name={area.icon} className="h-4 w-4" /> {area.label}</div></label>))}</div></div>
                  </div>
                  <div className="flex gap-3">
                    <Button onClick={handleGenerateCurriculum} disabled={curriculumLoading || !user} size="lg" className="flex-1">{curriculumLoading ? <> <Loader2 className="h-4 w-4 animate-spin mr-2" /> Generating Curriculum... </> : <> <Layers className="h-4 w-4 mr-2" /> Generate Full Curriculum </>}</Button>
                    <Button variant="outline" onClick={() => setGeneratedCurriculum([])}><RotateCcw className="h-4 w-4 mr-2" /> Clear</Button>
                  </div>
                  {curriculumError && (<div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm flex items-center gap-2"><AlertCircle className="h-4 w-4 flex-shrink-0" /> {curriculumError}</div>)}
                </CardContent>
              </Card>
              {generatedCurriculum.length > 0 && (
                <div className="space-y-6">
                  <div className="flex items-center justify-between"><h3 className="text-lg font-semibold">Generated Curriculum ({generatedCurriculum.length} lessons)</h3><div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400"><span>~{Math.round(generatedCurriculum.reduce((sum, l) => sum + l.duration_minutes, 0) / 60 * 10) / 10} hours total</span><span>{generatedCurriculum.reduce((sum, l) => sum + l.xp_reward, 0)} XP total</span></div></div>
                  <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {generatedCurriculum.map((lesson, index) => (
                      <Card key={lesson.id} className="hover:shadow-lg transition-shadow group">
                        <CardContent className="p-4">
                          <div className="flex items-start gap-3 mb-3"><span className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 text-white flex items-center justify-center font-bold text-sm">{index + 1}</span><div className="flex-1 min-w-0"><h4 className="font-medium text-gray-900 dark:text-white truncate pr-2">{lesson.title}</h4><div className="flex items-center gap-2 mt-1"><Badge variant="outline" className="text-xs">{lesson.level}</Badge><Badge variant="secondary" className="text-xs">{lesson.focus_area}</Badge><Badge variant="outline" className="text-xs">{lesson.gamification_level}</Badge></div></div></div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">{lesson.description}</p>
                          <div className="flex items-center justify-between text-xs text-gray-500"><span><Clock className="h-3 w-3 mr-1 inline" /> {formatDuration(lesson.duration_minutes)}</span><span><Trophy className="h-3 w-3 mr-1 inline" /> {lesson.xp_reward} XP</span><span><Layers className="h-3 w-3 mr-1 inline" /> {lesson.content_assets.length} activities</span></div>
                          <div className="flex gap-2 mt-3 pt-3 border-t"><Button variant="ghost" size="sm" className="flex-1" onClick={() => { setShowCurriculumDetail(lesson); setShowLessonPreview(true); }}><Eye className="h-3 w-3 mr-1" /> Preview</Button><Button variant="outline" size="sm" className="flex-1" disabled={!user}><Save className="h-3 w-3 mr-1" /> Save</Button></div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Sources Tab */}
          <TabsContent value="sources" className="mt-6 animate-fade-in">
            <div className="space-y-6">
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2"><DatabaseIcon className="h-5 w-5" /> Available Content Sources</CardTitle><CardDescription>Configured sources for multimedia content generation and search</CardDescription></CardHeader>
                <CardContent>
                  {sourcesLoading ? (
                    <div className="flex items-center justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-blue-600" /><span className="ml-3 text-gray-600 dark:text-gray-400">Loading sources...</span></div>
                  ) : sourcesInfo ? (
                    <div className="space-y-4">
                      {Object.entries(sourcesInfo.sources).map(([key, source]) => (
                        <div key={key} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                          <div className="flex items-start gap-4">
                            <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center"><Icon name={getSourceIcon(key as ContentSource)} className="h-6 w-6 text-blue-600 dark:text-blue-400" /></div>
                            <div className="flex-1">
                              <div className="flex items-center gap-3 mb-2"><h4 className="font-medium text-gray-900 dark:text-white capitalize">{key.replace('_', ' ')}</h4>{source.configured ? (<Badge variant="default" className="gap-1"><CheckCircle className="h-3 w-3" /> Configured</Badge>) : (<Badge variant="outline" className="gap-1"><AlertCircle className="h-3 w-3" /> Not Configured</Badge>)}{source.requires_api_key && (<Badge variant="secondary" className="gap-1"><Key className="h-3 w-3" /> API Key Required</Badge>)}</div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Capabilities: {source.capabilities.join(', ')}</p>
                              <div className="flex flex-wrap gap-1">{source.capabilities.map((cap, i) => (<Badge key={i} variant="outline" className="text-xs">{cap}</Badge>))}</div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-12"><AlertCircle className="h-12 w-12 mx-auto text-gray-400 mb-4" /><p className="text-gray-600 dark:text-gray-400">Unable to load source information</p></div>
                  )}
                </CardContent>
              </Card>
              <Card className="border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20">
                <CardHeader><CardTitle className="flex items-center gap-2"><Settings className="h-5 w-5" /> Source Configuration</CardTitle></CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg"><h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2"><Icon name="Youtube" className="h-4 w-4 text-red-500" /> YouTube API</h4><p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Get a free API key from <a href="https://console.cloud.google.com/apis/library/youtube.googleapis.com" target="_blank" rel="noopener" className="text-blue-600 hover:underline">Google Cloud Console</a></p><code className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded block">YOUTUBE_API_KEY=your_key</code></div>
                    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg"><h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2"><Icon name="Brain" className="h-4 w-4 text-purple-500" /> LLM Providers (Free Tier)</h4><p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Configure in shared-canonical-services: OpenRouter, Groq, Google AI, NVIDIA, Together, Cohere, Mistral, Cloudflare, Cerebras</p><code className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded block">OPENROUTER_API_KEY=your_key\nGROQ_API_KEY=your_key\n...</code></div>
                    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg"><h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2"><Icon name="Volume2" className="h-4 w-4 text-green-500" /> TTS Providers</h4><p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Edge TTS (free, no key needed) or ElevenLabs (premium)</p><code className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded block">ELEVENLABS_API_KEY=your_key</code></div>
                    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg"><h4 className="font-medium text-gray-900 dark:text-white mb-2 flex items-center gap-2"><Icon name="BookOpen" className="h-4 w-4 text-orange-500" /> Textbooks</h4><p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Add JSON-indexed textbooks to ./data/textbooks/ directory</p><code className="text-xs bg-gray-100 dark:bg-gray-700 p-2 rounded block">{'{"title": "Spanish A1", "language": "es", "chapters": [...]}'}</code></div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={showLessonPreview} onOpenChange={setShowLessonPreview}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
          <DialogHeader><DialogTitle>Lesson Preview</DialogTitle><DialogDescription>{previewLessonData?.title || generatedLesson?.title || 'Generated Lesson'}</DialogDescription></DialogHeader>
          <div className="flex-1 overflow-y-auto p-6" style={{ maxHeight: '60vh' }}>
            {previewLessonData || generatedLesson ? (
              <LessonPreviewBlueprint blueprint={previewLessonData || generatedLesson!} onClose={() => setShowLessonPreview(false)} />
            ) : (
              <div className="text-center py-12"><Loader2 className="h-8 w-8 animate-spin mx-auto text-blue-600 mb-4" /><p className="text-gray-600 dark:text-gray-400">Loading preview...</p></div>
            )}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setShowLessonPreview(false)}>Close</Button><Button onClick={handleSaveLesson} disabled={!user}><Save className="h-4 w-4 mr-2" /> Save to Curriculum</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!showAssetDetail} onOpenChange={(open) => !open && setShowAssetDetail(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{showAssetDetail?.title}</DialogTitle><DialogDescription>{showAssetDetail?.source.replace('_', ' ')} • {showAssetDetail?.type}</DialogDescription></DialogHeader>
          <div className="space-y-4">
            {showAssetDetail && (
              <>
                <div className="flex items-center gap-2"><Badge variant="outline">{showAssetDetail.type}</Badge><Badge variant="secondary">{showAssetDetail.source.replace('_', ' ')}</Badge><Badge variant="outline">{formatDuration(Math.round(showAssetDetail.duration_seconds / 60))}</Badge></div>
                <p className="text-gray-700 dark:text-gray-300">{showAssetDetail.description}</p>
                {showAssetDetail.url && (<a href={showAssetDetail.url} target="_blank" rel="noopener" className="text-blue-600 hover:underline flex items-center gap-1"><ExternalLink className="h-4 w-4" /> Open Source</a>)}
                <div className="pt-4 border-t"><h5 className="font-medium mb-2">Metadata</h5><pre className="text-xs bg-gray-100 dark:bg-gray-800 p-3 rounded overflow-auto max-h-64">{JSON.stringify(showAssetDetail.metadata, null, 2)}</pre></div>
              </>
            )}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setShowAssetDetail(null)}>Close</Button></DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!showCurriculumDetail} onOpenChange={(open) => !open && setShowCurriculumDetail(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden">
          <DialogHeader><DialogTitle>{showCurriculumDetail?.title}</DialogTitle><DialogDescription>Curriculum lesson detail</DialogDescription></DialogHeader>
          <div className="flex-1 overflow-y-auto p-6" style={{ maxHeight: '60vh' }}>
            {showCurriculumDetail && <LessonPreviewBlueprint blueprint={showCurriculumDetail} onClose={() => setShowCurriculumDetail(null)} />}
          </div>
          <DialogFooter><Button variant="outline" onClick={() => setShowCurriculumDetail(null)}>Close</Button><Button onClick={handleSaveLesson} disabled={!user}><Save className="h-4 w-4 mr-2" /> Save to Curriculum</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Lesson Preview Component
function LessonPreviewBlueprint({ blueprint, onClose }: { blueprint: LessonBlueprint; onClose: () => void }) {
  const getContentTypeIcon = (type: string) => CONTENT_TYPE_ICONS[type] || 'FileText';
  const getSourceIcon = (source: string) => {
    const icons: Record<string, string> = {
      llm_generated: 'Brain',
      youtube: 'Youtube',
      textbook: 'BookOpen',
      api_curriculum: 'Layers',
      user_created: 'User',
      community: 'Users',
      ai_curated: 'Sparkles',
    };
    return icons[source] || 'Database';
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 rounded-xl">
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <span className="px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium">{blueprint.level}</span>
          <span className="px-3 py-1 bg-purple-100 dark:bg-purple-900 text-purple-800 dark:text-purple-200 rounded-full text-sm font-medium">{blueprint.focus_area}</span>
          <span className="px-3 py-1 bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200 rounded-full text-sm font-medium">{blueprint.gamification_level}</span>
          <span className="px-3 py-1 bg-orange-100 dark:bg-orange-900 text-orange-800 dark:text-orange-200 rounded-full text-sm font-medium">{blueprint.target_age_groups[0] || 'adult'}</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">{blueprint.title}</h2>
        <p className="text-gray-600 dark:text-gray-400">{blueprint.description}</p>
        <div className="flex flex-wrap gap-4 mt-4 text-sm text-gray-600 dark:text-gray-400">
          <div className="flex items-center gap-1"><Clock className="h-4 w-4" /> {formatDuration(blueprint.duration_minutes)}</div>
          <div className="flex items-center gap-1"><Trophy className="h-4 w-4" /> {blueprint.xp_reward} XP</div>
          <div className="flex items-center gap-1"><Layers className="h-4 w-4" /> {blueprint.content_assets.length} activities</div>
          <div className="flex items-center gap-1"><Target className="h-4 w-4" /> {blueprint.learning_objectives.length} objectives</div>
        </div>
      </div>
      <section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Target className="h-5 w-5" /> Learning Objectives</h3><ul className="space-y-2">{blueprint.learning_objectives.map((obj, i) => (<li key={i} className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"><span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 flex items-center justify-center text-sm font-medium">{i + 1}</span><span className="text-gray-700 dark:text-gray-300">{obj}</span></li>))}</ul></section>
      <div className="grid md:grid-cols-2 gap-4">
        {blueprint.vocabulary_targets.length > 0 && (<section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><BookOpen className="h-5 w-5" /> Vocabulary Targets</h3><div className="flex flex-wrap gap-2">{blueprint.vocabulary_targets.map((word, i) => (<Badge key={i} variant="secondary">{word}</Badge>))}</div></section>)}
        {blueprint.grammar_points.length > 0 && (<section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><FileText className="h-5 w-5" /> Grammar Points</h3><div className="flex flex-wrap gap-2">{blueprint.grammar_points.map((point, i) => (<Badge key={i} variant="outline">{point}</Badge>))}</div></section>)}
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {blueprint.pronunciation_focus.length > 0 && (<section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Mic className="h-5 w-5" /> Pronunciation Focus</h3><ul className="space-y-1">{blueprint.pronunciation_focus.map((sound, i) => (<li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2"><CheckCircle className="h-4 w-4 text-green-500" /> {sound}</li>))}</ul></section>)}
        {blueprint.cultural_notes.length > 0 && (<section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Globe className="h-5 w-5" /> Cultural Notes</h3><ul className="space-y-1">{blueprint.cultural_notes.map((note, i) => (<li key={i} className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2"><MapPin className="h-4 w-4 text-orange-500" /> {note}</li>))}</ul></section>)}
      </div>
      <section><h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Layers className="h-5 w-5" /> Lesson Activities ({blueprint.content_assets.length})</h3><div className="space-y-3">{blueprint.content_assets.map((asset, index) => (<div key={asset.id} className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"><div className="flex items-start gap-4"><div className="flex-shrink-0 w-12 h-12 rounded-xl bg-blue-100 dark:bg-blue-900 flex items-center justify-center"><Icon name={getContentTypeIcon(asset.type)} className="h-6 w-6 text-blue-600 dark:text-blue-400" /></div><div className="flex-1 min-w-0"><div className="flex items-center gap-2 mb-1"><h4 className="font-medium text-gray-900 dark:text-white">{asset.title}</h4><Badge variant="outline" className="text-xs">{asset.type}</Badge><Badge variant="secondary" className="text-xs flex items-center gap-1"><Icon name={getSourceIcon(asset.source)} className="h-3 w-3" /> {asset.source.replace('_', ' ')}</Badge><span className="text-sm text-gray-500 ml-auto">~{Math.round(asset.duration_seconds / 60)} min</span></div><p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{asset.description}</p><div className="flex flex-wrap gap-1">{asset.tags.slice(0, 5).map((tag, i) => (<Badge key={i} variant="outline" className="text-xs h-5 px-2">{tag}</Badge>))}</div></div></div></div>))}</div></section>
    </div>
  );
}

export { LessonGeneratorPage as LessonGenerator };
export default LessonGeneratorPage;