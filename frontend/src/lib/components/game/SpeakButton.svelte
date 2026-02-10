<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let isRecording = false;
  export let isEvaluating = false;
  export let isTimeStopped = true;
  export let analyser = null;

  const dispatch = createEventDispatcher();

  let waveCanvas;
  let canvasCtx = null;
  let dataArray = null;
  let animationId = null;
  let lastDrawTime = 0;
  const FRAME_INTERVAL = 50; // ~20fps

  function toggleRecording() {
    dispatch('toggle');
  }

  // Draw waveform visualization
  function drawWaveform(timestamp) {
    if (!waveCanvas || !analyser || !isRecording) {
      if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
      }
      return;
    }

    if (timestamp - lastDrawTime < FRAME_INTERVAL) {
      animationId = requestAnimationFrame(drawWaveform);
      return;
    }
    lastDrawTime = timestamp;

    if (!canvasCtx) {
      canvasCtx = waveCanvas.getContext('2d');
    }
    if (!dataArray) {
      dataArray = new Uint8Array(analyser.frequencyBinCount);
    }

    analyser.getByteFrequencyData(dataArray);

    const width = waveCanvas.width;
    const height = waveCanvas.height;

    // Clear with rounded rect
    canvasCtx.clearRect(0, 0, width, height);
    canvasCtx.fillStyle = 'rgba(255, 255, 255, 0.1)';
    canvasCtx.fillRect(0, 0, width, height);

    // Draw bars
    const barCount = dataArray.length;
    const barWidth = width / barCount;
    canvasCtx.fillStyle = isTimeStopped ? '#a78bfa' : '#f87171';

    for (let i = 0; i < barCount; i++) {
      const barHeight = (dataArray[i] / 255) * height * 0.85;
      canvasCtx.fillRect(
        i * barWidth + 1,
        height - barHeight,
        barWidth - 2,
        barHeight
      );
    }

    animationId = requestAnimationFrame(drawWaveform);
  }

  function startWaveform() {
    if (animationId) return;
    canvasCtx = null;
    dataArray = null;
    lastDrawTime = 0;
    animationId = requestAnimationFrame(drawWaveform);
  }

  function stopWaveform() {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    if (waveCanvas && canvasCtx) {
      canvasCtx.clearRect(0, 0, waveCanvas.width, waveCanvas.height);
    }
  }

  $: if (isRecording && analyser && waveCanvas) {
    startWaveform();
  } else if (!isRecording) {
    stopWaveform();
  }

  onDestroy(() => {
    stopWaveform();
  });

  $: buttonLabel = isTimeStopped
    ? (isRecording ? 'Stop & Submit' : 'Release Time & Speak')
    : (isRecording ? 'Stop Speaking' : 'Speak');

  $: buttonIcon = isRecording ? 'stop' : 'mic';
</script>

<div class="speak-button-container">
  {#if isRecording}
    <canvas bind:this={waveCanvas} width="280" height="40" class="waveform"></canvas>
  {/if}

  <button
    class="speak-button"
    class:recording={isRecording}
    class:evaluating={isEvaluating}
    class:time-stopped={isTimeStopped && !isRecording}
    on:click={toggleRecording}
    disabled={isEvaluating}
    aria-label={buttonLabel}
  >
    <span class="button-icon">
      {#if isRecording}
        <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
          <rect x="6" y="6" width="12" height="12" rx="2"/>
        </svg>
      {:else}
        <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
          <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"/>
        </svg>
      {/if}
    </span>
    <span class="button-text">{buttonLabel}</span>
  </button>

  {#if isEvaluating}
    <div class="evaluating-indicator">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="eval-text">Processing...</span>
    </div>
  {/if}
</div>

<style>
  .speak-button-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    width: 100%;
    max-width: 320px;
    margin: 0 auto;
  }

  .waveform {
    width: 100%;
    height: 40px;
    border-radius: 12px;
    background: rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(8px);
  }

  .speak-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: 100%;
    padding: 16px 24px;
    border: none;
    border-radius: 16px;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
    transition: transform 0.15s ease, box-shadow 0.2s ease, background 0.2s ease;
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    box-shadow: 0 4px 20px rgba(249, 115, 22, 0.4);
  }

  .speak-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 28px rgba(249, 115, 22, 0.5);
  }

  .speak-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .speak-button.time-stopped {
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
  }

  .speak-button.time-stopped:hover:not(:disabled) {
    box-shadow: 0 6px 28px rgba(99, 102, 241, 0.5);
  }

  .speak-button.recording {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4);
    animation: pulse-record 1.5s ease-in-out infinite;
  }

  @keyframes pulse-record {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 4px 20px rgba(239, 68, 68, 0.4);
    }
    50% {
      transform: scale(1.02);
      box-shadow: 0 6px 30px rgba(239, 68, 68, 0.6);
    }
  }

  .speak-button.evaluating {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    cursor: wait;
    animation: pulse-eval 1s ease-in-out infinite;
  }

  @keyframes pulse-eval {
    0%, 100% {
      opacity: 0.9;
    }
    50% {
      opacity: 1;
    }
  }

  .speak-button:disabled {
    cursor: wait;
  }

  .button-icon {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .button-text {
    letter-spacing: 0.02em;
  }

  .evaluating-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    background: rgba(245, 158, 11, 0.2);
    border: 1px solid rgba(245, 158, 11, 0.4);
    border-radius: 12px;
  }

  .dot {
    width: 8px;
    height: 8px;
    background: #f59e0b;
    border-radius: 50%;
    animation: bounce-dot 1.4s ease-in-out infinite;
  }

  .dot:nth-child(1) { animation-delay: 0s; }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce-dot {
    0%, 80%, 100% {
      transform: scale(1);
      opacity: 0.5;
    }
    40% {
      transform: scale(1.3);
      opacity: 1;
    }
  }

  .eval-text {
    font-size: 0.9rem;
    font-weight: 600;
    color: #f59e0b;
    margin-left: 4px;
  }
</style>
