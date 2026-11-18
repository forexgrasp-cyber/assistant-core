/**
 * API Client for Tutor Service
 * Handles all communication with the backend API
 */

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Auth
  async login(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail || 'Login failed');
    }

    return response.json();
  }

  async register(data: { email: string; password: string; name: string }) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async refreshToken() {
    return this.request('/auth/refresh', { method: 'POST' });
  }

  async getMe() {
    return this.request('/auth/me');
  }

  // Lessons
  async getLessons(params?: { language?: string; level?: string; focusArea?: string }) {
    const query = new URLSearchParams(params as Record<string, string>).toString();
    return this.request<Lesson[]>(`/lessons${query ? `?${query}` : ''}`);
  }

  async getLesson(id: string) {
    return this.request<Lesson>(`/lessons/${id}`);
  }

  async getLessonContent(lessonId: string) {
    return this.request<LessonContent[]>(`/lessons/${lessonId}/content`);
  }

  // Lesson Generation
  async generateLesson(request: GenerateLessonRequest) {
    return this.request<GenerateLessonResponse>('/generation/lesson', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async previewLesson(request: GenerateLessonRequest) {
    return this.request<GenerateLessonResponse>('/generation/lesson/preview', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async searchContent(request: SearchContentRequest) {
    return this.request<SearchContentResponse>('/generation/content/search', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async generateCurriculum(request: GenerateCurriculumRequest) {
    return this.request<GenerateCurriculumResponse>('/generation/curriculum/generate', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  async getAvailableSources() {
    return this.request<AvailableSourcesResponse>('/generation/sources');
  }

  async fetchContentAsset(source: string, assetId: string) {
    return this.request(`/generation/content/fetch/${source}/${assetId}`, {
      method: 'POST',
    });
  }

  // Progress
  async getUserProgress(language: string) {
    return this.request<UserProgress>(`/progress/${language}`);
  }

  async updateProgress(language: string, data: Partial<UserProgress>) {
    return this.request<UserProgress>(`/progress/${language}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async completeLesson(lessonId: string, data: { score: number; timeSpent: number }) {
    return this.request(`/progress/lessons/${lessonId}/complete`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  // Tutor Memory / AI Chat
  async chatWithTutor(data: { message: string; language: string; sessionId?: string }) {
    return this.request<TutorResponse>('/tutor/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getTutorSuggestions(language: string) {
    return this.request<string[]>(`/tutor/suggestions/${language}`);
  }

  // Voice Settings
  async getVoiceSettings() {
    return this.request<VoiceSettings>('/voice/settings');
  }

  async updateVoiceSettings(settings: Partial<VoiceSettings>) {
    return this.request<VoiceSettings>('/voice/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  async getAvailableVoices(language?: string) {
    const query = language ? `?language=${language}` : '';
    return this.request<AvailableVoice[]>(`/voice/voices${query}`);
  }

  async previewVoice(voiceId: string, text: string) {
    return this.request<{ audioUrl: string }>('/voice/preview', {
      method: 'POST',
      body: JSON.stringify({ voice_id: voiceId, text }),
    });
  }

  // Curriculum
  async getCurriculum(language: string) {
    return this.request<Lesson[]>(`/curriculum/${language}`);
  }

  async getCurriculumProgress(language: string) {
    return this.request<CurriculumProgress>(`/curriculum/${language}/progress`);
  }
}

export const api = new ApiClient();

// Types for Lesson Generation
export interface GenerateLessonRequest {
  focus_area?: FocusArea;
  age_group: AgeGroup;
  gamification: GamificationLevel;
  duration_minutes?: number;
  use_sources?: ContentSource[];
  language: string;
}

export interface GenerateLessonResponse {
  blueprint: LessonBlueprint;
  lesson_id?: string;
  status: 'generated' | 'saved' | 'error';
  message: string;
}

export interface SearchContentRequest {
  language: string;
  level: CEFRLevel;
  focus_area: FocusArea;
  topic: string;
  age_groups?: AgeGroup[];
  max_duration_minutes?: number;
  max_results?: number;
  gamification?: GamificationLevel;
  content_types?: ContentType[];
  sources?: ContentSource[];
}

export interface SearchContentResponse {
  assets: ContentAsset[];
  total: number;
  sources_searched: string[];
}

export interface GenerateCurriculumRequest {
  language: string;
  age_group?: AgeGroup;
  gamification?: GamificationLevel;
  levels?: CEFRLevel[];
  focus_areas?: FocusArea[];
}

export interface GenerateCurriculumResponse {
  total_lessons: number;
  lessons: LessonBlueprint[];
  estimated_hours: number;
}

export interface AvailableSourcesResponse {
  sources: Record<string, SourceInfo>;
  age_groups: AgeGroup[];
  gamification_levels: GamificationLevel[];
  content_types: ContentType[];
}

export interface SourceInfo {
  name: string;
  type: string;
  capabilities: string[];
  requires_api_key: boolean;
  configured: boolean;
}

export interface LessonBlueprint {
  id: string;
  title: string;
  description: string;
  language: string;
  level: CEFRLevel;
  focus_area: FocusArea;
  target_age_groups: AgeGroup[];
  gamification_level: GamificationLevel;
  duration_minutes: number;
  xp_reward: number;
  prerequisites: string[];
  learning_objectives: string[];
  content_assets: ContentAsset[];
  vocabulary_targets: string[];
  grammar_points: string[];
  pronunciation_focus: string[];
  cultural_notes: string[];
  assessment_criteria: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface ContentAsset {
  id: string;
  type: ContentType;
  source: ContentSource;
  title: string;
  description: string;
  url?: string;
  local_path?: string;
  metadata: Record<string, unknown>;
  duration_seconds: number;
  difficulty: number;
  age_appropriate: AgeGroup[];
  language: string;
  tags: string[];
  license: string;
  attribution: string;
}

export type AgeGroup = 'child' | 'teen' | 'young_adult' | 'adult' | 'senior';
export type GamificationLevel = 'none' | 'light' | 'medium' | 'full';
export type ContentSource = 'llm_generated' | 'youtube' | 'textbook' | 'api_curriculum' | 'user_created' | 'community' | 'ai_curated';

// Re-export from types
export type { CEFRLevel, FocusArea, ContentType, Lesson, LessonContent, UserProgress, TutorResponse, ChatMessage } from '../types';

export interface VoiceSettings {
  language: string;
  voice_id: string;
  provider: 'edge_tts' | 'elevenlabs';
  speed: number;
  pitch: number;
  volume: number;
}

export interface AvailableVoice {
  voice_id: string;
  name: string;
  language: string;
  gender: 'male' | 'female' | 'neutral';
  age_group: 'child' | 'teen' | 'adult' | 'senior';
  accent?: string;
  provider: 'edge_tts' | 'elevenlabs';
  preview_url?: string;
}

export interface CurriculumProgress {
  language: string;
  current_level: CEFRLevel;
  completed_lessons: number;
  total_lessons: number;
  level_progress: Record<CEFRLevel, number>;
  focus_area_progress: Record<FocusArea, number>;
  estimated_completion_date?: string;
}