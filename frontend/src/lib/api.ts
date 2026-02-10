import { getAuthToken } from '$lib/auth';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Get the API base URL
 */
export function getApiBase(): string {
  return API_BASE;
}

export async function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
  const headers = new Headers(init.headers || {});
  const token = getAuthToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return fetch(input, { ...init, headers });
}

// TTS Types
export interface TTSRequest {
  text: string;
  language?: string;
  voice?: string;
  format?: 'mp3' | 'wav' | 'opus';
  scenario_id?: number;
  character_id?: string;  // For consistent voice across scenes
  role?: 'npc' | 'narrator' | 'bimbo' | 'player_example';
  character_gender?: 'male' | 'female' | 'neutral';
  character_type?: string;
  sentiment?: Sentiment;   // Emotion/tone for expressive TTS
  context?: TTSContext;    // Situational context for sentiment inference
}

// Available sentiments for expressive TTS
export type Sentiment =
  // Positive
  | 'warm' | 'friendly' | 'encouraging' | 'happy' | 'excited' | 'grateful' | 'proud'
  // Neutral
  | 'neutral' | 'formal' | 'calm' | 'informative' | 'thoughtful'
  // Negative/tense
  | 'suspicious' | 'stern' | 'angry' | 'threatening' | 'impatient' | 'worried' | 'sad' | 'confused'
  // Urgent/dramatic
  | 'urgent' | 'commanding' | 'dramatic' | 'whispered';

// Situational contexts that map to sentiments
export type TTSContext =
  | 'greeting' | 'question' | 'teaching' | 'warning' | 'threat' | 'praise' | 'correction';

export interface TTSResponse {
  url: string;
  voice: string;
  sentiment?: string;
  instructions?: string;
  clip_id?: string;
  phrase_id?: string;
  file?: string;
  format?: string;
  error?: string;
}

export interface VoicesResponse {
  voices: Record<string, { gender: string; tone: string; accent: string }>;
  male: string[];
  female: string[];
  neutral: string[];
  character_types: string[];
  sentiments: string[];
  contexts: string[];
}

/**
 * Get available TTS voices
 */
export async function getVoices(): Promise<VoicesResponse> {
  const res = await apiFetch(`${API_BASE}/api/voices`);
  return res.json();
}

/**
 * Generate or retrieve a TTS audio clip for text
 */
export async function getTTS(options: TTSRequest): Promise<TTSResponse> {
  const res = await apiFetch(`${API_BASE}/api/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  const data = await res.json();
  // Prepend API base to relative URL
  if (data.url && !data.url.startsWith('http')) {
    data.url = `${API_BASE}${data.url}`;
  }
  return data;
}

/**
 * Play TTS audio for given text (convenience wrapper)
 */
export async function playTTS(
  text: string,
  options: Omit<TTSRequest, 'text'> = {}
): Promise<HTMLAudioElement> {
  const response = await getTTS({ text, ...options });
  if (response.error) {
    throw new Error(response.error);
  }
  const audio = new Audio(response.url);
  await audio.play();
  return audio;
}

/**
 * Get TTS for Bimbo (AI companion) with appropriate voice
 */
export async function playBimboTTS(text: string): Promise<HTMLAudioElement> {
  return playTTS(text, { role: 'bimbo', voice: 'alloy' });
}

/**
 * Get TTS for narrator with appropriate voice
 */
export async function playNarratorTTS(text: string): Promise<HTMLAudioElement> {
  return playTTS(text, { role: 'narrator', voice: 'alloy' });
}

/**
 * Get TTS for NPC with auto-selected voice based on character
 */
export async function playNPCTTS(
  text: string,
  options: {
    scenario_id?: number;
    character_gender?: 'male' | 'female' | 'neutral';
    character_type?: string;
  } = {}
): Promise<HTMLAudioElement> {
  return playTTS(text, { role: 'npc', ...options });
}

// Panel Types
export type PanelType = 'full' | 'wide' | 'tall' | 'split' | 'triple' | 'impact' | 'transition';
export type ArtStyle = 'manhwa' | 'manga' | 'ghibli' | 'dramatic' | 'minimal';
export type PanelMood = 'warm' | 'cold' | 'tense' | 'peaceful' | 'mysterious' | 'dramatic' | 'hopeful';
export type VisualEffect = 'none' | 'speed_lines' | 'impact_burst' | 'radial_zoom' | 'screen_tone' | 'vignette' | 'frozen' | 'rain' | 'particles';

export interface Panel {
  id: string;
  type: PanelType;
  scene_description: string;
  dialogue?: string;
  dialogue_translation?: string;
  speaker?: string;
  mood: PanelMood;
  art_style: ArtStyle;
  effects: VisualEffect[];
  character_expression?: string;
  duration_ms: number;
  image_url?: string;
}

export interface PanelsResponse {
  panels: Panel[];
}

/**
 * Get pre-defined intro panels
 */
export async function getIntroPanels(): Promise<PanelsResponse> {
  const res = await apiFetch(`${API_BASE}/api/panels/intro`);
  return res.json();
}

/**
 * Generate images for panels
 */
export async function generatePanelImages(
  panels: Panel[],
  options: { context?: string; force?: boolean } = {}
): Promise<{ results: Array<{ panel_id: string; url?: string; error?: string }> }> {
  const res = await apiFetch(`${API_BASE}/api/panels/generate-images`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      panels: panels.map(p => ({
        id: p.id,
        type: p.type,
        scene_description: p.scene_description,
        mood: p.mood,
        art_style: p.art_style,
        effects: p.effects,
        character_expression: p.character_expression,
      })),
      context: options.context || '',
      force: options.force || false,
    }),
  });
  return res.json();
}
