<script>
  import { storyStore } from '$lib/storyStore.js';
  import { getBackendUrl, discoverBackend, getStreamMode } from '$lib/config';
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
  const nativeLang = 'English'; // TODO: make user-configurable
  let audioCtx = null;
  let requireRepeat = false;
  let selectedOption = null; // { next_scenario, example: { native, target, audio } }
  let lives = 3;
  let livesTotal = 3;
  let score = 0;
  let penaltyMessage = '';
  let devMode = false;
  let lastHeard = '';
  let evaluating = false;
  // Make-your-own line (native -> translate -> try)
  let myNativeText = '';
  let translating = false;
  let isNativeRecording = false;
  let nativeRecorder;
  let nativeChunks = [];
  let streamMode = 'real';
  let streamingEnabled = false;
  let streamStatus = 'disabled';
  let streamEvents = [];
  let streamSocket = null;
  let liveTranscript = '';
  let waveCanvas;

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

  function resetStreamState() {
    streamEvents = [];
    liveTranscript = '';
    streamStatus = streamingEnabled ? 'idle' : 'disabled';
    penaltyMessage = '';
    if (!streamingEnabled) {
      score = 0;
    }
  }

  function handleOptionSelection(event) {
    const detail = event?.detail || {};
    const nextScenario = detail.next_scenario ?? detail.nextScenario ?? null;
    const example = detail.example || null;
    selectedOption = { next_scenario: nextScenario, example };
    requireRepeat = true;
    lastHeard = '';
    playBeep();
  }

  const handlePlayPrompt = () => {
    playBeep();
  };

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
          language: targetLang,
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
        resetLives(Math.max(1, data.lives_total));
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, data.lives_remaining);
      }
      score = typeof data.score === 'number' ? data.score : 0;
      penaltyMessage = '';
      return;
    }
    if (evt === 'reset') {
      streamStatus = 'open';
      if (typeof data.lives_total === 'number') {
        resetLives(Math.max(1, data.lives_total));
      }
      if (typeof data.lives_remaining === 'number') {
        lives = Math.max(0, data.lives_remaining);
      }
      score = typeof data.score === 'number' ? data.score : score;
      penaltyMessage = '';
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
      penaltyMessage = data.message || `Try that again in ${targetLang}.`;
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
      playBeep();
    } else if (result?.nextScenario) {
      const next = result.nextScenario;
      if (typeof next === 'object' && next?.id) {
        storyStore.goToScenario(next.id);
      } else if (typeof next === 'number') {
        storyStore.goToScenario(next);
      }
      resetLives();
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
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
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

          if (streamingEnabled) {
            return;
          }

          const formData = new FormData();
          formData.append('audio_file', audioBlob, 'recording.webm');

          try {
            if (requireRepeat && selectedOption) {
              evaluating = true;
              lastHeard = '';
              formData.append('expected', selectedOption.example?.target || '');
              if (selectedOption.next_scenario != null) formData.append('next_scenario', String(selectedOption.next_scenario));
              if (targetLang) formData.append('lang', targetLang);
              const response = await fetch(`${getBackendUrl()}/narrative/imitate`, { method: 'POST', body: formData });
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              const result = await response.json();
              applyInteractionResult(result);
            } else {
              formData.append('current_scenario_id', $storyStore.id);
              if (targetLang) formData.append('lang', targetLang);
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
          mediaRecorder.start(400);
        } else {
          mediaRecorder.start();
        }
        isRecording = true;

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
    // Dev back button visibility: only in dev build or URL/localStorage flag
    try {
      devMode = (import.meta?.env?.DEV === true) || /[?&]dev=1\b/.test(window.location.search) || localStorage.getItem('DEV_BACK') === '1';
    } catch (_) {}
    if ($storyStore.audio_to_play_url) {
        audioPlayer.src = $storyStore.audio_to_play_url;
    }
    window.addEventListener('click', handleFirstInteraction);

    // Resolve backend dynamically if needed
    discoverBackend().catch(() => {});

    streamMode = getStreamMode();
    streamingEnabled = streamMode !== 'off';
    resetStreamState();

    // Client-only fetching of speaking suggestions on scenario changes
    let lastScenarioId = null;
    const fetchSuggestions = async (sid) => {
      try {
        const url = `${getBackendUrl()}/narrative/options?scenario_id=${encodeURIComponent(sid)}&n_per_option=3&lang=${encodeURIComponent(targetLang)}&native=${encodeURIComponent(nativeLang)}&stage=examples`;
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
        score = 0;
        const scenarioLives = Number(s?.lives ?? s?.max_lives ?? s?.lives_total);
        if (Number.isFinite(scenarioLives) && scenarioLives > 0) {
          livesTotal = Math.floor(scenarioLives);
        }
        resetLives();
        // Only fetch if no local examples available
        if (!localSuggestions) fetchSuggestions(s.id);
      }
    });
    return () => {
      unsub();
      window.removeEventListener('click', handleFirstInteraction);
    };
  });

  onDestroy(() => {
    closeStream('component_destroy');
  });

  async function translateNativeText() {
    const t = (myNativeText || '').trim();
    if (!t) return;
    translating = true;
    try {
      const fd = new FormData();
      fd.append('native', 'English');
      fd.append('target', targetLang);
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
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        nativeRecorder = new MediaRecorder(stream);
        nativeRecorder.ondataavailable = (e) => { nativeChunks.push(e.data); };
        nativeRecorder.onstop = async () => {
          const blob = new Blob(nativeChunks, { type: 'audio/webm' });
          nativeChunks = [];
          const fd = new FormData();
          fd.append('native', 'English');
          fd.append('target', targetLang);
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
    on:toggle={toggleRecording}
    on:devBack={() => storyStore.goBack()}
  />
  {#if lastHeard && !requireRepeat}
    <div class="heard">Heard: <em>{lastHeard}</em>{evaluating ? ' …' : ''}</div>
  {/if}

  <ScenarioStatus
    {lives}
    {livesTotal}
    {score}
    {penaltyMessage}
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
    {translating}
    {isNativeRecording}
    fallbackOptions={$storyStore.options ?? []}
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
</style>
