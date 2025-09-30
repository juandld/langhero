<script>
  import { storyStore } from '$lib/storyStore.js';
  import { getBackendUrl, discoverBackend } from '$lib/config';
  import { onMount } from 'svelte';

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
  let devMode = false;
  let lastHeard = '';
  let evaluating = false;
  const STYLE_LABELS = {
    'polite': 'Polite',
    'casual': 'Casual',
    'polite-decline': 'Polite decline',
    'rude': 'Rude',
  };
  // Make-your-own line (native -> translate -> try)
  let myNativeText = '';
  let translating = false;
  let isNativeRecording = false;
  let nativeRecorder;
  let nativeChunks = [];

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

  function playExampleAudio(url) {
    // Prefer example audio; if unavailable or fails quickly, beep.
    if (!url) {
      playBeep();
      return;
    }
    try {
      const a = new Audio(`${getBackendUrl()}${url}`);
      let fallbackDone = false;
      const doFallback = () => { if (!fallbackDone) { fallbackDone = true; playBeep(); } };
      a.addEventListener('error', doFallback, { once: true });
      a.addEventListener('stalled', doFallback, { once: true });
      // If it hasn't started within 700ms, fallback
      setTimeout(() => { if (a.paused) doFallback(); }, 700);
      a.play().catch(doFallback);
    } catch (_) {
      playBeep();
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

  async function toggleRecording() {
    if (isRecording) {
      // Stop recording
      if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
      }
      isRecording = false;
    } else {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        
        mediaRecorder.ondataavailable = event => {
          audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
          audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
          audioChunks = [];
          
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
              lastHeard = result?.heard || '';
              if (result.success && result.nextScenario != null) {
                requireRepeat = false;
                lives = 3;
                storyStore.goToScenario(result.nextScenario);
              } else {
                // Only lose a life if it doesn't make sense
                if (result?.makesSense === false) {
                  lives = Math.max(0, lives - 1);
                }
                playBeep({ frequency: 440, duration: 200 });
                if (lives === 0) {
                  alert("Out of lives. Try a different option.");
                  requireRepeat = false;
                }
              }
              evaluating = false;
            } else {
              formData.append('current_scenario_id', $storyStore.id);
              if (targetLang) formData.append('lang', targetLang);
              const response = await fetch(`${getBackendUrl()}/narrative/interaction`, { method: 'POST', body: formData });
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              const result = await response.json();
              lastHeard = result?.heard || '';
              // If backend suggests a repeat in Japanese, enter repeat mode with suggested line
              if (result?.repeatExpected) {
                selectedOption = {
                  next_scenario: (result?.repeatNextScenario ?? null),
                  example: {
                    native: lastHeard || '',
                    target: result.repeatExpected || '',
                    pronunciation: result.pronunciation || ''
                  }
                };
                lives = 3;
                requireRepeat = true;
                playBeep();
              } else if (result.nextScenario) {
                storyStore.goToScenario(result.nextScenario.id);
              } else {
                // If suggestions/options are available, don't interrupt with alert
                // Users can pick an example chip or try again
                playBeep({ frequency: 440, duration: 160 });
              }
            }
          } catch (error) {
            console.error("Error sending audio to backend:", error);
            alert("There was an issue connecting to the server. Please try again.");
          }
        };

        audioChunks = [];
        mediaRecorder.start();
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
        // Only fetch if no local examples available
        if (!localSuggestions) fetchSuggestions(s.id);
      }
    });
    return () => {
      unsub();
      window.removeEventListener('click', handleFirstInteraction);
    };
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
        lives = 3;
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
              lives = 3;
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
  {#if $storyStore.image_url}
    <img src={$storyStore.image_url} alt="Scenario" class="scenario-image" on:error={(e) => e.currentTarget && (e.currentTarget.style.display = 'none')} />
  {/if}

  <div class="dialogue-box">
    <p class="character-dialogue-jp">{$storyStore.character_dialogue_jp}</p>
    <p class="character-dialogue-en"><em>{$storyStore.character_dialogue_en}</em></p>
  </div>

  {#if $storyStore.description}
    <p class="user-prompt">{$storyStore.description}</p>
  {/if}

  <div class="controls">
    <button 
      class="record-button" 
      class:isRecording 
      on:click={toggleRecording}
      aria-label={isRecording ? 'Stop Recording' : 'Start Recording'}
    >
      <svg viewBox="0 0 24 24" width="24" height="24" fill="white">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"/>
      </svg>
    </button>
    {#if devMode}
      <button class="dev-back" on:click={() => storyStore.goBack()} title="Back (dev)">⟲ Back</button>
    {/if}
  </div>
  {#if isRecording}
    <canvas width="300" height="40" class="wave"></canvas>
  {/if}
  {#if lastHeard && !requireRepeat}
    <div class="heard">Heard: <em>{lastHeard}</em>{evaluating ? ' …' : ''}</div>
  {/if}

  <!-- For now, we'll include clickable text options to test the story flow -->
  <div class="options-block">
    {#if localSuggestions || speakingSuggestions}
      <h3 class="prompt-question">{requireRepeat ? 'Say this' : ((localSuggestions?.question || speakingSuggestions?.question) || 'What do you say?')}</h3>
      {#if requireRepeat && selectedOption}
        <div class="say-panel">
          {#if selectedOption.example?.native}
            <div class="line-native">{selectedOption.example.native}</div>
          {/if}
          <div class="line-target">{selectedOption.example?.target}</div>
          {#if selectedOption.example?.pronunciation}
            <div class="line-pron">{selectedOption.example.pronunciation}</div>
          {/if}
          <div class="lives">Lives: {lives}</div>
          <div class="say-actions">
            <button type="button" class="chip-advance" on:click={() => { playBeep(); }}>▶</button>
          </div>
          {#if lastHeard}
            <div class="heard">Heard: <em>{lastHeard}</em>{evaluating ? ' …' : ''}</div>
          {/if}
        </div>
      {/if}
      {#each (localSuggestions ? localSuggestions.options : speakingSuggestions.options) as opt, i}
        {#if opt.examples && opt.examples.length}
          <div class="chips" role="list">
            <div class="chip-group" role="group" aria-label="Example option">
              <button type="button" class="chip-advance" on:click={() => { selectedOption = { next_scenario: opt.next_scenario, example: opt.examples[0] }; requireRepeat = true; playBeep(); }}>
                <div class="line-native">▶ {opt.examples[0].native || opt.examples[0].target}</div>
                <div class="line-target">{opt.examples[0].target || opt.examples[0].native}</div>
                {#if opt.examples[0].pronunciation}
                  <div class="line-pron">{opt.examples[0].pronunciation}</div>
                {/if}
              </button>
            </div>
          </div>
        {/if}
      {/each}
    {:else}
      <div class="debug-options">
        {#each $storyStore.options as option}
          <button type="button" class="chip-advance" on:click={() => { selectedOption = { next_scenario: option.next_scenario, example: { native: option.text, target: option.text } }; requireRepeat = true; playBeep(); }}>
            <div class="line-native">▶ {option.text}</div>
            <div class="line-target">{option.text}</div>
          </button>
        {/each}
      </div>
    {/if}
    <div class="make-own">
      <div class="make-label">Make your own line</div>
      <div class="make-row">
        <input class="make-input" bind:value={myNativeText} placeholder="Type in your language" />
        <button class="make-btn" on:click={translateNativeText} disabled={translating}>{translating ? '...' : 'Translate'}</button>
        <button class="make-btn" on:click={toggleNativeRecording}>{isNativeRecording ? 'Stop' : '🎤 Speak'}</button>
      </div>
    </div>
  </div>

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
  .scenario-image {
    width: 100%;
    height: auto;
    border-radius: 12px;
    margin-bottom: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  .dialogue-box {
    background-color: #f0f0f0;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 20px;
    width: 100%;
  }
  .character-dialogue-jp {
    font-size: 1.5rem;
    font-weight: bold;
    margin: 0;
  }
  .character-dialogue-en {
    font-size: 1rem;
    color: #555;
    margin: 5px 0 0 0;
  }
  .user-prompt {
    font-size: 1.2rem;
    font-weight: 500;
    margin-bottom: 20px;
  }
  .controls {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .wave { width: 100%; max-width: 400px; height: 40px; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 10px; }
  .options-block {
    width: 100%;
    margin-top: 8px;
    text-align: left;
  }
  .prompt-question {
    margin: 6px 0 10px;
    font-size: 1rem;
    color: #374151;
  }
  .make-own { margin-top: 16px; }
  .make-label { font-weight: 600; margin-bottom: 6px; color: #374151; }
  .make-row { display: flex; gap: 8px; align-items: center; }
  .make-input { flex: 1; padding: 8px 10px; border: 1px solid #e5e7eb; border-radius: 8px; }
  .make-btn { padding: 8px 10px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f9fafb; cursor: pointer; }
  .make-btn:hover { background: #f3f4f6; }
  .say-panel { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
  .say-actions { display: inline-flex; gap: 8px; }
  .lives { margin-left: 6px; font-size: 0.9rem; color: #6b7280; }
  .heard { margin-left: 6px; font-size: 0.9rem; color: #6b7280; margin-top: 4px; }
  .option-group { margin: 8px 0 14px; }
  .style-badge {
    display: inline-block;
    margin-left: 8px;
    padding: 2px 6px;
    border-radius: 10px;
    font-size: 0.75rem;
    border: 1px solid transparent;
  }
  .style-badge.polite { background: #ecfdf5; color: #065f46; border-color: #a7f3d0; }
  .style-badge.casual { background: #eff6ff; color: #1e40af; border-color: #bfdbfe; }
  .style-badge[class*="decline"] { background: #fef3c7; color: #92400e; border-color: #fde68a; }
  .style-badge.rude { background: #fee2e2; color: #991b1b; border-color: #fecaca; }
  .chips { display: flex; flex-wrap: wrap; gap: 10px; }
  .chip-group { display: inline-flex; align-items: center; gap: 6px; }
  .chip-advance {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 6px 10px;
    font-size: 0.9rem;
    cursor: pointer;
  }
  .chip-advance:hover { background: #e5e7eb; }
  .chip-advance .line-native { text-align: left; }
  .chip-advance .line-target { text-align: left; }
  .line-native { font-size: 0.85rem; color: #4b5563; }
  .line-target { font-size: 1rem; font-weight: 600; color: #111827; }
  .line-pron { font-size: 0.85rem; color: #6b7280; font-style: italic; }
  .chip-play { background: #111827; color: white; border: none; border-radius: 9999px; padding: 6px 10px; cursor: pointer; }
  .chip-play:hover { background: #1f2937; }
  .record-button {
    background-color: #e63946;
    border: none;
    border-radius: 50%;
    width: 64px;
    height: 64px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
    transition: background-color 0.2s, transform 0.2s;
  }
  .record-button:hover {
    background-color: #d62828;
  }
  .record-button.isRecording {
    background-color: #a8202a;
    transform: scale(0.95);
  }
  .debug-options button {
    margin: 0 5px;
    padding: 8px 12px;
    border-radius: 6px;
    border: 1px solid #ccc;
    cursor: pointer;
  }
  .dev-back {
    background: #111827;
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    cursor: pointer;
  }
  .dev-back:hover { background: #1f2937; }
</style>
