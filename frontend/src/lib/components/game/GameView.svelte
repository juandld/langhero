<script>
  import { storyStore } from '$lib/storyStore.js';
  import { getBackendUrl, discoverBackend, getStreamMode } from '$lib/config';
  import { apiFetch } from '$lib/api';
  import { getAuthToken } from '$lib/auth';
  import { activeRunId, getRun, syncFromStorage, updateRun } from '$lib/runStore.js';
  import { profileStore } from '$lib/profileStore';
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
  import { get } from 'svelte/store';
  import GameHUD from './GameHUD.svelte';
  import GameScene from './GameScene.svelte';
  import DialogueBox from './DialogueBox.svelte';
  import TimeStopPanel from './TimeStopPanel.svelte';
  import SpeakButton from './SpeakButton.svelte';
  import GameMenu from './GameMenu.svelte';
  import GameAssistant from './GameAssistant.svelte';
  import IntroSequence from './IntroSequence.svelte';
  import SocialToast from '../SocialToast.svelte';
  import VolumeControl from './VolumeControl.svelte';
  import { masterVolume, playbackSpeed } from '$lib/audioStore.js';
  import { normalizeLanguage } from '$lib/utils/language';
  import { toBackendUrl, STORAGE_KEYS } from '$lib/utils';
  import { fetchTtsUrl } from '$lib/utils/ttsCache';
  import {
    getMicrophoneDevices,
    setupAudioAnalyser,
    disconnectAnalyser,
    playBeep
  } from '$lib/game/audioUtils';
  import { createStreamingManager } from '$lib/game/streamingManager';
  import { createGameState } from '$lib/game/gameStateStore';
  import { createPromptPlayer } from '$lib/game/audioPromptManager';

  export let showBackdrop = true;
  export let transparentBackground = false;

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

  let audioPlayer;
  let isRecording = false;
  let mediaRecorder;
  let audioChunks = [];
  let audioBlob = null;
  let speakingSuggestions = null;
  let localSuggestions = null;

  $: targetLang = ($storyStore?.language && typeof $storyStore.language === 'string' && $storyStore.language.trim())
    ? $storyStore.language
    : ($storyStore?.character_dialogue_jp ? 'Japanese' : 'English');

  $: effectiveTargetLang = languageOverride || targetLang;
  const nativeLang = 'English';

  let requireRepeat = false;
  let selectedOption = null;
  let evaluating = false;
  let micDevices = [];
  let micDeviceId = '';
  let recordingStream = null;
  let streamMode = 'real';
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

  // Menu state
  let menuVisible = false;

  // Intro state
  const INTRO_SEEN_KEY = 'LANGHERO_INTRO_SEEN_V1';
  let showIntro = false;

  // Assistant state
  let assistantMessage = '';
  let showAssistantTools = true;

  // Social feedback toast state
  let showToast = false;
  let toastMessage = '';
  let toastStyleGained = '';
  let toastSentiment = 'neutral';
  let toastKey = 0;

  $: scenarioMode = (() => {
    const raw = typeof $storyStore?.mode === 'string' ? $storyStore.mode : '';
    if (typeof raw === 'string') {
      const normalized = raw.trim().toLowerCase();
      if (normalized === 'advanced') return 'advanced';
      if (normalized === 'beginner') return 'beginner';
    }
    return 'beginner';
  })();

  $: isTimeStopped = scenarioMode !== 'advanced';
  $: isLiveScenario = scenarioMode === 'advanced';

  // Format options for TimeStopPanel
  $: formattedOptions = (() => {
    const source = localSuggestions || speakingSuggestions;
    if (!source?.options) return [];
    return source.options.map(o => ({
      option_text: o.option_text || o.text,
      style: o.style || null,
      next_scenario: o.next_scenario,
      examples: o.examples || []
    }));
  })();

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

  // Create prompt player using shared audio prompt manager
  const playPrompt = createPromptPlayer({
    getAudioPlayer: () => audioPlayer,
    getLanguage: () => effectiveTargetLang
  });

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
      const styleGained = result?.styleGained || null;
      const stylePoints = Number(result?.stylePoints ?? 1);
      profileStore.completeScenario(styleGained, stylePoints);

      // Get current scenario ID before transitioning
      const currentScenarioId = $storyStore?.id;
      let nextScenarioId = null;

      if (typeof next === 'object' && next?.id) {
        nextScenarioId = next.id;
        storyStore.goToScenario(next.id);
      } else if (typeof next === 'number') {
        nextScenarioId = next;
        storyStore.goToScenario(next);
      }

      // Dispatch scenario completion event for story orchestration
      dispatch('scenarioComplete', {
        scenarioId: currentScenarioId,
        nextScenarioId,
      });

      requireRepeat = false;
    } else {
      playBeep({ frequency: 440, duration: 160 });
    }
    evaluating = false;
  }

  async function toggleRecording() {
    if (isRecording) {
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        if (streamingEnabled) {
          streamingManager.signalStop('stop');
        }
        mediaRecorder.stop();
      }
      isRecording = false;
      audioAnalyser = null;
      disconnectAnalyser();
    } else {
      try {
        const audioConstraints = micDeviceId ? { deviceId: { exact: micDeviceId } } : true;
        const stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        recordingStream = stream;
        mediaRecorder = new MediaRecorder(stream);
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

  function openMenu() {
    menuVisible = true;
  }

  function closeMenu() {
    menuVisible = false;
  }

  function handleMenuExit() {
    menuVisible = false;
    window.location.href = '/';
  }

  function handleUpdateJudgeFocus(event) {
    judgeFocus = event.detail;
  }

  function handleUpdateLanguage(event) {
    languageOverride = normalizeLanguage(event.detail);
  }

  function handleUpdateMic(event) {
    micDeviceId = event.detail;
    persistMicChoice();
  }

  function handlePlayAudio() {
    playPrompt(selectedOption?.example);
  }

  // Assistant handlers
  function handleAssistantTranslate() {
    // TODO: Open translate panel or trigger translation
    assistantMessage = "Type what you want to say in English, and I'll translate it for you.";
  }

  function handleAssistantHearExample() {
    if (selectedOption?.example) {
      playPrompt(selectedOption.example);
      assistantMessage = "Listen carefully and repeat what you hear.";
    } else if (formattedOptions.length > 0 && formattedOptions[0].examples?.length > 0) {
      playPrompt(formattedOptions[0].examples[0]);
      assistantMessage = "Here's one way to respond.";
    }
  }

  function handleAssistantHint() {
    // Provide contextual hints with thematic flavor
    if (requireRepeat) {
      assistantMessage = "Match the rhythm, the rise and fall. Close enough will save your life.";
    } else if (formattedOptions.length > 0) {
      const randomOption = formattedOptions[Math.floor(Math.random() * formattedOptions.length)];
      if (randomOption.examples?.length > 0) {
        assistantMessage = `Perhaps try: "${randomOption.examples[0].target}" — it might keep your head attached.`;
      }
    } else {
      assistantMessage = "A bow, a greeting, anything. Silence is often mistaken for defiance here.";
    }
  }

  function handleIntroComplete() {
    showIntro = false;
    try {
      localStorage.setItem(INTRO_SEEN_KEY, '1');
    } catch (_) {}
  }

  function handleReplayTutorial() {
    try {
      localStorage.removeItem(INTRO_SEEN_KEY);
    } catch (_) {}
    showIntro = true;
  }

  // Keyboard shortcut
  function handleKeydown(event) {
    if (event.key === 'Escape') {
      if (menuVisible) {
        closeMenu();
      } else {
        openMenu();
      }
    }
  }

  onMount(() => {
    // Check if intro has been seen
    try {
      const introSeen = localStorage.getItem(INTRO_SEEN_KEY);
      showIntro = !introSeen;
    } catch (_) {
      showIntro = true;
    }

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
          livesStore.set(currentLivesTotal);
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
          livesStore.set((Number.isFinite(storedLivesRemaining) && storedLivesRemaining >= 0)
            ? Math.max(0, Math.min(currentLivesTotal, Math.floor(storedLivesRemaining)))
            : currentLivesTotal);
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

    try {
      micDeviceId = String(localStorage.getItem(STORAGE_KEYS.MIC_DEVICE_ID) || '').trim();
    } catch (_) {}
    refreshMicDevices();
    try {
      navigator?.mediaDevices?.addEventListener?.('devicechange', refreshMicDevices);
    } catch (_) {}

    discoverBackend().catch(() => {});

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
    window.addEventListener('keydown', handleKeydown);

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
      if (Array.isArray(s?.options) && s.options.some(o => Array.isArray(o.examples) && o.examples.length)) {
        localSuggestions = {
          question: 'What do you say?',
          options: s.options.map(o => ({
            option_text: o.text,
            style: o.style || null,
            next_scenario: o.next_scenario,
            examples: (o.examples || []).map(e => ({
              native: e.native || '',
              target: e.target || '',
              pronunciation: e.pronunciation || ''
            }))
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
        if (!localSuggestions) fetchSuggestions(s.id);
      }
    });

    return () => {
      unsub();
      window.removeEventListener('langhero:rankup', handleRankUp);
      window.removeEventListener('keydown', handleKeydown);
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

  $: profile = $profileStore;
  $: scenariosCompleted = profile?.scenariosCompleted || 0;

  // Keep audio player in sync with audio settings
  $: if (audioPlayer) {
    audioPlayer.volume = $masterVolume;
    audioPlayer.playbackRate = $playbackSpeed;
  }
</script>

<audio bind:this={audioPlayer}></audio>

<IntroSequence
  visible={showIntro}
  on:complete={handleIntroComplete}
/>

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

<GameMenu
  visible={menuVisible}
  {judgeFocus}
  {languageOverride}
  {micDevices}
  {micDeviceId}
  {scenariosCompleted}
  on:close={closeMenu}
  on:updateJudgeFocus={handleUpdateJudgeFocus}
  on:updateLanguage={handleUpdateLanguage}
  on:updateMic={handleUpdateMic}
  on:replayTutorial={handleReplayTutorial}
  on:exit={handleMenuExit}
/>

<GameAssistant
  visible={!menuVisible}
  message={assistantMessage}
  {isTimeStopped}
  showTools={showAssistantTools}
  {requireRepeat}
  on:translate={handleAssistantTranslate}
  on:hearExample={handleAssistantHearExample}
  on:hint={handleAssistantHint}
/>

<div class="game-view" class:transparent={transparentBackground}>
  <div class="scene-layer">
    {#if showBackdrop}
      <GameScene
        imageUrl={$storyStore.image_url || $storyStore.ai_image_url}
        {isTimeStopped}
      />
    {/if}
    <GameHUD
      {lives}
      {livesTotal}
      {score}
      on:openMenu={openMenu}
    />
    <div class="volume-container">
      <VolumeControl />
    </div>
  </div>

  <div class="ui-layer">
    <div class="dialogue-area">
      <DialogueBox
        speakerEmoji=""
        dialogueTarget={$storyStore.character_dialogue_jp || ''}
        dialogueNative={$storyStore.character_dialogue_en || ''}
      />
    </div>

    {#if isTimeStopped}
      <div class="choices-area">
        <TimeStopPanel
          options={formattedOptions}
          {selectedOption}
          {requireRepeat}
          on:selectOption={handleOptionSelection}
          on:playAudio={handlePlayAudio}
        />
      </div>
    {:else}
      <div class="live-indicator">
        <span class="live-dot"></span>
        <span class="live-text">LIVE - Respond naturally</span>
      </div>
    {/if}

    {#if penaltyMessage}
      <div class="penalty-message" role="alert">
        {penaltyMessage}
      </div>
    {/if}

    {#if lastHeard && !requireRepeat}
      <div class="heard-text">
        Heard: <em>{lastHeard}</em>
      </div>
    {/if}

    <div class="speak-area">
      <SpeakButton
        {isRecording}
        isEvaluating={evaluating}
        {isTimeStopped}
        analyser={audioAnalyser}
        on:toggle={toggleRecording}
      />
    </div>
  </div>
</div>

<style>
  .game-view {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    background: #0f172a;
    font-family: system-ui, -apple-system, sans-serif;
    overflow: hidden;
  }

  .game-view.transparent {
    background: transparent;
  }

  .scene-layer {
    position: relative;
    flex: 1;
    min-height: 0;
    overflow: hidden;
  }

  .volume-container {
    position: absolute;
    top: 16px;
    left: 16px;
    z-index: 50;
  }

  .ui-layer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 16px;
    padding-bottom: max(16px, env(safe-area-inset-bottom));
    background: linear-gradient(
      to top,
      rgba(15, 23, 42, 0.95) 0%,
      rgba(15, 23, 42, 0.8) 50%,
      transparent 100%
    );
    pointer-events: none;
  }

  .ui-layer > * {
    pointer-events: auto;
  }

  .dialogue-area {
    margin-bottom: 4px;
  }

  .choices-area {
    margin-bottom: 4px;
  }

  .live-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 10px 20px;
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 20px;
    margin: 0 auto;
    max-width: fit-content;
  }

  .live-dot {
    width: 10px;
    height: 10px;
    background: #ef4444;
    border-radius: 50%;
    animation: pulse-live 1.5s ease-in-out infinite;
  }

  @keyframes pulse-live {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(0.9);
    }
  }

  .live-text {
    color: #fca5a5;
    font-size: 0.9rem;
    font-weight: 600;
    letter-spacing: 0.03em;
  }

  .penalty-message {
    text-align: center;
    padding: 10px 16px;
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 12px;
    color: #fca5a5;
    font-size: 0.95rem;
    font-weight: 500;
    max-width: 400px;
    margin: 0 auto;
  }

  .heard-text {
    text-align: center;
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.9rem;
  }

  .heard-text em {
    color: #e2e8f0;
  }

  .speak-area {
    display: flex;
    justify-content: center;
    padding-top: 8px;
  }

  /* Responsive adjustments */
  @media (max-height: 700px) {
    .ui-layer {
      gap: 8px;
      padding: 12px;
    }
  }

  @media (min-height: 800px) {
    .ui-layer {
      gap: 16px;
      padding: 24px;
    }
  }
</style>
