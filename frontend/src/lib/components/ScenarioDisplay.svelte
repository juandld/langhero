<script>
  import { storyStore } from '$lib/storyStore.js';
  import { getBackendUrl, discoverBackend, getStreamMode } from '$lib/config';
  import { apiFetch } from '$lib/api';
  import { getAuthToken } from '$lib/auth';
  import { activeRunId, getRun, syncFromStorage, updateRun } from '$lib/runStore.js';
  import { profileStore } from '$lib/profileStore';
  import { onMount, onDestroy } from 'svelte';
  import { get } from 'svelte/store';
  import ScenarioHeader from './scenario/ScenarioHeader.svelte';
  import ScenarioStatus from './scenario/ScenarioStatus.svelte';
  import ScenarioOptionsPanel from './scenario/ScenarioOptionsPanel.svelte';
  import MockStreamPanel from './scenario/MockStreamPanel.svelte';
  import ScenarioControls from './scenario/ScenarioControls.svelte';
  import SocialToast from './SocialToast.svelte';
  import { normalizeLanguage } from '$lib/utils/language';
  import { STORAGE_KEYS } from '$lib/utils';
  import {
    getMicrophoneDevices,
    setupAudioAnalyser,
    disconnectAnalyser,
    playBeep
  } from '$lib/game/audioUtils';
  import { createStreamingManager } from '$lib/game/streamingManager';
  import { createGameState } from '$lib/game/gameStateStore';
  import { createPromptPlayer } from '$lib/game/audioPromptManager';

  // Initialize shared game state and streaming manager
  const gameState = createGameState();
  const {
    lives: livesStore,
    livesTotal: livesTotalStore,
    score: scoreStore,
    judgeFocus: judgeFocusStore,
    languageOverride: languageOverrideStore,
    penaltyMessage: penaltyMessageStore,
    lastHeard: lastHeardStore,
    matchConfidence: matchConfidenceStore,
    matchType: matchTypeStore,
    initialized: runLivesInitializedStore,
    isGameOver,
    resetLives,
    addScore,
    loseLife,
    applyUpdate: applyGameStateUpdate,
    applyResult: applyGameStateResult,
    clearPenalty,
    loadFromStorage: loadGameStateFromStorage,
    persistToStorage: persistGameStateToStorage,
    syncToRun,
    setRun,
    getState: getGameState
  } = gameState;

  // Local variables bound to stores for template use
  $: lives = $livesStore;
  $: livesTotal = $livesTotalStore;
  $: score = $scoreStore;
  $: penaltyMessage = $penaltyMessageStore;
  $: lastHeard = $lastHeardStore;
  $: matchConfidence = $matchConfidenceStore;
  $: matchType = $matchTypeStore;
  $: runLivesInitialized = $runLivesInitializedStore;

  // Two-way bindable variables that sync with stores
  let judgeFocus = 0;
  let languageOverride = '';

  // Sync stores -> local when stores change
  $: if ($judgeFocusStore !== judgeFocus) judgeFocus = $judgeFocusStore;
  $: if ($languageOverrideStore !== languageOverride) languageOverride = $languageOverrideStore;

  // Sync local -> stores when local changes (from child component bindings)
  $: judgeFocusStore.set(judgeFocus);
  $: languageOverrideStore.set(normalizeLanguage(languageOverride));

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
  $: effectiveTargetLang = languageOverride || targetLang;
  const nativeLang = 'English'; // TODO: make user-configurable
  let requireRepeat = false;
  let selectedOption = null; // { next_scenario, example: { native, target, audio } }
  let devMode = false;
  let evaluating = false;
  let micDevices = [];
  let micDeviceId = '';
  let recordingStream = null;
  let nativeStream = null;
  // Make-your-own line (native -> translate -> try)
  let myNativeText = '';
  let translating = false;
  let isNativeRecording = false;
  let nativeRecorder;
  let nativeChunks = [];
  let streamMode = 'real';
  let waveCanvas;
  let audioAnalyser = null;
  let scenarioMode = 'beginner';
  let trackRun = false;
  let currentRunId = null;
  let unsubRun = null;
  let lastRunIdForState = null;
  let lastSavedScore = null;
  let lastSavedLivesTotal = null;
  let lastSavedLivesRemaining = null;
  let lastSavedJudgeFocus = null;
  let lastSavedLanguageOverride = null;

  // Initialize streaming manager
  const streamingManager = createStreamingManager({
    getScenario: () => get(storyStore),
    getLanguage: () => effectiveTargetLang,
    getGameState: () => getGameState(),
    onStateUpdate: applyGameStateUpdate,
    onTranscript: (text) => { /* transcript handled via store subscription */ },
    onResult: (result, opts) => applyInteractionResult(result, opts),
    onPenalty: (data) => {
      if (lives === 0) {
        alert('Out of lives. Try a different option.');
        requireRepeat = false;
      }
    },
    onError: (err) => console.error('[Stream] error:', err)
  });

  // Subscribe to streaming manager stores
  const { status: streamStatusStore, events: streamEventsStore, transcript: streamTranscriptStore } = streamingManager;
  $: streamStatus = $streamStatusStore;
  $: streamEvents = $streamEventsStore;
  $: liveTranscript = $streamTranscriptStore;
  $: streamingEnabled = streamingManager.isEnabled();

  // Social feedback toast state
  let showToast = false;
  let toastMessage = '';
  let toastStyleGained = '';
  let toastSentiment = 'neutral';
  let toastKey = 0; // Forces new toast component on each trigger

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

  // Reactive: enable/disable streaming based on mode
  $: {
    const shouldStream = streamMode !== 'off' && isLiveScenario;
    if (streamingManager.isEnabled() !== shouldStream) {
      streamingManager.setEnabled(shouldStream);
      streamingManager.setMode(streamMode);
    }
  }

  function handleOptionSelection(event) {
    const detail = event?.detail || {};
    const nextScenario = detail.next_scenario ?? detail.nextScenario ?? null;
    const example = detail.example || null;
    selectedOption = { next_scenario: nextScenario, example };
    requireRepeat = true;
    lastHeardStore.set('');
    playPrompt(example);
  }

  const handlePlayPrompt = () => playPrompt(selectedOption?.example);

  async function refreshMicDevices() {
    try {
      const devices = await getMicrophoneDevices();
      micDevices = devices;
      if (micDeviceId && !devices.some((d) => d.deviceId === micDeviceId)) {
        micDeviceId = '';
        try { localStorage.removeItem(STORAGE_KEYS.MIC_DEVICE_ID); } catch (_) {}
      }
    } catch (_) {}
  }

  function persistMicChoice() {
    try {
      const id = String(micDeviceId || '').trim();
      if (!id) localStorage.removeItem(STORAGE_KEYS.MIC_DEVICE_ID);
      else localStorage.setItem(STORAGE_KEYS.MIC_DEVICE_ID, id);
    } catch (_) {}
  }

  // Use shared audio prompt player
  const playPrompt = createPromptPlayer({
    getAudioPlayer: () => audioPlayer,
    getLanguage: () => effectiveTargetLang
  });

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

    // Apply result to game state (handles lastHeard, matchConfidence, matchType, score, lives)
    applyGameStateResult(result);

    if (!fromStream) {
      const deltaScore = Number(result?.scoreDelta ?? 0);
      if (Number.isFinite(deltaScore) && deltaScore !== 0) {
        addScore(Math.round(deltaScore));
      }
      const deltaLives = Number(result?.livesDelta ?? 0);
      if (Number.isFinite(deltaLives) && deltaLives !== 0) {
        loseLife(-deltaLives); // loseLife subtracts, so negate
        if (get(livesStore) <= 0) {
          requireRepeat = false;
        }
      }
      if (result?.error) {
        penaltyMessageStore.set(String(result.error));
      } else if (typeof result?.message === 'string' && result.message.trim()) {
        penaltyMessageStore.set(result.message.trim());
      } else {
        clearPenalty();
      }
    }

    // Show social feedback toast if present
    if (result?.socialFeedback) {
      toastMessage = result.socialFeedback;
      toastStyleGained = result?.styleGained || '';
      toastSentiment = result?.socialSentiment || 'neutral';
      toastKey += 1;
      showToast = true;
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

      // Update player profile on successful scenario completion
      const styleGained = result?.styleGained || null;
      const stylePoints = Number(result?.stylePoints ?? 1);
      profileStore.completeScenario(styleGained, stylePoints);

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
          streamingManager.signalStop('stop');
        }
        mediaRecorder.stop();
      }
      isRecording = false;
      // Clean up analyser
      audioAnalyser = null;
      disconnectAnalyser();
    } else {
      // Start recording
      try {
        const audioConstraints = micDeviceId ? { deviceId: { exact: micDeviceId } } : true;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        recordingStream = stream;
        mediaRecorder = new MediaRecorder(stream);

        // Setup audio analyser for waveform visualization
        audioAnalyser = setupAudioAnalyser(stream);

        mediaRecorder.ondataavailable = async event => {
          if (!event?.data) return;
          audioChunks.push(event.data);
          if (streamingEnabled) {
            await streamingManager.sendChunk(event.data);
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
              lastHeardStore.set('');
              matchConfidenceStore.set(null);
              matchTypeStore.set('');
              formData.append('expected', selectedOption.example?.target || '');
              if (selectedOption.next_scenario != null) formData.append('next_scenario', String(selectedOption.next_scenario));
              if (effectiveTargetLang) formData.append('lang', effectiveTargetLang);
              formData.append('judge', String(judgeFocus));
              const response = await apiFetch(`${getBackendUrl()}/narrative/imitate`, { method: 'POST', body: formData });
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              const result = await response.json();
              applyInteractionResult(result);
            } else {
              formData.append('current_scenario_id', $storyStore.id);
              if (effectiveTargetLang) formData.append('lang', effectiveTargetLang);
              formData.append('judge', String(judgeFocus));
              const response = await apiFetch(`${getBackendUrl()}/narrative/interaction`, { method: 'POST', body: formData });
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
          clearPenalty();
          streamingManager.connect();
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
        if (Number.isFinite(storedFocus)) judgeFocusStore.set(Math.min(1, Math.max(0, storedFocus)));
        if (typeof run.languageOverride === 'string' && run.languageOverride.trim()) {
          languageOverrideStore.set(run.languageOverride);
        }
        if (typeof run.score === 'number') {
          scoreStore.set(Math.max(0, Math.floor(run.score)));
        }
        const storedLivesTotal = Number(run.livesTotal);
        if (Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) {
          livesTotalStore.set(Math.floor(storedLivesTotal));
        }
        const storedLivesRemaining = Number(run.livesRemaining);
        const currentLivesTotal = get(livesTotalStore);
        if (Number.isFinite(storedLivesRemaining) && storedLivesRemaining >= 0) {
          livesStore.set(Math.max(0, Math.min(currentLivesTotal, Math.floor(storedLivesRemaining))));
          runLivesInitializedStore.set(true);
        } else if (Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) {
          livesStore.set(Math.max(0, currentLivesTotal));
          runLivesInitializedStore.set(true);
        }
        lastSavedScore = get(scoreStore);
        lastSavedLivesTotal = get(livesTotalStore);
        lastSavedLivesRemaining = get(livesStore);
      }
    }
    unsubRun = activeRunId.subscribe((id) => {
      if (trackRun && id && id !== lastRunIdForState) {
        const run = getRun(id);
        clearPenalty();
        runLivesInitializedStore.set(false);
        if (run) {
          const storedFocus = Number(run.judgeFocus);
          if (Number.isFinite(storedFocus)) judgeFocusStore.set(Math.min(1, Math.max(0, storedFocus)));
          if (typeof run.languageOverride === 'string' && run.languageOverride.trim()) {
            languageOverrideStore.set(run.languageOverride);
          }
          if (typeof run.score === 'number') {
            scoreStore.set(Math.max(0, Math.floor(run.score)));
          } else {
            scoreStore.set(0);
          }
          const storedLivesTotal = Number(run.livesTotal);
          livesTotalStore.set((Number.isFinite(storedLivesTotal) && storedLivesTotal > 0) ? Math.floor(storedLivesTotal) : 3);
          const storedLivesRemaining = Number(run.livesRemaining);
          const currentLivesTotal = get(livesTotalStore);
          livesStore.set((Number.isFinite(storedLivesRemaining) && storedLivesRemaining >= 0) ? Math.max(0, Math.min(currentLivesTotal, Math.floor(storedLivesRemaining))) : currentLivesTotal);
          runLivesInitializedStore.set(true);
        } else {
          scoreStore.set(0);
          livesTotalStore.set(3);
          livesStore.set(3);
        }
        lastSavedScore = get(scoreStore);
        lastSavedLivesTotal = get(livesTotalStore);
        lastSavedLivesRemaining = get(livesStore);
        lastRunIdForState = id;
      }
      currentRunId = id;
    });

    // Dev back button visibility: only in dev build or URL/localStorage flag
    try {
      devMode = (import.meta?.env?.DEV === true) || /[?&]dev=1\b/.test(window.location.search) || localStorage.getItem('DEV_BACK') === '1';
    } catch (_) {}
    try {
      micDeviceId = String(localStorage.getItem(STORAGE_KEYS.MIC_DEVICE_ID) || '').trim();
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

    // Listen for rank up events
    const handleRankUp = (e) => {
      const { newRank } = e.detail || {};
      if (newRank) {
        toastMessage = `Congratulations! You've become a ${newRank}!`;
        toastStyleGained = '';
        toastSentiment = 'positive';
        toastKey += 1;
        showToast = true;
      }
    };
    window.addEventListener('langhero:rankup', handleRankUp);

    streamMode = getStreamMode();
    streamingManager.setMode(streamMode);
    streamingManager.setEnabled(streamMode !== 'off' && isLiveScenario);
    try {
      const stored = localStorage.getItem('JUDGE_FOCUS');
      if (stored != null && String(stored).trim() !== '') {
        const v = Number(stored);
        if (Number.isFinite(v)) judgeFocusStore.set(Math.min(1, Math.max(0, v)));
      }
    } catch (_) {}
    try {
      const stored = localStorage.getItem('LANGUAGE_OVERRIDE');
      if (stored != null) languageOverrideStore.set(String(stored));
    } catch (_) {}

    // Client-only fetching of speaking suggestions on scenario changes
    let lastScenarioId = null;
    const fetchSuggestions = async (sid) => {
      try {
        const url = `${getBackendUrl()}/narrative/options?scenario_id=${encodeURIComponent(sid)}&n_per_option=3&lang=${encodeURIComponent(effectiveTargetLang)}&native=${encodeURIComponent(nativeLang)}&stage=examples`;
        const res = await apiFetch(url);
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
        clearPenalty();
        requireRepeat = false;
        selectedOption = null;
        lastHeardStore.set('');
        matchConfidenceStore.set(null);
        matchTypeStore.set('');
        evaluating = false;
        myNativeText = '';
        const scenarioLives = Number(s?.lives ?? s?.max_lives ?? s?.lives_total);
        if (Number.isFinite(scenarioLives) && scenarioLives > 0) {
          const nextTotal = Math.floor(scenarioLives);
          if (!runLivesInitialized) {
            resetLives(nextTotal);
          } else if (nextTotal > 0 && nextTotal !== livesTotal) {
            livesTotalStore.set(nextTotal);
            livesStore.update(l => Math.min(l, nextTotal));
          }
        } else if (!runLivesInitialized) {
          resetLives(livesTotal);
        }
        const nextMode = (typeof s?.mode === 'string' && s.mode.trim().toLowerCase() === 'advanced') ? 'advanced' : 'beginner';
        const liveForScenario = nextMode === 'advanced' && streamMode !== 'off';
        streamingManager.close('scenario_change');
        streamingManager.setEnabled(liveForScenario);
        // Only fetch if no local examples available
        if (!localSuggestions) fetchSuggestions(s.id);
      }
    });
    return () => {
      unsub();
      window.removeEventListener('click', handleFirstInteraction);
      window.removeEventListener('langhero:rankup', handleRankUp);
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
    streamingManager.close('component_destroy');
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
      const res = await apiFetch(`${getBackendUrl()}/narrative/translate`, { method: 'POST', body: fd });
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
            const res = await apiFetch(`${getBackendUrl()}/narrative/translate`, { method: 'POST', body: fd });
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

<!-- Social feedback toast -->
{#if showToast}
  {#key toastKey}
    <SocialToast
      message={toastMessage}
      styleGained={toastStyleGained}
      sentiment={toastSentiment}
      onDismiss={() => { showToast = false; }}
    />
  {/key}
{/if}

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
    {evaluating}
    {devMode}
    {micDevices}
    bind:micDeviceId
    mode={scenarioMode}
    analyser={audioAnalyser}
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
