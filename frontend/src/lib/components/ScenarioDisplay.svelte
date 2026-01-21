<script>
  import { storyStore } from '$lib/storyStore.js';
  import { getBackendUrl, discoverBackend, getStreamMode } from '$lib/config';
  import { activeRunId, getRun, syncFromStorage, updateRun } from '$lib/runStore.js';
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import ScenarioHeader from './scenario/ScenarioHeader.svelte';
  import ScenarioStatus from './scenario/ScenarioStatus.svelte';
  import ScenarioOptionsPanel from './scenario/ScenarioOptionsPanel.svelte';
  import MockStreamPanel from './scenario/MockStreamPanel.svelte';
  import ScenarioControls from './scenario/ScenarioControls.svelte';

  let audioPlayer; // Bind to the audio element
  let isRecording = false;
  let mediaRecorder;
  let audioChunks = [];
  let audioBlob = null;
  let speakingSuggestions = null; // { question, options: [{option_text, examples[], next_scenario}] }
  let localSuggestions = null;
  $: targetLang = ($storyStore?.language && typeof $storyStore.language === 'string' && $storyStore.language.trim())
    ? $storyStore.language
    : ($storyStore?.character_dialogue_jp ? 'Japanese' : 'English');
  const normalizeLanguageOverride = (v) => {
    const raw = String(v || '').trim();
    if (!raw) return '';
    const lowered = raw.toLowerCase();
    if (['auto', 'default', 'none'].includes(lowered)) return '';
    if (['ja', 'jp', 'japanese'].includes(lowered)) return 'Japanese';
    if (['en', 'eng', 'english'].includes(lowered)) return 'English';
    if (['es', 'spa', 'spanish', 'espanol', 'español'].includes(lowered)) return 'Spanish';
    return raw;
  };
  let languageOverride = '';
  $: languageOverride = normalizeLanguageOverride(languageOverride);
  $: effectiveTargetLang = languageOverride || targetLang;
  const nativeLang = 'English'; // TODO: make user-configurable
  let audioCtx = null;
  let requireRepeat = false;
  let selectedOption = null; // { next_scenario, example: { native, target, audio } }
  let lives = 3;
  let livesTotal = 3;
  let score = 0;
  let runLivesInitialized = false;
  let lastRunIdForState = null;
  let lastSavedScore = null;
  let lastSavedLivesTotal = null;
  let lastSavedLivesRemaining = null;
  let penaltyMessage = '';
  let devMode = false;
  let lastHeard = '';
  let matchConfidence = null;
  let matchType = '';
  let evaluating = false;
  let micDevices = [];
  let micDeviceId = '';
  const MIC_KEY = 'LANGHERO_MIC_DEVICE_ID_V1';
  let recordingStream = null;
  let nativeStream = null;
  // Make-your-own line (native -> translate -> try)
  let myNativeText = '';
  let translating = false;
  let isNativeRecording = false;
  let nativeRecorder;
  let nativeChunks = [];
  let judgeFocus = 0; // 0 = learning-first, 1 = story-first
  let streamMode = 'real';
  let streamingEnabled = false;
  let streamStatus = 'disabled';
  let streamEvents = [];
  let streamSocket = null;
  let liveTranscript = '';
  let waveCanvas;
  let scenarioMode = 'beginner';
  let trackRun = false;
  let currentRunId = null;
  let lastSavedJudgeFocus = null;
  let lastSavedLanguageOverride = null;
  let unsubRun = null;
  const ttsCache = new Map(); // key -> absolute URL
  $: scenarioMode = (() => {
    const raw = typeof $storyStore?.mode === 'string' ? $storyStore.mode : '';
    if (typeof raw === 'string') {
      const normalized = raw.trim().toLowerCase();
      if (normalized === 'advanced') return 'advanced';
      if (normalized === 'beginner') return 'beginner';
    }
    return 'beginner';
  })();
  $: isLiveScenario = scenarioMode === 'advanced';

  function ensureAudioContext() {
    // Lazily create a shared AudioContext (resumed on interaction)
    if (!audioCtx) {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      if (Ctx) audioCtx = new Ctx();
    }
    if (audioCtx?.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }
    return audioCtx;
  }

  function playBeep({ duration = 250, frequency = 880, volume = 0.25, type = 'sine' } = {}) {
    const ctx = ensureAudioContext();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(frequency, ctx.currentTime);
    // simple attack/decay to avoid click
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, volume), now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + duration / 1000);
    osc.connect(gain).connect(ctx.destination);
    osc.start(now);
    osc.stop(now + duration / 1000 + 0.05);
  }

  function resetLives(total = livesTotal) {
    const candidate = Number.isFinite(total) ? Number(total) : livesTotal;
    const safeTotal = Number.isFinite(candidate) && candidate > 0 ? Math.floor(candidate) : 3;
    livesTotal = safeTotal;
    lives = safeTotal;
  }

  function resetStreamState(forceActive) {
    const active = typeof forceActive === 'boolean' ? forceActive : streamingEnabled;
    streamEvents = [];
    liveTranscript = '';
    streamStatus = active ? 'idle' : 'disabled';
    penaltyMessage = '';
  }

  $: {
    const shouldStream = streamMode !== 'off' && isLiveScenario;
    if (streamingEnabled !== shouldStream) {
      streamingEnabled = shouldStream;
      if (streamingEnabled) {
        resetStreamState(true);
      } else {
        closeStream('mode_disabled');
        streamEvents = [];
        liveTranscript = '';
        streamStatus = 'disabled';
      }
    }
  }

  function handleOptionSelection(event) {
    const detail = event?.detail || {};
    const nextScenario = detail.next_scenario ?? detail.nextScenario ?? null;
    const example = detail.example || null;
    selectedOption = { next_scenario: nextScenario, example };
    requireRepeat = true;
    lastHeard = '';
    playPrompt(example);
  }

  const handlePlayPrompt = () => playPrompt(selectedOption?.example);

  async function refreshMicDevices() {
    try {
      if (typeof navigator === 'undefined' || !navigator?.mediaDevices?.enumerateDevices) return;
      const devices = await navigator.mediaDevices.enumerateDevices();
      const inputs = (devices || [])
        .filter((d) => d && d.kind === 'audioinput')
        .map((d, idx) => ({
          deviceId: String(d.deviceId || ''),
          label: String(d.label || '').trim() || `Microphone ${idx + 1}`,
        }))
        .filter((d) => Boolean(d.deviceId));
      micDevices = inputs;
      if (micDeviceId && !inputs.some((d) => d.deviceId === micDeviceId)) {
        micDeviceId = '';
        try { localStorage.removeItem(MIC_KEY); } catch (_) {}
      }
    } catch (_) {
      // ignore
    }
  }

  function persistMicChoice() {
    try {
      const id = String(micDeviceId || '').trim();
      if (!id) localStorage.removeItem(MIC_KEY);
      else localStorage.setItem(MIC_KEY, id);
    } catch (_) {}
  }

  function toBackendUrl(pathOrUrl) {
    const raw = String(pathOrUrl || '').trim();
    if (!raw) return '';
    if (/^https?:\/\//.test(raw)) return raw;
    const backend = getBackendUrl().replace(/\/$/, '');
    const normalized = raw.startsWith('/') ? raw : `/${raw}`;
    return `${backend}${normalized}`;
  }

  async function fetchTtsUrl(text) {
    const phrase = String(text || '').trim();
    if (!phrase) return '';
    const cacheKey = `${(effectiveTargetLang || '').trim().toLowerCase()}::${phrase}`;
    if (ttsCache.has(cacheKey)) return ttsCache.get(cacheKey) || '';
    try {
      const res = await fetch(`${getBackendUrl()}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: phrase, language: effectiveTargetLang }),
      });
      const data = res.ok ? await res.json() : null;
      if (data?.error) {
        console.warn('TTS failed', data.error);
      }
      const url = toBackendUrl(data?.url || '');
      if (url) ttsCache.set(cacheKey, url);
      return url;
    } catch (_) {
      return '';
    }
  }

  async function playPrompt(example) {
    try {
      const ex = example || null;
      const url = toBackendUrl(ex?.audio || '');
      let finalUrl = url;
      if (!finalUrl) {
        finalUrl = await fetchTtsUrl(ex?.target || ex?.native || '');
      }
      if (!finalUrl) {
        const spoken = speakAssistant(ex?.target || ex?.native || '', effectiveTargetLang);
        if (!spoken) playBeep();
        return;
      }
      if (!audioPlayer) return;
      audioPlayer.src = finalUrl;
      try {
        await audioPlayer.play();
      } catch (_) {
        const spoken = speakAssistant(ex?.target || ex?.native || '', effectiveTargetLang);
        if (!spoken) playBeep();
      }
    } catch (_) {
      const ex = example || null;
      const spoken = speakAssistant(ex?.target || ex?.native || '', effectiveTargetLang);
      if (!spoken) playBeep();
      return;
    }
  }

  function speakAssistant(text, language) {
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
      // Robotic-ish defaults for the "time machine assistant".
      utter.rate = 1.05;
      utter.pitch = 0.7;
      utter.volume = 1.0;
      try {
        const voices = synth.getVoices ? synth.getVoices() : [];
        if (voices && voices.length) {
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

  function ensureStreamConnection() {
    if (!streamingEnabled) return;
    if (streamSocket && (streamSocket.readyState === WebSocket.OPEN || streamSocket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    const backend = getBackendUrl();
    const path = streamMode === 'mock' ? '/stream/mock' : '/stream/interaction';
    const wsUrl = backend.replace(/^http/, backend.startsWith('https') ? 'wss' : 'ws') + path;
    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      streamStatus = 'connecting';
      streamEvents = [];

      ws.onopen = () => {
        streamStatus = 'open';
        const scenario = get(storyStore);
        const payload = {
          scenario_id: scenario?.id ?? null,
          language: effectiveTargetLang,
          judge: judgeFocus,
          score,
          lives_total: livesTotal,
          lives_remaining: lives,
        };
        try {
          ws.send(JSON.stringify(payload));
        } catch (err) {
          console.error('stream init failed', err);
        }
      };

      ws.onmessage = (event) => {
        let data;
        try {
          data = typeof event.data === 'string' ? JSON.parse(event.data) : JSON.parse(new TextDecoder().decode(event.data));
        } catch (err) {
          console.warn('stream non-json message', err);
          return;
        }
        handleStreamEvent(data);
      };

      ws.onerror = () => {
        streamStatus = 'error';
      };

      ws.onclose = () => {
        if (streamStatus !== 'final') {
          streamStatus = 'closed';
        }
        streamSocket = null;
      };

      streamSocket = ws;
    } catch (err) {
      console.error('stream connection error', err);
      streamStatus = 'error';
    }
  }

  async function sendStreamChunk(blob) {
    if (!streamingEnabled) return;
    if (!streamSocket || streamSocket.readyState !== WebSocket.OPEN) return;
    if (!blob || !blob.size) return;
    try {
      const buffer = await blob.arrayBuffer();
      streamSocket.send(buffer);
    } catch (err) {
      console.error('stream send error', err);
    }
  }

  function signalStreamStop(reason = 'stop') {
    if (!streamSocket || streamSocket.readyState !== WebSocket.OPEN) return;
    try {
      streamSocket.send(reason);
    } catch (err) {
      console.error('stream stop error', err);
    }
  }

  function closeStream(reason = 'cleanup') {
    if (!streamSocket) return;
    try {
      if (streamSocket.readyState === WebSocket.OPEN) {
        streamSocket.send(reason);
      }
      streamSocket.close();
    } catch (err) {
      console.error('stream close error', err);
    } finally {
      streamSocket = null;
    }
  }

  function handleStreamEvent(data) {
    if (!data || typeof data !== 'object') return;
    streamEvents = [...streamEvents.slice(-19), data];
    const evt = data.event;
    if (evt === 'ready') {
      streamStatus = 'open';
      if (typeof data.lives_total === 'number') {
        livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, Math.min(livesTotal, data.lives_remaining));
      } else {
        lives = Math.max(0, Math.min(livesTotal, lives));
      }
      if (typeof data.score === 'number') {
        score = Math.max(0, data.score);
      }
      penaltyMessage = '';
      runLivesInitialized = true;
      return;
    }
    if (evt === 'reset') {
      streamStatus = 'open';
      if (typeof data.lives_total === 'number') {
        livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, Math.min(livesTotal, data.lives_remaining));
      } else {
        lives = Math.max(0, Math.min(livesTotal, lives));
      }
      if (typeof data.score === 'number') {
        score = Math.max(0, data.score);
      }
      penaltyMessage = '';
      runLivesInitialized = true;
      return;
    }
    if (evt === 'partial') {
      streamStatus = 'streaming';
      liveTranscript = data.transcript || '';
      return;
    }
    if (evt === 'penalty') {
      streamStatus = 'penalty';
      if (typeof data.lives_total === 'number') {
        livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, data.lives_remaining);
      } else {
        const delta = (typeof data.lives_delta === 'number' && Number.isFinite(data.lives_delta)) ? data.lives_delta : -1;
        lives = Math.max(0, lives + delta);
      }
      if (typeof data.score === 'number') {
        score = data.score;
      }
      penaltyMessage = data.message || `Try that again in ${effectiveTargetLang}.`;
      playBeep({ frequency: 420, duration: 160 });
      if (lives === 0) {
        alert('Out of lives. Try a different option.');
        requireRepeat = false;
      }
      return;
    }
    if (evt === 'final') {
      streamStatus = 'final';
      liveTranscript = data?.result?.heard || liveTranscript;
      if (typeof data.score === 'number') {
        score = data.score;
      }
      if (typeof data.lives_total === 'number') {
        livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, data.lives_remaining);
      }
      const finalResult = data?.result || {};
      if (!finalResult?.error) {
        penaltyMessage = '';
      }
      applyInteractionResult(data?.result, { fromStream: true });
      return;
    }
    if (evt === 'error') {
      streamStatus = 'error';
      return;
    }
    if (evt === 'info') {
      // leave status unchanged
      return;
    }
  }

  // Reactive: update audio src; defer autoplay until user interacts
  let userInteracted = false;
  $: if ($storyStore.audio_to_play_url && audioPlayer) {
    audioPlayer.src = $storyStore.audio_to_play_url;
    if (userInteracted) {
      setTimeout(() => {
        audioPlayer.play().catch(() => {});
      }, 100);
    }
  }

  function applyInteractionResult(result, { fromStream = false } = {}) {
    if (!result || typeof result !== 'object') return;
    lastHeard = result?.heard || '';
    const c = Number(result?.confidence ?? result?.match_confidence ?? result?.matchConfidence);
    matchConfidence = Number.isFinite(c) ? Math.max(0, Math.min(1, c)) : null;
    matchType = String(result?.match_type ?? result?.matchType ?? '');
    if (!fromStream) {
      const deltaScore = Number(result?.scoreDelta ?? 0);
      if (Number.isFinite(deltaScore) && deltaScore !== 0) {
        score = Math.max(0, score + Math.round(deltaScore));
      }
      const deltaLives = Number(result?.livesDelta ?? 0);
      if (Number.isFinite(deltaLives) && deltaLives !== 0) {
        lives = Math.max(0, lives + deltaLives);
        if (lives <= 0) {
          requireRepeat = false;
        }
      }
      if (result?.error) {
        penaltyMessage = String(result.error);
      } else if (typeof result?.message === 'string' && result.message.trim()) {
        penaltyMessage = result.message.trim();
      } else {
        penaltyMessage = '';
      }
    }
    if (result?.repeatExpected) {
      selectedOption = {
        next_scenario: (result?.repeatNextScenario ?? null),
        example: {
          native: lastHeard || '',
          target: result.repeatExpected || '',
          pronunciation: result.pronunciation || ''
        }
      };
      requireRepeat = true;
      playPrompt(selectedOption.example);
    } else if (result?.nextScenario) {
      const next = result.nextScenario;
      if (typeof next === 'object' && next?.id) {
        storyStore.goToScenario(next.id);
      } else if (typeof next === 'number') {
        storyStore.goToScenario(next);
      }
      requireRepeat = false;
    } else {
      playBeep({ frequency: 440, duration: 160 });
    }
    evaluating = false;
  }

  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        if (streamingEnabled) {
          signalStreamStop('stop');
        }
        mediaRecorder.stop();
      }
      isRecording = false;
    } else {
      // Start recording
      try {
        const audioConstraints = micDeviceId ? { deviceId: { exact: micDeviceId } } : true;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        recordingStream = stream;
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = async event => {
          if (!event?.data) return;
          audioChunks.push(event.data);
          if (streamingEnabled) {
            await sendStreamChunk(event.data);
          }
        };

        mediaRecorder.onstop = async () => {
          audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          audioChunks = [];
          try {
            recordingStream?.getTracks?.().forEach((t) => t.stop());
          } catch (_) {}
          recordingStream = null;

          if (streamingEnabled) {
            return;
          }

          const formData = new FormData();
          formData.append('audio_file', audioBlob, 'recording.webm');

          try {
            if (requireRepeat && selectedOption) {
              evaluating = true;
              lastHeard = '';
              matchConfidence = null;
              matchType = '';
              formData.append('expected', selectedOption.example?.target || '');
              if (selectedOption.next_scenario != null) formData.append('next_scenario', String(selectedOption.next_scenario));
              if (effectiveTargetLang) formData.append('lang', effectiveTargetLang);
              formData.append('judge', String(judgeFocus));
              const response = await fetch(`${getBackendUrl()}/narrative/imitate`, { method: 'POST', body: formData });
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              const result = await response.json();
              applyInteractionResult(result);
            } else {
              formData.append('current_scenario_id', $storyStore.id);
              if (effectiveTargetLang) formData.append('lang', effectiveTargetLang);
              formData.append('judge', String(judgeFocus));
              const response = await fetch(`${getBackendUrl()}/narrative/interaction`, { method: 'POST', body: formData });
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              const result = await response.json();
              applyInteractionResult(result);
            }
          } catch (error) {
            console.error("Error sending audio to backend:", error);
            alert("There was an issue connecting to the server. Please try again.");
          }
        };

        audioChunks = [];
        if (streamingEnabled) {
          resetStreamState();
          ensureStreamConnection();
          mediaRecorder.start(200);
        } else {
          mediaRecorder.start();
        }
        isRecording = true;
        refreshMicDevices();

      } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Microphone access is required to proceed. Please allow access and try again.");
      }
    }
  }

  // Handle browser autoplay restrictions
  function handleFirstInteraction() {
    if (audioPlayer && audioPlayer.paused) {
      userInteracted = true;
      audioPlayer.play().catch(e => {});
    }
    window.removeEventListener('click', handleFirstInteraction);
  }

    onMount(() => {
    try {
      const path = typeof window !== 'undefined' ? (window.location?.pathname || '') : '';
      trackRun = path.startsWith('/play/');
    } catch (_) {
      trackRun = false;
    }
    syncFromStorage();
    currentRunId = get(activeRunId);
    if (trackRun && currentRunId) {
      const run = getRun(currentRunId);
      if (run) {
        const storedFocus = Number(run.judgeFocus);
        if (Number.isFinite(storedFocus)) judgeFocus = Math.min(1, Math.max(0, storedFocus));
        if (typeof run.languageOverride === 'string' && run.languageOverride.trim()) {
          languageOverride = run.languageOverride;
        }
        if (typeof run.score === 'number') {
          score = Math.max(0, Math.floor(run.score));
        }
        const storedLivesTotal = Number(run.livesTotal);
        if (Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) {
          livesTotal = Math.floor(storedLivesTotal);
        }
        const storedLivesRemaining = Number(run.livesRemaining);
        if (Number.isFinite(storedLivesRemaining) && storedLivesRemaining >= 0) {
          lives = Math.max(0, Math.min(livesTotal, Math.floor(storedLivesRemaining)));
          runLivesInitialized = true;
        } else if (Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) {
          lives = Math.max(0, Math.min(livesTotal, livesTotal));
          runLivesInitialized = true;
        }
        lastSavedScore = score;
        lastSavedLivesTotal = livesTotal;
        lastSavedLivesRemaining = lives;
      }
    }
    unsubRun = activeRunId.subscribe((id) => {
      if (trackRun && id && id !== lastRunIdForState) {
        const run = getRun(id);
        penaltyMessage = '';
        runLivesInitialized = false;
        if (run) {
          const storedFocus = Number(run.judgeFocus);
          if (Number.isFinite(storedFocus)) judgeFocus = Math.min(1, Math.max(0, storedFocus));
          if (typeof run.languageOverride === 'string' && run.languageOverride.trim()) {
            languageOverride = run.languageOverride;
          }
          if (typeof run.score === 'number') {
            score = Math.max(0, Math.floor(run.score));
          } else {
            score = 0;
          }
          const storedLivesTotal = Number(run.livesTotal);
          livesTotal = (Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) ? Math.floor(storedLivesTotal) : 3;
          const storedLivesRemaining = Number(run.livesRemaining);
          lives = (Number.isFinite(storedLivesRemaining) && storedLivesRemaining >= 0) ? Math.max(0, Math.min(livesTotal, Math.floor(storedLivesRemaining))) : livesTotal;
          runLivesInitialized = true;
        } else {
          score = 0;
          livesTotal = 3;
          lives = 3;
        }
        lastSavedScore = score;
        lastSavedLivesTotal = livesTotal;
        lastSavedLivesRemaining = lives;
        lastRunIdForState = id;
      }
      currentRunId = id;
    });

    // Dev back button visibility: only in dev build or URL/localStorage flag
    try {
      devMode = (import.meta?.env?.DEV === true) || /[?&]dev=1\b/.test(window.location.search) || localStorage.getItem('DEV_BACK') === '1';
    } catch (_) {}
    try {
      micDeviceId = String(localStorage.getItem(MIC_KEY) || '').trim();
    } catch (_) {}
    refreshMicDevices();
    try {
      navigator?.mediaDevices?.addEventListener?.('devicechange', refreshMicDevices);
    } catch (_) {}
    if ($storyStore.audio_to_play_url) {
        audioPlayer.src = $storyStore.audio_to_play_url;
    }
    window.addEventListener('click', handleFirstInteraction);

    // Resolve backend dynamically if needed
    discoverBackend().catch(() => {});

    streamMode = getStreamMode();
    resetStreamState(streamMode !== 'off' && isLiveScenario);
    try {
      const stored = localStorage.getItem('JUDGE_FOCUS');
      if (stored != null && String(stored).trim() !== '') {
        const v = Number(stored);
        if (Number.isFinite(v)) judgeFocus = Math.min(1, Math.max(0, v));
      }
    } catch (_) {}
    try {
      const stored = localStorage.getItem('LANGUAGE_OVERRIDE');
      if (stored != null) languageOverride = String(stored);
    } catch (_) {}

    // Client-only fetching of speaking suggestions on scenario changes
    let lastScenarioId = null;
    const fetchSuggestions = async (sid) => {
      try {
        const url = `${getBackendUrl()}/narrative/options?scenario_id=${encodeURIComponent(sid)}&n_per_option=3&lang=${encodeURIComponent(effectiveTargetLang)}&native=${encodeURIComponent(nativeLang)}&stage=examples`;
        const res = await fetch(url);
        speakingSuggestions = res.ok ? await res.json() : null;
      } catch (e) {
        speakingSuggestions = null;
      }
    };
    const unsub = storyStore.subscribe((s) => {
      if (!s?.id) return;
      // Build local suggestions from scenario JSON if examples exist
      if (Array.isArray(s?.options) && s.options.some(o => Array.isArray(o.examples) && o.examples.length)) {
        localSuggestions = {
          question: 'What do you say?',
          options: s.options.map(o => ({
            option_text: o.text,
            style: o.style || null,
            next_scenario: o.next_scenario,
            examples: (o.examples || []).map(e => ({ native: e.native || '', target: e.target || '', pronunciation: e.pronunciation || '' }))
          }))
        };
      } else {
        localSuggestions = null;
      }

      if (s.id !== lastScenarioId) {
        lastScenarioId = s.id;
        penaltyMessage = '';
        requireRepeat = false;
        selectedOption = null;
        lastHeard = '';
        matchConfidence = null;
        matchType = '';
        evaluating = false;
        myNativeText = '';
        const scenarioLives = Number(s?.lives ?? s?.max_lives ?? s?.lives_total);
        if (Number.isFinite(scenarioLives) && scenarioLives > 0) {
          const nextTotal = Math.floor(scenarioLives);
          if (!runLivesInitialized) {
            resetLives(nextTotal);
            runLivesInitialized = true;
          } else if (nextTotal > 0 && nextTotal !== livesTotal) {
            livesTotal = nextTotal;
            lives = Math.min(lives, livesTotal);
          }
        } else if (!runLivesInitialized) {
          resetLives(livesTotal);
          runLivesInitialized = true;
        }
        const nextMode = (typeof s?.mode === 'string' && s.mode.trim().toLowerCase() === 'advanced') ? 'advanced' : 'beginner';
        const liveForScenario = nextMode === 'advanced' && streamMode !== 'off';
        closeStream('scenario_change');
        resetStreamState(liveForScenario);
        // Only fetch if no local examples available
        if (!localSuggestions) fetchSuggestions(s.id);
      }
    });
    return () => {
      unsub();
      window.removeEventListener('click', handleFirstInteraction);
      try {
        navigator?.mediaDevices?.removeEventListener?.('devicechange', refreshMicDevices);
      } catch (_) {}
    };
  });

  $: {
    try {
      localStorage.setItem('JUDGE_FOCUS', String(judgeFocus));
    } catch (_) {}
  }
  $: {
    try {
      localStorage.setItem('LANGUAGE_OVERRIDE', String(languageOverride));
    } catch (_) {}
  }
  $: {
    if (!trackRun || !currentRunId) {
      lastSavedJudgeFocus = null;
      lastSavedLanguageOverride = null;
    } else {
      const nextFocus = Math.min(1, Math.max(0, Number(judgeFocus)));
      const nextLang = String(languageOverride || '');
      if (nextFocus !== lastSavedJudgeFocus || nextLang !== lastSavedLanguageOverride) {
        updateRun(currentRunId, { judgeFocus: nextFocus, languageOverride: nextLang });
        lastSavedJudgeFocus = nextFocus;
        lastSavedLanguageOverride = nextLang;
      }
    }
  }
  $: {
    if (!trackRun || !currentRunId) {
      lastSavedScore = null;
      lastSavedLivesTotal = null;
      lastSavedLivesRemaining = null;
    } else {
      const nextScore = Math.max(0, Math.floor(Number(score) || 0));
      const nextLivesTotal = Math.max(1, Math.floor(Number(livesTotal) || 1));
      const nextLivesRemaining = Math.max(0, Math.min(nextLivesTotal, Math.floor(Number(lives) || 0)));
      if (
        nextScore !== lastSavedScore ||
        nextLivesTotal !== lastSavedLivesTotal ||
        nextLivesRemaining !== lastSavedLivesRemaining
      ) {
        updateRun(currentRunId, {
          score: nextScore,
          livesTotal: nextLivesTotal,
          livesRemaining: nextLivesRemaining,
        });
        lastSavedScore = nextScore;
        lastSavedLivesTotal = nextLivesTotal;
        lastSavedLivesRemaining = nextLivesRemaining;
      }
    }
  }

  onDestroy(() => {
    closeStream('component_destroy');
  });
  onDestroy(() => {
    try {
      if (unsubRun) unsubRun();
      unsubRun = null;
    } catch (_) {}
  });

  async function translateNativeText() {
    const t = (myNativeText || '').trim();
    if (!t) return;
    translating = true;
    try {
      const fd = new FormData();
      fd.append('native', 'English');
      fd.append('target', effectiveTargetLang);
      fd.append('text', t);
      const res = await fetch(`${getBackendUrl()}/narrative/translate`, { method: 'POST', body: fd });
      const data = res.ok ? await res.json() : null;
      if (data && (data.target || data.native)) {
        selectedOption = { next_scenario: null, example: { native: data.native || t, target: data.target || '', pronunciation: data.pronunciation || '' } };
        requireRepeat = true;
        playBeep();
      }
    } catch (e) {
      // ignore
    } finally {
      translating = false;
    }
  }

  async function toggleNativeRecording() {
    if (isNativeRecording) {
      if (nativeRecorder && nativeRecorder.state !== 'inactive') nativeRecorder.stop();
      isNativeRecording = false;
    } else {
      try {
        const audioConstraints = micDeviceId ? { deviceId: { exact: micDeviceId } } : true;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        nativeStream = stream;
        nativeRecorder = new MediaRecorder(stream);
        nativeRecorder.ondataavailable = (e) => { nativeChunks.push(e.data); };
        nativeRecorder.onstop = async () => {
          const blob = new Blob(nativeChunks, { type: 'audio/webm' });
          nativeChunks = [];
          try {
            nativeStream?.getTracks?.().forEach((t) => t.stop());
          } catch (_) {}
          nativeStream = null;
          const fd = new FormData();
          fd.append('native', 'English');
          fd.append('target', effectiveTargetLang);
          fd.append('audio_file', blob, 'native_recording.webm');
          try {
            const res = await fetch(`${getBackendUrl()}/narrative/translate`, { method: 'POST', body: fd });
            const data = res.ok ? await res.json() : null;
            if (data && (data.target || data.native)) {
              selectedOption = { next_scenario: null, example: { native: data.native || '', target: data.target || '', pronunciation: data.pronunciation || '' } };
              requireRepeat = true;
              playBeep();
            }
          } catch (_) {}
        };
        nativeChunks = [];
        nativeRecorder.start();
        isNativeRecording = true;
        refreshMicDevices();
      } catch (e) {
        alert('Microphone permission needed');
      }
    }
  }

</script>

<!-- The actual audio element, hidden from the user -->
<audio bind:this={audioPlayer}></audio>

<div class="scenario-container">
  <ScenarioHeader
    imageUrl={$storyStore.image_url}
    dialogueJp={$storyStore.character_dialogue_jp}
    dialogueEn={$storyStore.character_dialogue_en}
    description={$storyStore.description}
  />

  <ScenarioControls
    bind:waveCanvas
    {isRecording}
    {devMode}
    {micDevices}
    bind:micDeviceId
    mode={scenarioMode}
    on:toggle={toggleRecording}
    on:devBack={() => storyStore.goBack()}
    on:refreshMics={refreshMicDevices}
    on:micChange={persistMicChoice}
  />
  <div class={`timeline-instructions ${isLiveScenario ? 'live-mode' : 'time-stop'}`} role="status" aria-live="polite">
    {#if isLiveScenario}
      <div class="risk-callout">
        <strong>Live stream:</strong> Audio beams out as you speak. Stay in {effectiveTargetLang} or you’ll burn lives fast.
      </div>
      <div class="prep-callout">
        Translator + examples stay consequence-free between bursts. Lives only drop while the live mic is rolling.
      </div>
      {#if streamMode === 'off'}
        <div class="prep-callout caution">Streaming disabled in settings — time-stop fallback engaged.</div>
      {/if}
    {:else}
      <div class="risk-callout">
        <strong>High-stakes response:</strong> Pressing record risks a rewind if you’re wrong.
      </div>
      <div class="prep-callout">
        Prep tools below (examples, translate, make-your-own) freeze time—no lives lost while you plan.
      </div>
    {/if}
  </div>
  {#if lastHeard && !requireRepeat}
    <div class="heard">Heard: <em>{lastHeard}</em>{evaluating ? ' …' : ''}</div>
  {/if}

  <ScenarioStatus
    {lives}
    {livesTotal}
    {score}
    {penaltyMessage}
    confidence={matchConfidence}
    matchType={matchType}
    mode={scenarioMode}
  />

  <ScenarioOptionsPanel
    {requireRepeat}
    {selectedOption}
    {lastHeard}
    {evaluating}
    {lives}
    {localSuggestions}
    {speakingSuggestions}
    bind:myNativeText
    bind:judgeFocus
    bind:languageOverride
    {translating}
    {isNativeRecording}
    fallbackOptions={$storyStore.options ?? []}
    mode={scenarioMode}
    on:selectOption={handleOptionSelection}
    on:playPrompt={handlePlayPrompt}
    on:translate={translateNativeText}
    on:toggleNativeRecording={toggleNativeRecording}
  />
  <MockStreamPanel
    {streamingEnabled}
    {streamMode}
    {streamStatus}
    {liveTranscript}
    {streamEvents}
  />

</div>

<style>
  .scenario-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    max-width: 600px;
    margin: auto;
    font-family: sans-serif;
    text-align: center;
  }
.heard {
  font-size: 0.9rem;
  color: #374151;
  margin-bottom: 8px;
}

.timeline-instructions {
  width: 100%;
  max-width: 520px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #7c2d12;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  text-align: left;
  box-shadow: 0 6px 14px rgba(253, 186, 116, 0.2);
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.timeline-instructions.live-mode {
  background: #eef2ff;
  border-color: #c7d2fe;
  color: #312e81;
  box-shadow: 0 6px 14px rgba(99, 102, 241, 0.2);
}

.timeline-instructions .risk-callout {
  font-size: 0.95rem;
  margin-bottom: 4px;
}

.timeline-instructions .prep-callout {
  font-size: 0.9rem;
  color: inherit;
}

.timeline-instructions.live-mode .prep-callout {
  color: #4338ca;
}

.timeline-instructions .prep-callout.caution {
  margin-top: 6px;
  font-weight: 600;
  color: #b45309;
}
</style>
