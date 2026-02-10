/**
 * Audio Prompt Manager for LangHero.
 *
 * Handles playing audio prompts with TTS fallback.
 * Used by GameView and ScenarioDisplay for option playback.
 */

import { toBackendUrl } from '$lib/utils';
import { fetchTtsUrl } from '$lib/utils/ttsCache';
import { playBeep, speakWithSynthesis } from './audioUtils';

/**
 * Play an audio prompt with fallback chain:
 * 1. Direct audio URL from example
 * 2. TTS-generated audio from backend
 * 3. Browser speech synthesis
 * 4. Beep sound
 *
 * @param {Object} options
 * @param {Object|null} options.example - Example object with audio/target/native
 * @param {string} options.language - Target language for TTS
 * @param {HTMLAudioElement|null} options.audioPlayer - Audio element to use
 * @returns {Promise<boolean>} - Whether audio played successfully
 */
export async function playPrompt({ example, language, audioPlayer }) {
  const ex = example || null;
  const text = ex?.target || ex?.native || '';

  try {
    // Try direct audio URL first
    const url = toBackendUrl(ex?.audio || '');
    let finalUrl = url;

    // Fall back to TTS if no direct URL
    if (!finalUrl && text) {
      finalUrl = await fetchTtsUrl(text, language);
    }

    // If no URL available, use speech synthesis
    if (!finalUrl) {
      const spoken = speakWithSynthesis(text, language);
      if (!spoken) playBeep();
      return spoken;
    }

    // Play via audio element
    if (!audioPlayer) {
      const spoken = speakWithSynthesis(text, language);
      if (!spoken) playBeep();
      return spoken;
    }

    audioPlayer.src = finalUrl;
    try {
      await audioPlayer.play();
      return true;
    } catch (_) {
      // Audio play failed, fall back to synthesis
      const spoken = speakWithSynthesis(text, language);
      if (!spoken) playBeep();
      return spoken;
    }
  } catch (_) {
    // Any error, fall back to synthesis
    const spoken = speakWithSynthesis(text, language);
    if (!spoken) playBeep();
    return spoken;
  }
}

/**
 * Create a prompt player bound to an audio element and language getter.
 * Returns a simpler function that only needs the example.
 *
 * @param {Object} options
 * @param {Function} options.getAudioPlayer - Function returning the audio element
 * @param {Function} options.getLanguage - Function returning the current target language
 * @returns {Function} - Play function that takes just the example
 */
export function createPromptPlayer({ getAudioPlayer, getLanguage }) {
  return async function play(example) {
    return playPrompt({
      example,
      language: getLanguage(),
      audioPlayer: getAudioPlayer()
    });
  };
}
