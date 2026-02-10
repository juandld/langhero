<script>
  /**
   * FirstChallenge - First interactive speaking moment in the story.
   *
   * Features:
   * - Time-frozen cinematic background
   * - Phrase display with pronunciation
   * - Listen button to hear the phrase
   * - Speech recognition for player response
   * - Success/failure feedback
   */
  import { createEventDispatcher, onMount, onDestroy, getContext } from 'svelte';
  import { fade, fly, scale } from 'svelte/transition';
  import { cubicOut } from 'svelte/easing';
  import { getTTS, getApiBase } from '$lib/api';
  import { masterVolume, playbackSpeed } from '$lib/audioStore.js';
  import { createStreamingManager } from '$lib/game/streamingManager';
  import { playBeep, speakWithSynthesis } from '$lib/game/audioUtils';

  /** @type {{ options?: Array<{ examples?: Array<{ target: string, native: string, pronunciation: string }> }> } | null} */
  export let scenario = null;
  /** @type {{ id?: string, image_url?: string, mood?: string } | null} */
  export let panel = null;

  const dispatch = createEventDispatcher();
  const aesthetic = getContext('aesthetic');

  // Get the first phrase to learn from scenario
  $: phrase = scenario?.options?.[0]?.examples?.[0] || {
    target: '私は...旅人です。',
    native: 'I am... a traveler.',
    pronunciation: 'Watashi wa... tabibito desu.'
  };

  // State
  let audioElement = null;
  let isPlayingAudio = false;
  let isListening = false;
  let showMicrophone = false;
  let lastHeard = '';
  let matchResult = null;
  let attempts = 0;
  let showSuccess = false;

  // Streaming manager for speech recognition
  const streamingManager = createStreamingManager({
    onResult: handleSpeechResult,
    onError: (err) => console.warn('Speech error:', err),
  });

  // Background image
  $: backgroundUrl = panel?.image_url || 'https://images.unsplash.com/photo-1507400492013-162706c8c05e?w=1200&q=80';

  // Play the phrase audio
  async function playPhrase() {
    if (isPlayingAudio) return;
    isPlayingAudio = true;

    try {
      const response = await getTTS({
        text: phrase.target,
        role: 'teacher',
        language: 'Japanese',
      });

      if (response.url && !response.error) {
        if (audioElement) {
          audioElement.pause();
        }

        audioElement = new Audio(response.url);
        audioElement.playbackRate = $playbackSpeed;
        audioElement.volume = $masterVolume;
        audioElement.onended = () => {
          isPlayingAudio = false;
          showMicrophone = true;  // Show mic after listening
        };
        audioElement.onerror = () => {
          isPlayingAudio = false;
          showMicrophone = true;  // Show mic even on error
        };

        await audioElement.play();
      } else {
        // Fallback to speech synthesis
        speakWithSynthesis(phrase.target, 'ja-JP');
        isPlayingAudio = false;
        showMicrophone = true;  // Show mic after synthesis
      }
    } catch (e) {
      console.warn('Failed to play phrase:', e);
      speakWithSynthesis(phrase.target, 'ja-JP');
      isPlayingAudio = false;
      showMicrophone = true;  // Show mic even on error
    }
  }

  // Start listening for speech
  async function startListening() {
    if (isListening) return;

    showMicrophone = true;
    isListening = true;
    lastHeard = '';
    matchResult = null;

    try {
      await streamingManager.connect({
        scenarioId: scenario?.id || 100,
        language: 'Japanese',
        judgeThreshold: 0.6, // More lenient for first challenge
      });
    } catch (e) {
      console.warn('Failed to start listening:', e);
      isListening = false;
    }
  }

  // Stop listening
  function stopListening() {
    isListening = false;
    streamingManager.disconnect();
  }

  // Handle speech recognition result
  function handleSpeechResult(result) {
    isListening = false;
    attempts++;

    if (result.heard) {
      lastHeard = result.heard;
    }

    const confidence = Number(result.confidence ?? result.match_confidence ?? 0);
    const matchType = result.match_type || result.matchType || '';

    if (matchType === 'exact' || matchType === 'close' || confidence > 0.7) {
      // Success!
      matchResult = 'success';
      playBeep({ frequency: 880, duration: 100 });
      setTimeout(() => playBeep({ frequency: 1100, duration: 150 }), 120);

      showSuccess = true;
      setTimeout(() => {
        dispatch('success');
      }, 1500);
    } else if (attempts >= 3) {
      // After 3 attempts, let them through with encouragement
      matchResult = 'pass';
      showSuccess = true;
      setTimeout(() => {
        dispatch('success');
      }, 1500);
    } else {
      // Try again
      matchResult = 'retry';
      playBeep({ frequency: 300, duration: 200 });
    }
  }

  // Keyboard handling
  function handleKeydown(e) {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      if (!showMicrophone) {
        playPhrase();
      } else if (!isListening && !showSuccess) {
        startListening();
      }
    } else if (e.key === 'Escape') {
      dispatch('skip');
    }
  }

  onMount(() => {
    // Auto-play phrase on mount after a brief delay
    setTimeout(playPhrase, 800);
  });

  onDestroy(() => {
    if (audioElement) {
      audioElement.pause();
      audioElement = null;
    }
    streamingManager.disconnect();
  });
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="first-challenge" style="--bg-url: url({backgroundUrl})">
  <!-- Background with time-frozen effect -->
  <div class="background-layer">
    <div class="background-image"></div>
    <div class="time-freeze-overlay"></div>
    <div class="frozen-particles">
      {#each Array(20) as _, i}
        <div
          class="frozen-particle"
          style="
            left: {5 + Math.random() * 90}%;
            top: {5 + Math.random() * 90}%;
            animation-delay: {i * 0.15}s;
          "
        ></div>
      {/each}
    </div>
  </div>

  <!-- Bimbo orb (always visible, guiding) -->
  <div class="bimbo-orb" in:scale={{ duration: 400, delay: 300 }}>
    <div class="orb-glow"></div>
    <div class="orb-core"></div>
  </div>

  <!-- Main content -->
  <div class="challenge-content">
    <!-- Phrase card -->
    <div class="phrase-card" in:fly={{ y: 30, duration: 500, delay: 200 }}>
      <div class="phrase-label">Say this:</div>
      <div class="phrase-target">{phrase.target}</div>
      <div class="phrase-pronunciation">{phrase.pronunciation}</div>
      <div class="phrase-native">{phrase.native}</div>
    </div>

    <!-- Listen button -->
    {#if !showMicrophone}
      <button
        class="listen-btn"
        class:playing={isPlayingAudio}
        on:click={playPhrase}
        in:fly={{ y: 20, duration: 400, delay: 400 }}
      >
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/>
        </svg>
        {isPlayingAudio ? 'Playing...' : 'Listen'}
      </button>
    {/if}

    <!-- Microphone section -->
    {#if showMicrophone && !showSuccess}
      <div class="mic-section" in:fly={{ y: 20, duration: 400 }}>
        <!-- Listen again button -->
        <button
          class="listen-again-btn"
          class:playing={isPlayingAudio}
          on:click={playPhrase}
          disabled={isListening}
        >
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
          </svg>
          {isPlayingAudio ? 'Playing...' : 'Listen again'}
        </button>

        {#if lastHeard && matchResult === 'retry'}
          <div class="heard-text" in:fade>
            I heard: "{lastHeard}"
          </div>
          <div class="retry-hint">Try again! Focus on the sounds.</div>
        {/if}

        <button
          class="mic-btn"
          class:listening={isListening}
          on:click={isListening ? stopListening : startListening}
        >
          <div class="mic-ring" class:active={isListening}></div>
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.91-3c-.49 0-.9.36-.98.85C16.52 14.2 14.47 16 12 16s-4.52-1.8-4.93-4.15c-.08-.49-.49-.85-.98-.85-.61 0-1.09.54-1 1.14.49 3 2.89 5.35 5.91 5.78V20c0 .55.45 1 1 1s1-.45 1-1v-2.08c3.02-.43 5.42-2.78 5.91-5.78.1-.6-.39-1.14-1-1.14z"/>
          </svg>
        </button>

        <div class="mic-hint">
          {isListening ? 'Listening... Speak now!' : 'Tap to speak'}
        </div>
      </div>
    {/if}

    <!-- Success state -->
    {#if showSuccess}
      <div class="success-overlay" in:scale={{ duration: 300 }}>
        <div class="success-icon">
          <svg viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
        </div>
        <div class="success-text">
          {matchResult === 'pass' ? 'Good effort!' : 'Perfect!'}
        </div>
      </div>
    {/if}

    <!-- Initial instruction -->
    {#if !showMicrophone}
      <div class="instruction" in:fade={{ delay: 600 }}>
        Tap to hear the phrase, then speak it back
      </div>
    {/if}
  </div>

  <!-- Skip button -->
  <button class="skip-btn" on:click={() => dispatch('skip')}>
    Skip
  </button>
</div>

<style>
  .first-challenge {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 100;
    overflow: hidden;
  }

  /* Background */
  .background-layer {
    position: absolute;
    inset: 0;
  }

  .background-image {
    position: absolute;
    inset: 0;
    background-image: var(--bg-url);
    background-size: cover;
    background-position: center;
    filter: brightness(0.4) saturate(0.7);
  }

  .time-freeze-overlay {
    position: absolute;
    inset: 0;
    background: rgba(139, 92, 246, 0.15);
    mix-blend-mode: overlay;
  }

  .frozen-particles {
    position: absolute;
    inset: 0;
  }

  .frozen-particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(196, 181, 253, 0.6);
    border-radius: 50%;
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.8);
    animation: particle-float 4s ease-in-out infinite alternate;
  }

  @keyframes particle-float {
    0% { transform: translateY(0) scale(1); opacity: 0.5; }
    100% { transform: translateY(-15px) scale(0.7); opacity: 1; }
  }

  /* Bimbo orb */
  .bimbo-orb {
    position: absolute;
    top: 80px;
    left: 50%;
    transform: translateX(-50%);
    width: 60px;
    height: 60px;
    z-index: 10;
  }

  .orb-glow {
    position: absolute;
    inset: -15px;
    background: radial-gradient(circle, rgba(251, 191, 36, 0.4) 0%, transparent 70%);
    animation: orb-pulse 2s ease-in-out infinite;
  }

  .orb-core {
    position: absolute;
    inset: 8px;
    background: radial-gradient(circle at 30% 30%, #fde68a 0%, #fbbf24 50%, #d97706 100%);
    border-radius: 50%;
    box-shadow: 0 0 20px rgba(251, 191, 36, 0.6);
  }

  @keyframes orb-pulse {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.15); opacity: 1; }
  }

  /* Content */
  .challenge-content {
    position: relative;
    z-index: 20;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 24px;
    max-width: 400px;
    width: 100%;
  }

  /* Phrase card */
  .phrase-card {
    background: rgba(26, 21, 21, 0.95);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(139, 92, 246, 0.3);
    border-radius: 16px;
    padding: 24px;
    width: 100%;
    text-align: center;
    box-shadow: 0 0 30px rgba(139, 92, 246, 0.2);
  }

  .phrase-label {
    font-size: 0.85rem;
    color: rgba(196, 181, 253, 0.8);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
  }

  .phrase-target {
    font-size: 1.8rem;
    font-weight: 600;
    color: #fef3c7;
    margin-bottom: 8px;
    line-height: 1.4;
  }

  .phrase-pronunciation {
    font-size: 1.1rem;
    color: #c4b5fd;
    font-style: italic;
    margin-bottom: 12px;
  }

  .phrase-native {
    font-size: 0.95rem;
    color: rgba(254, 243, 199, 0.6);
  }

  /* Listen button */
  .listen-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    background: rgba(139, 92, 246, 0.3);
    border: 1px solid rgba(139, 92, 246, 0.5);
    color: #c4b5fd;
    padding: 14px 28px;
    border-radius: 30px;
    font-size: 1.1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .listen-btn:hover {
    background: rgba(139, 92, 246, 0.4);
    transform: scale(1.02);
  }

  .listen-btn.playing {
    background: rgba(139, 92, 246, 0.5);
    animation: pulse-glow 1s ease-in-out infinite;
  }

  .listen-btn svg {
    width: 24px;
    height: 24px;
  }

  @keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 10px rgba(139, 92, 246, 0.3); }
    50% { box-shadow: 0 0 25px rgba(139, 92, 246, 0.6); }
  }

  /* Listen again button (smaller, in mic section) */
  .listen-again-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(139, 92, 246, 0.2);
    border: 1px solid rgba(139, 92, 246, 0.3);
    color: #a78bfa;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .listen-again-btn:hover:not(:disabled) {
    background: rgba(139, 92, 246, 0.3);
  }

  .listen-again-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .listen-again-btn.playing {
    background: rgba(139, 92, 246, 0.4);
  }

  .listen-again-btn svg {
    width: 16px;
    height: 16px;
  }

  /* Microphone section */
  .mic-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .heard-text {
    background: rgba(220, 38, 38, 0.2);
    border: 1px solid rgba(220, 38, 38, 0.4);
    color: #fca5a5;
    padding: 10px 20px;
    border-radius: 12px;
    font-size: 0.95rem;
  }

  .retry-hint {
    color: rgba(254, 243, 199, 0.7);
    font-size: 0.9rem;
  }

  .mic-btn {
    position: relative;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: rgba(34, 197, 94, 0.3);
    border: 2px solid rgba(34, 197, 94, 0.6);
    color: #86efac;
    cursor: pointer;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .mic-btn:hover {
    background: rgba(34, 197, 94, 0.4);
    transform: scale(1.05);
  }

  .mic-btn.listening {
    background: rgba(34, 197, 94, 0.5);
    border-color: #86efac;
  }

  .mic-btn svg {
    width: 36px;
    height: 36px;
    z-index: 1;
  }

  .mic-ring {
    position: absolute;
    inset: -8px;
    border: 2px solid transparent;
    border-radius: 50%;
    transition: all 0.3s;
  }

  .mic-ring.active {
    border-color: rgba(34, 197, 94, 0.6);
    animation: ring-pulse 1s ease-out infinite;
  }

  @keyframes ring-pulse {
    0% { transform: scale(1); opacity: 1; }
    100% { transform: scale(1.4); opacity: 0; }
  }

  .mic-hint {
    color: rgba(254, 243, 199, 0.6);
    font-size: 0.9rem;
  }

  /* Success overlay */
  .success-overlay {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
  }

  .success-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: rgba(34, 197, 94, 0.3);
    border: 2px solid #86efac;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #86efac;
    animation: success-bounce 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .success-icon svg {
    width: 40px;
    height: 40px;
  }

  @keyframes success-bounce {
    0% { transform: scale(0); }
    60% { transform: scale(1.2); }
    100% { transform: scale(1); }
  }

  .success-text {
    font-size: 1.5rem;
    font-weight: 700;
    color: #86efac;
    text-shadow: 0 0 20px rgba(34, 197, 94, 0.5);
  }

  /* Instruction */
  .instruction {
    color: rgba(254, 243, 199, 0.5);
    font-size: 0.9rem;
    text-align: center;
  }

  /* Skip button */
  .skip-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    background: rgba(0, 0, 0, 0.5);
    border: 1px solid rgba(254, 243, 199, 0.2);
    color: rgba(254, 243, 199, 0.6);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    z-index: 100;
    transition: all 0.2s;
  }

  .skip-btn:hover {
    background: rgba(0, 0, 0, 0.7);
    color: rgba(254, 243, 199, 0.9);
  }

  /* Mobile adjustments */
  @media (max-width: 500px) {
    .phrase-target {
      font-size: 1.5rem;
    }

    .bimbo-orb {
      width: 50px;
      height: 50px;
      top: 60px;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .frozen-particle,
    .orb-glow,
    .mic-ring.active,
    .listen-btn.playing {
      animation: none;
    }
  }
</style>
