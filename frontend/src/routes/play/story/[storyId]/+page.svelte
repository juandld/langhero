<script>
  import { onMount, onDestroy } from 'svelte';
  import { page } from '$app/stores';
  import { browser } from '$app/environment';
  import { fade, fly, scale } from 'svelte/transition';
  import { getApiBase, getTTS } from '$lib/api';
  import { masterVolume, playbackSpeed } from '$lib/audioStore';
  import { STORAGE_KEYS, getString, getJson, setJson } from '$lib/utils/storage';
  import { createStreamingManager } from '$lib/game/streamingManager';
  import { createRecordingSession, ensureAudioContext, playBeep, setupAudioAnalyser, disconnectAnalyser } from '$lib/game/audioUtils';
  import { fetchTtsUrl } from '$lib/utils/ttsCache';

  // Game components
  import GameHUD from '$lib/components/game/GameHUD.svelte';
  import TimeStopPanel from '$lib/components/game/TimeStopPanel.svelte';
  import SpeakButton from '$lib/components/game/SpeakButton.svelte';
  import VolumeControl from '$lib/components/game/VolumeControl.svelte';
  import GameMenu from '$lib/components/game/GameMenu.svelte';

  const API_BASE = getApiBase();
  const AUTO_NARRATE_KEY = 'LANGHERO_AUTO_NARRATE_V1';

  // Story state
  let story = null;
  let voiceConfig = null;
  let loading = true;
  let error = null;

  // Navigation state
  let currentChapterIndex = 0;
  let currentPanelIndex = 0;

  // Game state
  let lives = 3;
  let livesTotal = 3;
  let score = 0;
  let choices = {};
  let gameOver = false;

  // Interaction state
  let isTimeFrozen = false;
  let canAdvance = true;
  let isPlaying = false;
  let autoNarrate = loadAutoNarrate();
  let userHasInteracted = false;

  // Options/speaking state
  let previewedOption = null;
  let selectedOption = null;
  let requireRepeat = false;
  let speakResult = null;
  let liveTranscript = '';
  let draftText = '';
  let bimboHint = null;
  let askingBimbo = false;

  // Speech recognition state
  let isRecording = false;
  let mediaRecorder = null;
  let audioChunks = [];
  let recordingStream = null;
  let audioAnalyser = null;
  let evaluating = false;
  let streamingManager = null;

  // Menu state
  let menuVisible = false;

  // Dev tools
  let devMenuOpen = false;
  let infiniteLives = false;
  let devAudioFile = null;
  let devInjecting = false;

  // Dev: Record Clip
  let devIsRecordingClip = false;
  let devClipRecorder = null;
  let devClipStream = null;
  let devClipChunks = [];
  let devClipDuration = 5;

  // Dev: Last Result Inspector
  let devLastResult = null;
  let devLastLang = '';

  // Dev: Auto-Inject on Freeze
  let devAutoInject = false;
  let devAutoInjectDelay = 500;
  let devAutoInjectTimeout = null;

  // Dev: Match Threshold Override
  let devMatchThreshold = 0.7;

  // Response Categories
  const RESPONSE_CATEGORIES = {
    diplomatic:       { label: 'Diplomatic',       color: '#86efac', icon: '🕊' },
    pragmatic:        { label: 'Pragmatic',        color: '#93c5fd', icon: '⚖' },
    bold:             { label: 'Bold',             color: '#fdba74', icon: '⚡' },
    hostile:          { label: 'Hostile',          color: '#fca5a5', icon: '🔥' },
    'history-breaking': { label: 'History-Breaking', color: '#e9d5ff', icon: '✦' },
  };

  const STYLE_TO_CATEGORY = {
    polite:      'diplomatic',
    charming:    'diplomatic',
    humble:      'diplomatic',
    friendly:    'diplomatic',

    cautious:    'pragmatic',
    honest:      'pragmatic',
    safe:        'pragmatic',
    vague:       'pragmatic',
    silent:      'pragmatic',
    obedient:    'pragmatic',
    curious:     'pragmatic',

    direct:      'bold',
    bold:        'bold',
    desperate:   'bold',

    hostile:     'hostile',
    defiant:     'hostile',
    threatening: 'hostile',

    insightful:  'history-breaking',
  };

  function getOptionCategory(option) {
    const style = option?.style || '';
    const key = STYLE_TO_CATEGORY[style] || 'pragmatic';
    return RESPONSE_CATEGORIES[key];
  }

  // Audio state
  let currentAudio = null;
  let audioQueue = [];
  let isProcessingQueue = false;
  let audioSessionId = 0;
  let activeSubscriptions = [];
  let audioPlayer;

  function loadAutoNarrate() {
    if (!browser) return true;
    try {
      const stored = localStorage.getItem(AUTO_NARRATE_KEY);
      if (stored !== null) return stored === 'true';
    } catch (_) {}
    return true;
  }

  $: storyId = $page.params.storyId;
  $: currentChapter = story?.chapters?.[currentChapterIndex];
  $: rawPanel = currentChapter?.panels?.[currentPanelIndex];
  $: currentPanel = resolvePanel(rawPanel, choices);
  $: totalPanels = story?.chapters?.reduce((sum, ch) => sum + ch.panels.length, 0) || 0;

  function resolvePanel(panel, playerChoices) {
    if (!panel || !panel.choice_variants) return panel;
    for (const [sourcePanelId, optionMap] of Object.entries(panel.choice_variants)) {
      const chosenIndex = playerChoices[sourcePanelId];
      if (chosenIndex !== undefined && optionMap[String(chosenIndex)]) {
        const variant = optionMap[String(chosenIndex)];
        return { ...panel, ...variant };
      }
    }
    return panel;
  }
  $: isLastPanel = currentChapterIndex === (story?.chapters?.length || 1) - 1 &&
                   currentPanelIndex === (currentChapter?.panels?.length || 1) - 1;

  // Check if this panel has options (triggers time freeze game mechanic)
  $: hasOptions = currentPanel?.options?.length > 0;
  // Time freeze only triggers when there are options to speak
  $: hasTimeFreeze = hasOptions;

  // Format options for TimeStopPanel
  $: formattedOptions = (() => {
    if (!currentPanel?.options) return [];
    return currentPanel.options.map(o => ({
      option_text: o.text,
      style: o.style || null,
      next_scenario: o.next_scenario,
      examples: o.examples || []
    }));
  })();

  // Track panel changes
  let lastPanelId = null;
  $: if (currentPanel?.id && currentPanel.id !== lastPanelId) {
    lastPanelId = currentPanel.id;
    // Reset state on panel change
    previewedOption = null;
    selectedOption = null;
    requireRepeat = false;
    speakResult = null;
    liveTranscript = '';
    draftText = '';
    bimboHint = null;
    askingBimbo = false;

    // Check if we should freeze time
    if (hasTimeFreeze && !isTimeFrozen) {
      triggerTimeFreeze();
      // Dev: auto-inject audio on freeze
      if (devAutoInject && devAudioFile) {
        if (devAutoInjectTimeout) clearTimeout(devAutoInjectTimeout);
        devAutoInjectTimeout = setTimeout(() => { injectAudio(); devAutoInjectTimeout = null; }, devAutoInjectDelay);
      }
    } else if (!hasTimeFreeze && isTimeFrozen) {
      resumeTime();
    }

    // Auto-narrate if enabled - play on ALL panels including time freeze
    if (autoNarrate && userHasInteracted) {
      setTimeout(() => autoPlayPanel(), 100);
    }
  }

  // Calculate progress
  $: currentPanelNumber = (() => {
    if (!story) return 0;
    let count = 0;
    for (let i = 0; i < currentChapterIndex; i++) {
      count += story.chapters[i].panels.length;
    }
    return count + currentPanelIndex + 1;
  })();

  $: progress = totalPanels > 0 ? (currentPanelNumber / totalPanels) * 100 : 0;

  // Dev: Flat panel list for jump navigator
  $: devPanelList = (() => {
    if (!story?.chapters) return [];
    const list = [];
    story.chapters.forEach((ch, ci) => {
      ch.panels.forEach((p, pi) => {
        const firstOpt = p.options?.[0] || null;
        const catColor = firstOpt ? getOptionCategory(firstOpt).color : null;
        list.push({ chapterIdx: ci, panelIdx: pi, id: p.id, hasOptions: p.options?.length > 0, catColor });
      });
    });
    return list;
  })();

  function saveProgress() {
    if (!storyId) return;
    setJson(STORAGE_KEYS.STORY_PROGRESS, {
      storyId,
      chapterIndex: currentChapterIndex,
      panelIndex: currentPanelIndex,
      score,
      lives,
      livesTotal,
      choices,
    });
  }

  function loadProgress() {
    const saved = getJson(STORAGE_KEYS.STORY_PROGRESS, null);
    if (!saved || saved.storyId !== storyId) return;
    currentChapterIndex = saved.chapterIndex ?? 0;
    currentPanelIndex = saved.panelIndex ?? 0;
    score = saved.score ?? 0;
    lives = saved.lives ?? 3;
    livesTotal = saved.livesTotal ?? 3;
    choices = saved.choices ?? {};
    if (lives <= 0) gameOver = true;
  }

  function resetGame() {
    currentChapterIndex = 0;
    currentPanelIndex = 0;
    score = 0;
    lives = 3;
    livesTotal = 3;
    choices = {};
    gameOver = false;
    isTimeFrozen = false;
    canAdvance = true;
    previewedOption = null;
    selectedOption = null;
    requireRepeat = false;
    speakResult = null;
    liveTranscript = '';
    draftText = '';
    bimboHint = null;
    askingBimbo = false;
    stopAudio();
    cleanupRecording();
    saveProgress();
  }

  onMount(async () => {
    autoNarrate = loadAutoNarrate();

    try {
      const [storyRes, voiceRes] = await Promise.all([
        fetch(`${API_BASE}/api/story-panels/stories/${storyId}`),
        fetch(`${API_BASE}/api/story-panels/stories/${storyId}/voice-config`)
      ]);

      if (!storyRes.ok) throw new Error('Story not found');
      story = await storyRes.json();

      if (voiceRes.ok) {
        voiceConfig = await voiceRes.json();
      }

      // Restore saved progress after story loads
      loadProgress();
    } catch (e) {
      error = e.message;
    } finally {
      loading = false;
    }
  });

  onDestroy(() => {
    stopAudio();
    cleanupRecording();
    if (streamingManager) {
      streamingManager.close();
    }
    // Dev cleanup
    if (devClipRecorder && devClipRecorder.state !== 'inactive') {
      try { devClipRecorder.stop(); } catch (_) {}
    }
    if (devClipStream) {
      devClipStream.getTracks().forEach(t => t.stop());
    }
    if (devAutoInjectTimeout) clearTimeout(devAutoInjectTimeout);
  });

  // Initialize streaming manager for speech recognition
  function initStreamingManager() {
    if (streamingManager) return;

    streamingManager = createStreamingManager({
      getScenario: () => {
        // Always free-speak: send all option targets for best-match
        if (currentPanel?.options?.length > 0) {
          const targets = currentPanel.options
            .map(o => o.examples?.[0]?.target)
            .filter(Boolean);
          if (targets.length > 0) {
            return { id: null, expected_responses: targets };
          }
        }
        return null;
      },
      getLanguage: () => 'Japanese',
      getGameState: () => ({ score, lives, livesTotal, judgeFocus: 0 }),
      onStateUpdate: () => {},
      onTranscript: (text, partial) => {
        liveTranscript = text;
        if (partial?.detected_language) devLastLang = partial.detected_language;
      },
      onResult: (result) => {
        console.log('[Speech] Result:', result);
        devLastResult = result;
        isRecording = false;
        evaluating = false;
        cleanupRecording();

        const matchLevel = result.match_level ?? 0;
        const tier = result.tier || (matchLevel >= 0.7 ? 'good' : 'fail');

        // Record matched option for all non-fail tiers
        if (tier !== 'fail') {
          const matchedIdx = result.matched_index;
          if (matchedIdx !== undefined && matchedIdx >= 0 && currentPanel?.options) {
            const matchedOpt = currentPanel.options[matchedIdx];
            if (matchedOpt) {
              choices = { ...choices, [currentPanel.id]: matchedIdx };
              selectedOption = { example: matchedOpt.examples?.[0] };
            }
          }
        }

        if (tier === 'perfect' || tier === 'good') {
          const quality = tier === 'perfect' ? 'Perfect!' : matchLevel >= 0.8 ? 'Great!' : 'Good!';
          const matchedIdx = result.matched_index;
          const matchedOpt = (matchedIdx >= 0 && currentPanel?.options) ? currentPanel.options[matchedIdx] : null;
          const category = matchedOpt ? getOptionCategory(matchedOpt) : null;
          speakResult = { success: true, message: quality, tier, heard: result.heard || '', heardTranslation: result.heard_translation || '', category };
          score += Math.round(matchLevel * 100);
          playBeep({ frequency: 880, duration: 200 });
          saveProgress();

        } else {
          const heard = result.heard || '';
          const heardTranslation = result.heard_translation || '';

          // Determine how the response landed using the category system
          const matchedIdx = result.matched_index;
          const matchedOpt = (matchedIdx >= 0 && currentPanel?.options) ? currentPanel.options[matchedIdx] : null;
          const category = matchedOpt ? getOptionCategory(matchedOpt) : null;

          speakResult = { success: false, tier, heard, heardTranslation, category, canSkip: true };
          requireRepeat = true;

          saveProgress();
          playBeep({ frequency: 420, duration: 160 });
        }
      },
      onPenalty: (data) => {
        console.log('[Speech] Penalty:', data);
        speakResult = { success: false, message: data.message || 'Try in Japanese' };
        isRecording = false;
        evaluating = false;
        cleanupRecording();
      },
      onError: (err) => {
        console.error('[Speech] Error:', err);
        speakResult = { success: false, message: 'Connection error - try again' };
        isRecording = false;
        evaluating = false;
        cleanupRecording();
      },
    });
  }

  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        if (streamingManager) {
          streamingManager.signalStop('stop');
        }
        mediaRecorder.stop();
      }
      isRecording = false;
      evaluating = true;
      audioAnalyser = null;
      disconnectAnalyser();
    } else {
      userHasInteracted = true;
      stopAudio();
      ensureAudioContext();
      // Re-create streaming manager each time so getScenario picks up current state
      if (streamingManager) {
        streamingManager.close();
        streamingManager = null;
      }
      initStreamingManager();

      try {
        liveTranscript = '';
        speakResult = null;

        const micId = getString(STORAGE_KEYS.MIC_DEVICE_ID, '');
        let stream;
        try {
          const audioConstraints = micId ? { deviceId: { exact: micId } } : true;
          stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
        } catch (_) {
          stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        }
        recordingStream = stream;
        mediaRecorder = new MediaRecorder(stream);
        audioAnalyser = setupAudioAnalyser(stream);

        mediaRecorder.ondataavailable = async (event) => {
          if (!event?.data) return;
          audioChunks.push(event.data);
          if (streamingManager) {
            await streamingManager.sendChunk(event.data);
          }
        };

        mediaRecorder.onstop = () => {
          try {
            recordingStream?.getTracks?.().forEach(t => t.stop());
          } catch (_) {}
          recordingStream = null;
          audioChunks = [];
        };

        audioChunks = [];
        streamingManager.setEnabled(true);
        streamingManager.connect();
        mediaRecorder.start(200);
        isRecording = true;

      } catch (err) {
        console.error('Error accessing microphone:', err);
        speakResult = { success: false, message: 'Microphone access denied' };
      }
    }
  }

  async function startDevClipRecording() {
    if (devIsRecordingClip || isRecording) return;
    try {
      const micId = getString(STORAGE_KEYS.MIC_DEVICE_ID, '');
      let stream;
      try {
        const audioConstraints = micId ? { deviceId: { exact: micId } } : true;
        stream = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
      } catch (_) {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      devClipStream = stream;
      devClipChunks = [];
      const recorder = new MediaRecorder(stream);
      devClipRecorder = recorder;
      recorder.ondataavailable = (e) => { if (e.data) devClipChunks = [...devClipChunks, e.data]; };
      recorder.onstop = () => {
        const blob = new Blob(devClipChunks, { type: 'audio/webm' });
        const optTarget = selectedOption?.example?.target || previewedOption?.example?.target || 'clip';
        const safePanelId = (currentPanel?.id || 'unknown').replace(/[^a-zA-Z0-9_-]/g, '_');
        const safeTarget = optTarget.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30);
        const ts = Date.now();
        const filename = `${safePanelId}_${safeTarget}_${ts}.webm`;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = filename; a.click();
        URL.revokeObjectURL(url);
        devClipStream?.getTracks().forEach(t => t.stop());
        devClipStream = null;
        devClipRecorder = null;
        devIsRecordingClip = false;
      };
      recorder.start(200);
      devIsRecordingClip = true;
      setTimeout(() => { if (devIsRecordingClip) stopDevClipRecording(); }, devClipDuration * 1000);
    } catch (err) {
      console.error('[DevClip] Mic error:', err);
    }
  }

  function stopDevClipRecording() {
    if (devClipRecorder && devClipRecorder.state !== 'inactive') {
      devClipRecorder.stop();
    }
  }

  function devJumpToPanel(entry) {
    stopAudio();
    cleanupRecording();
    isTimeFrozen = false;
    canAdvance = true;
    previewedOption = null;
    selectedOption = null;
    requireRepeat = false;
    speakResult = null;
    liveTranscript = '';
    currentChapterIndex = entry.chapterIdx;
    currentPanelIndex = entry.panelIdx;
    saveProgress();
  }

  function handleDevFileSelect(e) {
    devAudioFile = e.target.files?.[0] || null;
  }

  async function injectAudio() {
    if (!devAudioFile || devInjecting) return;
    devInjecting = true;

    stopAudio();
    if (streamingManager) {
      streamingManager.close();
      streamingManager = null;
    }
    initStreamingManager();

    liveTranscript = '';
    speakResult = null;
    evaluating = true;

    streamingManager.setEnabled(true);
    streamingManager.connect();

    // Wait for WebSocket to open
    await new Promise(resolve => {
      const unsub = streamingManager.status.subscribe(s => {
        if (s === 'open') { unsub(); resolve(); }
      });
    });

    // Send the file as a single chunk
    const blob = devAudioFile.slice();
    await streamingManager.sendChunk(blob);

    // Brief pause then signal stop to trigger finalization
    await new Promise(r => setTimeout(r, 200));
    streamingManager.signalStop('stop');

    devInjecting = false;
  }

  function cleanupRecording() {
    if (recordingStream) {
      try {
        recordingStream.getTracks().forEach(t => t.stop());
      } catch (_) {}
      recordingStream = null;
    }
    if (streamingManager) {
      streamingManager.setEnabled(false);
    }
    audioAnalyser = null;
    disconnectAnalyser();
    liveTranscript = '';
  }

  function stopAudio() {
    audioSessionId++;
    if (currentAudio) {
      currentAudio.pause();
      currentAudio.src = '';
      currentAudio = null;
    }
    activeSubscriptions.forEach(unsub => unsub());
    activeSubscriptions = [];
    audioQueue = [];
    isProcessingQueue = false;
    isPlaying = false;
  }

  function triggerTimeFreeze() {
    // Don't stop audio - let narration/dialogue play before showing options
    cleanupRecording();
    isTimeFrozen = true;
    canAdvance = false;
  }

  function resumeTime() {
    isTimeFrozen = false;
    canAdvance = true;
    previewedOption = null;
    selectedOption = null;
    requireRepeat = false;
  }

  const TTS_PROVIDER = 'elevenlabs';

  function getVoiceForSpeaker(speaker) {
    return {
      provider: TTS_PROVIDER,
      character: speaker,
      role: speaker === 'bimbo' ? 'bimbo' : 'npc',
    };
  }

  function getNarratorVoice() {
    return {
      provider: TTS_PROVIDER,
      character: 'narrator',
      role: 'narrator',
    };
  }

  async function playAudioWithSettings(url, sessionId) {
    if (sessionId !== audioSessionId) return;

    const audio = new Audio(url);
    audio.volume = $masterVolume;
    audio.playbackRate = $playbackSpeed;

    const unsubVol = masterVolume.subscribe(v => audio.volume = v);
    const unsubSpeed = playbackSpeed.subscribe(s => audio.playbackRate = s);
    activeSubscriptions.push(unsubVol, unsubSpeed);

    currentAudio = audio;

    return new Promise((resolve, reject) => {
      const cleanup = () => {
        activeSubscriptions = activeSubscriptions.filter(s => s !== unsubVol && s !== unsubSpeed);
        unsubVol();
        unsubSpeed();
        if (currentAudio === audio) currentAudio = null;
      };

      audio.onended = () => { cleanup(); resolve(undefined); };
      audio.onerror = (e) => { cleanup(); reject(e); };

      if (sessionId !== audioSessionId) {
        cleanup();
        resolve(undefined);
        return;
      }

      audio.play().catch(err => { cleanup(); reject(err); });
    });
  }

  async function processAudioQueue() {
    if (isProcessingQueue || audioQueue.length === 0) return;

    const sessionId = audioSessionId;
    isProcessingQueue = true;
    isPlaying = true;

    console.log('[Audio] Processing queue:', audioQueue.length, 'items');

    while (audioQueue.length > 0) {
      if (sessionId !== audioSessionId) break;

      const item = audioQueue.shift();
      console.log('[Audio] Playing item:', item);
      try {
        const response = await getTTS(item);
        console.log('[Audio] TTS response:', response);
        if (sessionId !== audioSessionId) break;
        if (response.skip) {
          console.log('[Audio] Skipped (no voice for character)');
          continue;
        }
        if (response.error) {
          console.error('[Audio] TTS error:', response.error);
          continue;
        }
        await playAudioWithSettings(response.url, sessionId);
      } catch (e) {
        console.error('[TTS] Error:', e);
      }
    }

    if (sessionId === audioSessionId) {
      isProcessingQueue = false;
      isPlaying = false;
    }
  }

  async function autoPlayPanel() {
    console.log('[Audio] autoPlayPanel called', { currentPanel: currentPanel?.id, userHasInteracted });
    if (!currentPanel || !userHasInteracted) {
      console.log('[Audio] Skipping - no panel or no interaction yet');
      return;
    }

    stopAudio();

    // Always play narration
    if (currentPanel.narration) {
      console.log('[Audio] Queuing narration');
      audioQueue.push({ text: currentPanel.narration, ...getNarratorVoice() });
    }

    // Play dialogue (skip player lines)
    if (currentPanel.dialogue && currentPanel.speaker && currentPanel.speaker !== 'player') {
      console.log('[Audio] Queuing dialogue for:', currentPanel.speaker);
      audioQueue.push({ text: currentPanel.dialogue, ...getVoiceForSpeaker(currentPanel.speaker) });
    }

    if (audioQueue.length > 0) {
      console.log('[Audio] Starting queue processing');
      processAudioQueue();
    } else {
      console.log('[Audio] Nothing to play');
    }
  }

  async function playNarration() {
    if (!currentPanel?.narration || isPlaying) return;
    userHasInteracted = true;

    stopAudio();
    const sessionId = audioSessionId;
    isPlaying = true;

    try {
      const response = await getTTS({
        text: currentPanel.narration,
        ...getNarratorVoice(),
      });

      if (sessionId !== audioSessionId) return;
      if (response.error) throw new Error(response.error);

      await playAudioWithSettings(response.url, sessionId);
    } catch (e) {
      console.error('[TTS] Error:', e);
    } finally {
      if (sessionId === audioSessionId) isPlaying = false;
    }
  }

  async function playDialogue() {
    if (!currentPanel?.dialogue || !currentPanel?.speaker || isPlaying) return;
    userHasInteracted = true;

    stopAudio();
    const sessionId = audioSessionId;
    isPlaying = true;

    try {
      const response = await getTTS({
        text: currentPanel.dialogue,
        ...getVoiceForSpeaker(currentPanel.speaker),
      });

      if (sessionId !== audioSessionId) return;
      if (response.skip) return;
      if (response.error) throw new Error(response.error);

      await playAudioWithSettings(response.url, sessionId);
    } catch (e) {
      console.error('[TTS] Error:', e);
    } finally {
      if (sessionId === audioSessionId) isPlaying = false;
    }
  }

  async function playExample(example) {
    if (!example?.target || isPlaying) return;

    stopAudio();
    const sessionId = audioSessionId;
    isPlaying = true;

    try {
      // Use Bimbo's voice for teaching examples
      const response = await getTTS({
        text: example.target,
        ...getVoiceForSpeaker('bimbo'),
        language: 'ja',
        sentiment: 'encouraging'
      });

      if (sessionId !== audioSessionId) return;
      if (response.error) throw new Error(response.error);

      await playAudioWithSettings(response.url, sessionId);
    } catch (e) {
      console.error('[TTS] Error:', e);
    } finally {
      if (sessionId === audioSessionId) isPlaying = false;
    }
  }

  function handleOptionPreview(event) {
    const detail = event?.detail || {};
    previewedOption = detail;
    speakResult = null;
    playExample(detail.example);
  }

  async function handleAskBimbo(event) {
    const text = event?.detail;
    console.log('[AskBimbo] Triggered, text:', text);
    if (!text || askingBimbo) {
      console.log('[AskBimbo] Skipped — empty text or already asking');
      return;
    }

    askingBimbo = true;
    bimboHint = null;

    try {
      const optionsPayload = formattedOptions.map(o => ({
        text: o.option_text,
        style: o.style || '',
      }));
      console.log('[AskBimbo] Sending request:', { player_text: text, options: optionsPayload });

      const res = await fetch(`${API_BASE}/narrative/ask-bimbo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_text: text, options: optionsPayload }),
      });

      console.log('[AskBimbo] HTTP status:', res.status);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      console.log('[AskBimbo] Response data:', data);

      bimboHint = {
        matchedIndex: data.matched_index,
        confidence: data.confidence,
        bimboSays: data.bimbo_says,
        translation: data.translation || '',
        pronunciation: data.pronunciation || '',
        playerText: text,
      };
      console.log('[AskBimbo] bimboHint set:', bimboHint);

      // Auto-play translation audio if available
      if (data.translation) {
        console.log('[AskBimbo] Auto-playing translation:', data.translation);
        playExample({ target: data.translation });
      }
      // Also highlight matched option if one fits
      else if (data.matched_index >= 0 && formattedOptions[data.matched_index]) {
        const matchedOpt = formattedOptions[data.matched_index];
        console.log('[AskBimbo] Auto-previewing matched option:', data.matched_index, matchedOpt.option_text);
        if (matchedOpt.examples?.[0]) {
          playExample(matchedOpt.examples[0]);
        }
      } else {
        console.log('[AskBimbo] No option to auto-preview (index:', data.matched_index, ')');
      }
    } catch (err) {
      console.error('[AskBimbo] Error:', err);
      bimboHint = {
        matchedIndex: -1,
        confidence: 'none',
        bimboSays: "Hmm, I'm having trouble thinking right now. Try tapping an option to hear it!",
        translation: '',
        pronunciation: '',
        playerText: text,
      };
    } finally {
      askingBimbo = false;
      console.log('[AskBimbo] Done. askingBimbo=false, bimboHint:', bimboHint);
    }
  }

  function handlePlayBimboTranslation(event) {
    const detail = event?.detail;
    if (detail?.target) {
      playExample({ target: detail.target });
    }
  }

  function handlePlayAudio() {
    if (selectedOption?.example) {
      playExample(selectedOption.example);
    }
  }

  function nextPanel() {
    if (!canAdvance || isTimeFrozen) return;

    stopAudio();

    if (currentPanelIndex < currentChapter.panels.length - 1) {
      currentPanelIndex++;
    } else if (currentChapterIndex < story.chapters.length - 1) {
      currentChapterIndex++;
      currentPanelIndex = 0;
    }
    saveProgress();
  }

  function prevPanel() {
    stopAudio();
    isTimeFrozen = false;
    canAdvance = true;
    selectedOption = null;
    requireRepeat = false;

    if (currentPanelIndex > 0) {
      currentPanelIndex--;
    } else if (currentChapterIndex > 0) {
      currentChapterIndex--;
      currentPanelIndex = story.chapters[currentChapterIndex].panels.length - 1;
    }
  }

  function toggleAutoNarrate() {
    autoNarrate = !autoNarrate;
    if (browser) {
      try { localStorage.setItem(AUTO_NARRATE_KEY, String(autoNarrate)); } catch (_) {}
    }
    if (autoNarrate && !isPlaying && !isTimeFrozen) {
      autoPlayPanel();
    } else if (!autoNarrate) {
      stopAudio();
    }
  }

  function openMenu() { menuVisible = true; }
  function closeMenu() { menuVisible = false; }
  function handleMenuExit() { menuVisible = false; window.location.href = '/'; }

  function handleKeydown(e) {
    // Don't capture keys when typing in an input field
    const tag = document.activeElement?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA') return;

    const wasInteracted = userHasInteracted;
    userHasInteracted = true;

    // If this is first interaction, play the current panel's audio
    if (!wasInteracted && autoNarrate) {
      autoPlayPanel();
    }

    if (e.key === 'Escape') {
      if (menuVisible) closeMenu();
      else openMenu();
      return;
    }

    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      if (isTimeFrozen && hasOptions) {
        toggleRecording();
      } else if (!isTimeFrozen) {
        nextPanel();
      }
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      prevPanel();
    }
  }

  function handlePanelClick(e) {
    const wasInteracted = userHasInteracted;
    userHasInteracted = true;

    // If this is first interaction, play the current panel's audio
    if (!wasInteracted && autoNarrate) {
      autoPlayPanel();
    }

    if (isTimeFrozen) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    if (x > rect.width / 2) {
      nextPanel();
    } else {
      prevPanel();
    }
  }

  function getSpeakerName(speaker) {
    const names = { bimbo: 'Bimbo', hana: 'Hana', samurai: 'Samurai', player: 'You' };
    return names[speaker] || speaker;
  }

  function getSpeakerColor(speaker) {
    const colors = { bimbo: '#a855f7', hana: '#78716c', samurai: '#dc2626', player: '#10b981' };
    return colors[speaker] || '#fff';
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<audio bind:this={audioPlayer}></audio>

<GameMenu
  visible={menuVisible}
  judgeFocus={0}
  languageOverride=""
  micDevices={[]}
  micDeviceId=""
  scenariosCompleted={0}
  on:close={closeMenu}
  on:exit={handleMenuExit}
/>

<div class="player" class:time-frozen={isTimeFrozen}>
  {#if loading}
    <div class="loading">
      <div class="loading-spinner"></div>
      <p>Loading story...</p>
    </div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if story}
    <!-- HUD -->
    <GameHUD {lives} {livesTotal} {score} on:openMenu={openMenu} />

    <!-- Game Over Overlay -->
    {#if gameOver}
      <div class="game-over-overlay" transition:fade={{ duration: 500 }}>
        <div class="game-over-content" in:scale={{ duration: 400, delay: 200 }}>
          <h1 class="game-over-title">Time Anchor Destabilized</h1>
          <p class="game-over-subtitle">The simulation has collapsed. Your words weren't enough to hold reality together.</p>
          <div class="game-over-score">Final Score: {score}</div>
          <button class="game-over-btn" on:click={resetGame}>
            Rewind to Beginning
          </button>
        </div>
      </div>
    {/if}

    <!-- Audio Controls -->
    <div class="audio-controls">
      <button
        class="control-btn"
        class:active={autoNarrate}
        class:muted={!autoNarrate}
        on:click={toggleAutoNarrate}
        title={autoNarrate ? 'Auto-narrate ON' : 'Auto-narrate OFF'}
      >
        {#if autoNarrate}
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>
        {:else}
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z"/></svg>
        {/if}
      </button>
      <VolumeControl />
    </div>

    <!-- Dev Tools -->
    <div class="dev-tools">
      <button class="dev-btn" on:click={() => devMenuOpen = !devMenuOpen} title="Dev tools">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
        </svg>
      </button>
      {#if devMenuOpen}
        <div class="dev-panel" transition:fade={{ duration: 100 }}>
          <div class="dev-title">Dev Tools</div>
          <label class="dev-option">
            <input type="checkbox" bind:checked={infiniteLives} />
            <span>Infinite lives</span>
          </label>

          <!-- Record Clip -->
          <div class="dev-separator"></div>
          <div class="dev-title">Record Clip</div>
          <div class="dev-row">
            <label class="dev-label">Duration (s)</label>
            <input type="number" class="dev-input-sm" min="1" max="30" bind:value={devClipDuration} />
          </div>
          <button
            class="dev-inject-btn"
            class:dev-recording={devIsRecordingClip}
            on:click={() => devIsRecordingClip ? stopDevClipRecording() : startDevClipRecording()}
            disabled={isRecording}
          >
            {devIsRecordingClip ? 'Stop Recording' : 'Record'}
          </button>

          <!-- Inject Audio -->
          <div class="dev-separator"></div>
          <div class="dev-title">Inject Audio</div>
          <input type="file" accept="audio/*" class="dev-file" on:change={handleDevFileSelect} />
          {#if devAudioFile}
            <div class="dev-file-name">{devAudioFile.name}</div>
            <button class="dev-inject-btn" on:click={injectAudio} disabled={devInjecting || !isTimeFrozen}>
              {devInjecting ? 'Injecting...' : 'Inject'}
            </button>
            <label class="dev-option" style="margin-top:4px">
              <input type="checkbox" bind:checked={devAutoInject} />
              <span>Auto-inject on freeze</span>
            </label>
            {#if devAutoInject}
              <div class="dev-row">
                <label class="dev-label">Delay (ms)</label>
                <input type="number" class="dev-input-sm" min="0" max="5000" step="100" bind:value={devAutoInjectDelay} />
              </div>
            {/if}
          {/if}

          <!-- Match Threshold -->
          <div class="dev-separator"></div>
          <div class="dev-title">Match Threshold</div>
          <div class="dev-row">
            <input type="range" class="dev-slider" min="0" max="1" step="0.05" bind:value={devMatchThreshold} />
            <span class="dev-value">{Math.round(devMatchThreshold * 100)}%</span>
          </div>
          <div class="dev-note">Frontend only. Backend uses 0.70.</div>

          <!-- Last Result -->
          <div class="dev-separator"></div>
          <div class="dev-title">Last Result</div>
          {#if devLastResult}
            {@const matchedIdx = devLastResult.matched_index}
            {@const matchedOpt = (matchedIdx !== undefined && matchedIdx >= 0 && currentPanel?.options) ? currentPanel.options[matchedIdx] : null}
            {@const cat = getOptionCategory(matchedOpt)}
            <div class="dev-category-badge" style="background: {cat.color}20; border-color: {cat.color}40; color: {cat.color}">
              {cat.icon} {cat.label}
            </div>
            <div class="dev-result-grid">
              <span class="dev-result-key">tier</span>
              <span class="dev-result-val" style="color: {devLastResult.tier === 'perfect' ? '#86efac' : devLastResult.tier === 'good' ? '#86efac' : devLastResult.tier === 'passable' ? '#fbbf24' : devLastResult.tier === 'fumble' ? '#fdba74' : '#fca5a5'}">
                {devLastResult.tier || '—'}
              </span>
              <span class="dev-result-key">style</span>
              <span class="dev-result-val">{matchedOpt?.style || '—'}</span>
              <span class="dev-result-key">match</span>
              <span class="dev-result-val" style="color: {(devLastResult.match_level ?? 0) >= 0.9 ? '#86efac' : (devLastResult.match_level ?? 0) >= 0.7 ? '#fde047' : '#fca5a5'}">
                {Math.round((devLastResult.match_level ?? 0) * 100)}%
              </span>
              <span class="dev-result-key">heard</span>
              <span class="dev-result-val">{devLastResult.heard || '—'}</span>
              <span class="dev-result-key">expected</span>
              <span class="dev-result-val">{devLastResult.expected || devLastResult.expected_response || '—'}</span>
              <span class="dev-result-key">lang</span>
              <span class="dev-result-val">{devLastResult.detected_language || '—'}</span>
            </div>
          {:else}
            <div class="dev-note">No result yet</div>
          {/if}

          <!-- Panel Jump -->
          <div class="dev-separator"></div>
          <div class="dev-title">Panel Jump</div>
          <div class="dev-panel-list">
            {#each devPanelList as entry, i}
              <button
                class="dev-panel-row"
                class:dev-panel-active={entry.chapterIdx === currentChapterIndex && entry.panelIdx === currentPanelIndex}
                on:click={() => devJumpToPanel(entry)}
              >
                <span class="dev-panel-idx">{i + 1}</span>
                {#if entry.hasOptions}<span class="dev-panel-dot" style="background: {entry.catColor || '#6366f1'}"></span>{/if}
                <span class="dev-panel-id">{entry.id}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>

    <!-- Progress bar -->
    <div class="progress-bar">
      <div class="progress-fill" style="width: {progress}%"></div>
    </div>

    <!-- Chapter title -->
    {#key currentChapter?.id}
      <div class="chapter-title" in:fade={{ duration: 300 }}>
        {currentChapter?.title}
      </div>
    {/key}

    <!-- Panel display -->
    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
    <div class="panel-container" on:click={handlePanelClick}>
      {#key currentPanel?.id}
        <div
          class="panel panel--{currentPanel?.aspect || 'square'}"
          class:panel--time-freeze={isTimeFrozen}
          in:fade={{ duration: 400 }}
        >
          <img
            src="{API_BASE}{currentPanel?.image}"
            alt={currentPanel?.id}
            class="panel-image"
          />

          {#if isTimeFrozen}
            <div class="freeze-overlay" transition:fade={{ duration: 300 }}>
              <div class="freeze-vignette"></div>
              <div class="freeze-particles">
                {#each Array(20) as _, i}
                  <div class="particle" style="--delay: {i * 0.1}s; --x: {Math.random() * 100}%; --y: {Math.random() * 100}%"></div>
                {/each}
              </div>
            </div>
          {/if}

          {#if isTimeFrozen}
            <div class="effect-badge freeze" transition:scale={{ duration: 300 }}>
              ⏸ TIME FROZEN
            </div>
          {/if}
        </div>
      {/key}
    </div>

    <!-- Time Stop Panel with options -->
    {#if isTimeFrozen && hasOptions}
      <div class="choices-section" transition:fly={{ y: 50, duration: 400 }}>
        <TimeStopPanel
          options={formattedOptions}
          {selectedOption}
          {previewedOption}
          {draftText}
          {bimboHint}
          {askingBimbo}
          isPreviewPlaying={isPlaying && !!previewedOption}
          on:previewOption={handleOptionPreview}
          on:playAudio={handlePlayAudio}
          on:draftChange={(e) => draftText = e.detail}
          on:askBimbo={handleAskBimbo}
          on:playBimboTranslation={handlePlayBimboTranslation}
        />

        {#if hasOptions}
          <!-- Live transcript -->
          {#if isRecording && liveTranscript}
            <div class="live-transcript" transition:fade={{ duration: 150 }}>
              "{liveTranscript}"
            </div>
          {/if}

          <!-- Result feedback -->
          {#if speakResult}
            <div
              class="speak-result"
              class:success={speakResult.success}
              class:tier-passable={speakResult.tier === 'passable'}
              class:tier-fumble={speakResult.tier === 'fumble'}
              class:tier-fail={speakResult.tier === 'fail'}
              transition:fade={{ duration: 150 }}
            >
              {#if speakResult.success}
                <div class="result-success-msg">{speakResult.message}</div>
                {#if speakResult.heard}<div class="result-heard"><span class="result-label">You said:</span> "{speakResult.heard}"{#if speakResult.heardTranslation} <span class="result-dim">— {speakResult.heardTranslation}</span>{/if}</div>{/if}
                {#if speakResult.category}
                  <div class="result-category" style="color: {speakResult.category.color}; border-color: {speakResult.category.color}40; background: {speakResult.category.color}15">
                    {speakResult.category.icon} {speakResult.category.label}
                  </div>
                {/if}
                <button class="continue-btn" on:click|stopPropagation={() => { speakResult = null; requireRepeat = false; resumeTime(); nextPanel(); }}>
                  Continue →
                </button>
              {:else}
                {#if speakResult.heard}<div class="result-heard"><span class="result-label">You said:</span> "{speakResult.heard}"{#if speakResult.heardTranslation} <span class="result-dim">— {speakResult.heardTranslation}</span>{/if}</div>{/if}
                {#if speakResult.category}
                  <div class="result-category" style="color: {speakResult.category.color}; border-color: {speakResult.category.color}40; background: {speakResult.category.color}15">
                    {speakResult.category.icon} {speakResult.category.label}
                  </div>
                {/if}
                {#if speakResult.canSkip}
                  <button class="skip-btn" on:click|stopPropagation={() => { speakResult = null; requireRepeat = false; resumeTime(); nextPanel(); }}>
                    Skip →
                  </button>
                {/if}
              {/if}
            </div>
          {/if}

          <!-- Speak button -->
          <div class="speak-section">
            <SpeakButton
              {isRecording}
              isEvaluating={evaluating}
              isTimeStopped={true}
              analyser={audioAnalyser}
              on:toggle={toggleRecording}
            />
          </div>
        {/if}
      </div>
    {/if}

    <!-- Text box -->
    <div class="text-box" class:minimized={isTimeFrozen && hasOptions}>
      {#key currentPanel?.id}
        <div class="text-content" in:fly={{ y: 20, duration: 300 }}>
          {#if currentPanel?.narration}
            <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
            <p class="narration clickable" on:click|stopPropagation={playNarration}>
              {currentPanel.narration}
              <span class="audio-hint">🔊</span>
            </p>
          {/if}
          {#if currentPanel?.dialogue}
            <p class="dialogue">
              {#if currentPanel?.speaker}
                {#if currentPanel.speaker === 'player'}
                  <span class="speaker" style="color: {getSpeakerColor(currentPanel.speaker)}">
                    {getSpeakerName(currentPanel.speaker)}:
                  </span>
                {:else}
                  <button
                    class="speaker-btn"
                    style="color: {getSpeakerColor(currentPanel.speaker)}"
                    on:click|stopPropagation={playDialogue}
                  >
                    {getSpeakerName(currentPanel.speaker)}:
                    <span class="audio-hint">🔊</span>
                  </button>
                {/if}
              {/if}
              "{currentPanel.dialogue}"
            </p>
          {/if}
        </div>
      {/key}

      {#if isPlaying}
        <div class="playing-bar" transition:fade={{ duration: 200 }}>
          <span class="playing-dot"></span>
          <span>Playing...</span>
          <button class="stop-btn" on:click|stopPropagation={stopAudio}>Stop</button>
        </div>
      {/if}
    </div>

    <!-- Navigation -->
    <div class="nav-bar">
      <button class="nav-btn" on:click={prevPanel} disabled={currentPanelNumber <= 1}>
        ← Back
      </button>
      <span class="panel-counter">
        {currentPanelNumber} / {totalPanels}
      </span>
      <button
        class="nav-btn nav-btn--primary"
        on:click={() => {
          if (isTimeFrozen && hasOptions) {
            toggleRecording();
          } else if (!isTimeFrozen) {
            nextPanel();
          }
        }}
        disabled={isLastPanel || isPlaying}
      >
        {#if isTimeFrozen}
          {isRecording ? 'Stop' : 'Speak'}
        {:else}
          Next →
        {/if}
      </button>
    </div>
  {/if}
</div>

<style>
  .player {
    min-height: 100vh;
    min-height: 100dvh;
    background: #0a0a0a;
    color: #fff;
    display: flex;
    flex-direction: column;
    font-family: 'Segoe UI', system-ui, sans-serif;
    transition: background 0.5s ease;
  }

  .player.time-frozen {
    background: #0a0a1a;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    gap: 1rem;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #333;
    border-top-color: #a855f7;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
    color: #ef4444;
    font-size: 1.2rem;
  }

  .dev-tools {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 100;
  }

  .dev-btn {
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    cursor: pointer;
    padding: 0;
    transition: background 0.15s;
  }

  .dev-btn:hover {
    background: rgba(255, 255, 255, 0.12);
  }

  .dev-btn svg {
    width: 16px;
    height: 16px;
    color: rgba(255, 255, 255, 0.35);
  }

  .dev-panel {
    position: absolute;
    top: 100%;
    right: 0;
    margin-top: 6px;
    background: rgba(15, 15, 25, 0.95);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    min-width: 280px;
    max-height: min(70vh, 600px);
    overflow-y: auto;
  }

  .dev-title {
    font-size: 0.6rem;
    color: #52525b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 6px;
  }

  .dev-option {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: #a1a1aa;
    cursor: pointer;
    padding: 3px 0;
  }

  .dev-option input[type="checkbox"] {
    width: 14px;
    height: 14px;
    accent-color: #6366f1;
    cursor: pointer;
  }

  .dev-separator {
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
    margin: 6px 0;
  }

  .dev-file {
    font-size: 0.65rem;
    color: #71717a;
    width: 100%;
    margin-top: 2px;
  }

  .dev-file::file-selector-button {
    font-size: 0.65rem;
    padding: 2px 6px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 4px;
    color: #a1a1aa;
    cursor: pointer;
    margin-right: 4px;
  }

  .dev-file-name {
    font-size: 0.6rem;
    color: #52525b;
    margin-top: 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dev-inject-btn {
    margin-top: 4px;
    width: 100%;
    padding: 4px 8px;
    font-size: 0.7rem;
    font-weight: 600;
    background: rgba(99, 102, 241, 0.25);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 5px;
    color: #a5b4fc;
    cursor: pointer;
    transition: background 0.15s;
  }

  .dev-inject-btn:hover:not(:disabled) {
    background: rgba(99, 102, 241, 0.4);
  }

  .dev-inject-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .dev-inject-btn.dev-recording {
    background: rgba(239, 68, 68, 0.35);
    border-color: rgba(239, 68, 68, 0.6);
    color: #fca5a5;
    animation: pulse-recording 1s ease-in-out infinite;
  }

  @keyframes pulse-recording {
    0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    50% { box-shadow: 0 0 8px 2px rgba(239, 68, 68, 0.3); }
  }

  .dev-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 3px 0;
  }

  .dev-label {
    font-size: 0.65rem;
    color: #71717a;
    white-space: nowrap;
  }

  .dev-input-sm {
    width: 60px;
    padding: 2px 4px;
    font-size: 0.65rem;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    color: #d4d4d8;
    text-align: center;
  }

  .dev-slider {
    flex: 1;
    height: 4px;
    accent-color: #6366f1;
    cursor: pointer;
  }

  .dev-value {
    font-size: 0.7rem;
    color: #a5b4fc;
    font-weight: 600;
    min-width: 32px;
    text-align: right;
  }

  .dev-note {
    font-size: 0.55rem;
    color: #52525b;
    font-style: italic;
    margin-top: 2px;
  }

  .dev-category-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border: 1px solid;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .dev-result-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 2px 8px;
    font-size: 0.65rem;
  }

  .dev-result-key {
    color: #52525b;
    text-align: right;
  }

  .dev-result-val {
    color: #a1a1aa;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .dev-panel-list {
    max-height: 160px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .dev-panel-row {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 3px 6px;
    background: none;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    text-align: left;
    color: #71717a;
    font-size: 0.6rem;
    transition: background 0.1s;
  }

  .dev-panel-row:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #a1a1aa;
  }

  .dev-panel-row.dev-panel-active {
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
  }

  .dev-panel-idx {
    min-width: 18px;
    text-align: right;
    color: #3f3f46;
  }

  .dev-panel-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .dev-panel-id {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .progress-bar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: #1f1f1f;
    z-index: 100;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #a855f7, #06b6d4);
    transition: width 0.3s ease;
  }

  .chapter-title {
    position: fixed;
    top: 12px;
    left: 50%;
    transform: translateX(-50%);
    font-size: 0.875rem;
    color: #a1a1aa;
    z-index: 50;
    text-align: center;
  }

  .audio-controls {
    position: fixed;
    top: 16px;
    left: 70px;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .control-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 50%;
    cursor: pointer;
    transition: all 0.2s ease;
    padding: 0;
    color: rgba(255, 255, 255, 0.7);
  }

  .control-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    color: white;
  }

  .control-btn.active {
    background: rgba(139, 92, 246, 0.3);
    border-color: rgba(139, 92, 246, 0.5);
    color: #c4b5fd;
  }

  .control-btn.muted {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
    color: #fca5a5;
  }

  .control-btn svg {
    width: 18px;
    height: 18px;
  }

  .panel-container {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 3rem 1rem 1rem;
    cursor: pointer;
    min-height: 0;
    overflow: hidden;
  }

  .panel {
    position: relative;
    max-width: 100%;
    max-height: 100%;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    transition: box-shadow 0.5s ease;
  }

  .panel--wide { max-width: min(900px, 95vw); }
  .panel--square { max-width: min(500px, 90vw); }
  .panel--tall { max-width: min(400px, 80vw); }

  .panel--time-freeze {
    box-shadow: 0 0 60px rgba(99, 102, 241, 0.4);
  }

  .panel-image {
    display: block;
    width: 100%;
    height: auto;
    max-height: 800px;
  }

  .freeze-overlay {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .freeze-vignette {
    position: absolute;
    inset: 0;
    box-shadow: inset 0 0 100px rgba(99, 102, 241, 0.3);
  }

  .freeze-particles {
    position: absolute;
    inset: 0;
    overflow: hidden;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(167, 139, 250, 0.6);
    border-radius: 50%;
    left: var(--x);
    top: var(--y);
    animation: float 3s ease-in-out infinite;
    animation-delay: var(--delay);
  }

  @keyframes float {
    0%, 100% { transform: translateY(0) scale(1); opacity: 0.6; }
    50% { transform: translateY(-20px) scale(1.2); opacity: 1; }
  }

  .effect-badge {
    position: absolute;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.1em;
  }

  .effect-badge.freeze {
    background: rgba(99, 102, 241, 0.9);
    color: white;
    animation: pulse-badge 2s ease-in-out infinite;
  }

  @keyframes pulse-badge {
    0%, 100% { box-shadow: 0 0 20px rgba(99, 102, 241, 0.5); }
    50% { box-shadow: 0 0 40px rgba(99, 102, 241, 0.8); }
  }

  .choices-section {
    padding: 0 1rem;
    margin-bottom: 0.5rem;
    flex-shrink: 0;
  }

  .live-transcript {
    margin-top: 0.75rem;
    padding: 0.5rem 1rem;
    background: rgba(99, 102, 241, 0.2);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 8px;
    color: #c4b5fd;
    font-size: 1.1rem;
    text-align: center;
    font-style: italic;
    max-width: 520px;
    margin-left: auto;
    margin-right: auto;
  }

  .speak-result {
    margin: 0.5rem auto 0;
    text-align: center;
    max-width: 340px;
  }

  .speak-result.success {
    color: #86efac;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .result-heard {
    font-size: 0.7rem;
    color: #71717a;
    margin-bottom: 0.4rem;
  }

  .result-label {
    color: #52525b;
  }

  .result-dim {
    color: #52525b;
    font-style: italic;
  }

  .result-answer {
    margin-bottom: 0.3rem;
  }

  .result-symbols {
    font-size: 1.3rem;
    font-weight: 600;
    color: #f1f5f9;
    letter-spacing: 0.05em;
    line-height: 1.3;
  }

  .result-pron {
    font-size: 0.75rem;
    color: #a5b4fc;
    margin-top: 0.15rem;
  }

  .result-meaning {
    font-size: 0.7rem;
    color: #94a3b8;
    font-style: italic;
    margin-top: 0.1rem;
  }

  .result-lives {
    font-size: 0.65rem;
    color: #fdba74;
    opacity: 0.7;
  }

  .speak-section {
    margin-top: 1rem;
    display: flex;
    justify-content: center;
  }

  .text-box {
    background: linear-gradient(to top, rgba(0,0,0,0.95), rgba(0,0,0,0.8));
    padding: 1rem;
    min-height: 80px;
    transition: min-height 0.3s ease, opacity 0.3s ease;
  }

  .text-box.minimized {
    min-height: 60px;
    opacity: 0.7;
  }

  .text-content {
    max-width: 700px;
    margin: 0 auto;
  }

  .narration {
    font-size: 0.95rem;
    line-height: 1.6;
    color: #d4d4d8;
    margin: 0 0 0.5rem 0;
    font-style: italic;
    position: relative;
  }

  .narration.clickable {
    cursor: pointer;
    transition: color 0.2s;
  }

  .narration.clickable:hover {
    color: #fff;
  }

  .audio-hint {
    font-size: 0.75em;
    opacity: 0.4;
    margin-left: 0.5rem;
    font-style: normal;
    transition: opacity 0.2s;
  }

  .narration.clickable:hover .audio-hint,
  .speaker-btn:hover .audio-hint {
    opacity: 0.8;
  }

  .dialogue {
    font-size: 1rem;
    line-height: 1.6;
    color: #fff;
    margin: 0;
  }

  .speaker {
    font-weight: 600;
    margin-right: 0.5rem;
  }

  .speaker-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    font-weight: 600;
    margin-right: 0.5rem;
    background: none;
    border: none;
    padding: 0;
    font-size: inherit;
    font-family: inherit;
    cursor: pointer;
    transition: opacity 0.2s;
  }

  .speaker-btn:hover {
    opacity: 0.8;
  }

  .playing-bar {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    font-size: 0.85rem;
    color: #a78bfa;
  }

  .playing-dot {
    width: 8px;
    height: 8px;
    background: #a78bfa;
    border-radius: 50%;
    animation: pulse-dot 1s ease-in-out infinite;
  }

  @keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.8); }
  }

  .stop-btn {
    margin-left: auto;
    padding: 0.25rem 0.75rem;
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    border-radius: 4px;
    color: #fca5a5;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .nav-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    padding-bottom: max(0.75rem, env(safe-area-inset-bottom, 0.75rem));
    background: #0a0a0a;
    border-top: 1px solid #1f1f1f;
  }

  .nav-btn {
    padding: 0.5rem 1rem;
    background: #27272a;
    border: 1px solid #3f3f46;
    border-radius: 8px;
    color: #a1a1aa;
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .nav-btn:hover:not(:disabled) {
    background: #3f3f46;
    color: #fff;
  }

  .nav-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .nav-btn--primary {
    background: #6366f1;
    border-color: #6366f1;
    color: white;
  }

  .nav-btn--primary:hover:not(:disabled) {
    background: #4f46e5;
  }

  .panel-counter {
    font-size: 0.85rem;
    color: #71717a;
    font-weight: 600;
  }

  .game-over-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    background: rgba(0, 0, 0, 0.92);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .game-over-content {
    text-align: center;
    padding: 2rem;
    max-width: 480px;
  }

  .game-over-title {
    font-size: 2rem;
    font-weight: 800;
    color: #ef4444;
    margin: 0 0 1rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    text-shadow: 0 0 40px rgba(239, 68, 68, 0.5);
  }

  .game-over-subtitle {
    font-size: 1rem;
    color: #a1a1aa;
    line-height: 1.6;
    margin: 0 0 2rem;
  }

  .game-over-score {
    font-size: 1.25rem;
    font-weight: 600;
    color: #c4b5fd;
    margin-bottom: 2rem;
  }

  .game-over-btn {
    padding: 0.75rem 2rem;
    background: #6366f1;
    border: none;
    border-radius: 8px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.2s;
  }

  .game-over-btn:hover {
    background: #4f46e5;
  }

  .result-success-msg {
    font-size: 1.1rem;
    font-weight: 700;
    color: #86efac;
    margin-bottom: 0.3rem;
  }

  .continue-btn {
    margin-top: 0.5rem;
    padding: 0.4rem 1.5rem;
    background: rgba(99, 102, 241, 0.3);
    border: 1px solid rgba(99, 102, 241, 0.5);
    border-radius: 8px;
    color: #c4b5fd;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
  }

  .continue-btn:hover {
    background: rgba(99, 102, 241, 0.5);
    border-color: rgba(99, 102, 241, 0.7);
    color: #fff;
  }

  .result-category {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px 10px;
    border: 1px solid;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    margin: 0.3rem 0;
  }

  /* Bimbo attempt result */
  .result-bimbo-heard {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 0.2rem;
  }

  .result-bimbo-translation {
    font-size: 0.85rem;
    color: #c4b5fd;
    margin-bottom: 0.5rem;
  }

  .result-bimbo-note {
    font-size: 0.75rem;
    color: #a78bfa;
    margin-bottom: 0.4rem;
  }

  /* Tier-specific result styles */
  .speak-result.tier-passable {
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.25);
    background: rgba(251, 191, 36, 0.08);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
  }

  .result-passable-msg {
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.3rem;
  }

  .result-hint {
    opacity: 0.85;
  }

  .speak-result.tier-fumble {
    border: 1px solid rgba(251, 146, 60, 0.25);
    background: rgba(251, 146, 60, 0.08);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
  }

  .result-fumble-note {
    font-size: 0.65rem;
    color: #fdba74;
    opacity: 0.7;
    margin-top: 0.2rem;
  }

  .speak-result.tier-fail {
    border: 1px solid rgba(239, 68, 68, 0.2);
    background: rgba(239, 68, 68, 0.06);
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
  }

  .skip-btn {
    margin-top: 0.5rem;
    padding: 0.3rem 1rem;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: #a1a1aa;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }

  .skip-btn:hover {
    background: rgba(255, 255, 255, 0.15);
    color: #fff;
  }

  @media (max-width: 640px) {
    .audio-controls {
      left: 56px;
      gap: 6px;
    }

    .panel-container {
      padding: 2.5rem 0.5rem 0.5rem;
      max-height: 40vh;
    }

    .text-box {
      padding: 0.75rem;
      min-height: 70px;
    }

    .narration { font-size: 0.85rem; }
    .dialogue { font-size: 0.9rem; }

    .game-over-title { font-size: 1.5rem; }
  }
</style>
