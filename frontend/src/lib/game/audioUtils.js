/**
 * Audio utilities for game interactions.
 * Handles recording, TTS playback, and audio feedback.
 */

let audioCtx = null;
let analyserSource = null;

/**
 * Ensure AudioContext is initialized and resumed
 */
export function ensureAudioContext() {
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx) audioCtx = new Ctx();
  }
  if (audioCtx?.state === 'suspended') {
    audioCtx.resume().catch(() => {});
  }
  return audioCtx;
}

/**
 * Create an audio analyser for visualizing audio input
 */
export function setupAudioAnalyser(stream) {
  const ctx = ensureAudioContext();
  if (!ctx) return null;

  try {
    if (analyserSource) {
      try { analyserSource.disconnect(); } catch (_) {}
    }

    const analyser = ctx.createAnalyser();
    analyser.fftSize = 64;
    analyser.smoothingTimeConstant = 0.8;

    const source = ctx.createMediaStreamSource(stream);
    source.connect(analyser);
    analyserSource = source;

    return analyser;
  } catch (err) {
    console.warn('Could not create audio analyser:', err);
    return null;
  }
}

/**
 * Disconnect the current analyser source
 */
export function disconnectAnalyser() {
  if (analyserSource) {
    try { analyserSource.disconnect(); } catch (_) {}
    analyserSource = null;
  }
}

/**
 * Play a simple beep sound for audio feedback
 */
export function playBeep({ duration = 250, frequency = 880, volume = 0.25, type = 'sine' } = {}) {
  const ctx = ensureAudioContext();
  if (!ctx) return;

  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(frequency, ctx.currentTime);

  const now = ctx.currentTime;
  gain.gain.setValueAtTime(0.0001, now);
  gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, volume), now + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, now + duration / 1000);

  osc.connect(gain).connect(ctx.destination);
  osc.start(now);
  osc.stop(now + duration / 1000 + 0.05);
}

/**
 * Play error/penalty beep
 */
export function playErrorBeep() {
  playBeep({ frequency: 420, duration: 160 });
}

/**
 * Play neutral feedback beep
 */
export function playFeedbackBeep() {
  playBeep({ frequency: 440, duration: 160 });
}

/**
 * Use browser speech synthesis as TTS fallback
 */
export function speakWithSynthesis(text, language = 'en') {
  const phrase = String(text || '').trim();
  if (!phrase) return false;

  try {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return false;

    const synth = window.speechSynthesis;
    synth.cancel();

    const utter = new SpeechSynthesisUtterance(phrase);
    const lang = String(language || '').toLowerCase();

    if (lang.includes('japanese') || lang === 'ja') utter.lang = 'ja-JP';
    else if (lang.includes('english') || lang === 'en') utter.lang = 'en-US';
    else utter.lang = 'en-US';

    utter.rate = 1.05;
    utter.pitch = 0.7;
    utter.volume = 1.0;

    try {
      const voices = synth.getVoices ? synth.getVoices() : [];
      if (voices?.length) {
        const preferred = voices.find((v) => v.lang === utter.lang && /synth|robot|elect|mono/i.test(v.name))
          || voices.find((v) => v.lang === utter.lang);
        if (preferred) utter.voice = preferred;
      }
    } catch (_) {}

    synth.speak(utter);
    return true;
  } catch (_) {
    return false;
  }
}

/**
 * Create a recording session
 * Returns { start, stop, onData, onStop }
 */
export async function createRecordingSession(deviceId = '') {
  const audioConstraints = deviceId ? { deviceId: { exact: deviceId } } : true;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
  const mediaRecorder = new MediaRecorder(stream);
  const chunks = [];

  const analyser = setupAudioAnalyser(stream);

  return {
    stream,
    mediaRecorder,
    analyser,
    chunks,

    start(timeslice) {
      if (timeslice) {
        mediaRecorder.start(timeslice);
      } else {
        mediaRecorder.start();
      }
    },

    stop() {
      if (mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }
    },

    cleanup() {
      try {
        stream.getTracks().forEach(t => t.stop());
      } catch (_) {}
      disconnectAnalyser();
    },

    getBlob() {
      return new Blob(chunks, { type: 'audio/webm' });
    }
  };
}

/**
 * Refresh available microphone devices
 */
export async function getMicrophoneDevices() {
  if (typeof navigator === 'undefined' || !navigator?.mediaDevices?.enumerateDevices) {
    return [];
  }

  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return (devices || [])
      .filter((d) => d && d.kind === 'audioinput')
      .map((d, idx) => ({
        deviceId: String(d.deviceId || ''),
        label: String(d.label || '').trim() || `Microphone ${idx + 1}`,
      }))
      .filter((d) => Boolean(d.deviceId));
  } catch (_) {
    return [];
  }
}
