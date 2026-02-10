<script>
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';

  export let isRecording = false;
  export let evaluating = false;
  export let devMode = false;
  export let mode = 'beginner';
  export let micDevices = [];
  export let micDeviceId = '';
  export let analyser = null;

  const dispatch = createEventDispatcher();
  export let waveCanvas;

  let animationId = null;
  let canvasCtx = null;
  let dataArray = null;
  let lastDrawTime = 0;
  const FRAME_INTERVAL = 50; // ~20fps instead of 60fps

  // Draw waveform visualization (throttled)
  function drawWaveform(timestamp) {
    if (!waveCanvas || !analyser || !isRecording) {
      if (animationId) {
        cancelAnimationFrame(animationId);
        animationId = null;
      }
      return;
    }

    // Throttle to ~20fps
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

    // Clear canvas
    canvasCtx.fillStyle = '#fefefe';
    canvasCtx.fillRect(0, 0, width, height);

    // Draw bars with single color (much faster)
    const barCount = dataArray.length;
    const barWidth = width / barCount;
    canvasCtx.fillStyle = '#f97316';

    for (let i = 0; i < barCount; i++) {
      const barHeight = (dataArray[i] / 255) * height * 0.9;
      canvasCtx.fillRect(
        i * barWidth + 0.5,
        height - barHeight,
        barWidth - 1,
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
      canvasCtx.fillStyle = '#fefefe';
      canvasCtx.fillRect(0, 0, waveCanvas.width, waveCanvas.height);
    }
  }

  // Watch for recording state changes
  $: if (isRecording && analyser && waveCanvas) {
    startWaveform();
  } else if (!isRecording) {
    stopWaveform();
  }

  onDestroy(() => {
    stopWaveform();
  });

  const toggleRecording = () => dispatch('toggle');
  const handleDevBack = () => dispatch('devBack');
  const refreshMics = () => dispatch('refreshMics');
  const handleMicChange = (event) => {
    micDeviceId = event?.currentTarget?.value || '';
    dispatch('micChange', { deviceId: micDeviceId });
  };

  $: isLiveMode = (mode || '').toLowerCase() === 'advanced';
  $: ariaLabel = isLiveMode
    ? (isRecording ? 'Stop live streaming answer' : 'Start live streaming answer')
    : (isRecording ? 'Stop high-stakes response recording' : 'Start high-stakes response recording');
  $: titleText = isLiveMode
    ? (isRecording ? 'Stop live mic' : 'Start live mic (lives burn immediately)')
    : (isRecording ? 'Stop risky response' : 'Record answer (rewind spent if wrong)');
</script>

<div class="controls">
  <button
    class="record-button"
    class:isRecording
    class:isEvaluating={evaluating && !isRecording}
    on:click={toggleRecording}
    aria-label={ariaLabel}
    title={titleText}
    disabled={evaluating}
  >
    <svg viewBox="0 0 24 24" width="24" height="24" fill="white">
      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm5.3-3c0 3-2.54 5.1-5.3 5.1S6.7 14 6.7 11H5c0 3.41 2.72 6.23 6 6.72V21h2v-3.28c3.28-.49 6-3.31 6-6.72h-1.7z"/>
    </svg>
  </button>
  {#if Array.isArray(micDevices)}
    <div class="mic">
      <label class="micLabel" for="micSelect">Mic</label>
      <select id="micSelect" class="micSelect" value={micDeviceId} on:change={handleMicChange} disabled={isRecording}>
        <option value="">Default</option>
        {#each micDevices as d (d.deviceId)}
          <option value={d.deviceId}>{d.label || 'Microphone'}</option>
        {/each}
      </select>
      <button class="micRefresh" type="button" on:click={refreshMics} title="Refresh microphones" aria-label="Refresh microphones" disabled={isRecording}>
        ↻
      </button>
    </div>
  {/if}
  {#if devMode}
    <button class="dev-back" on:click={handleDevBack} title="Back (dev)">⟲ Back</button>
  {/if}
</div>

{#if isRecording}
  <canvas bind:this={waveCanvas} width="300" height="48" class="wave"></canvas>
{/if}

{#if evaluating && !isRecording}
  <div class="processing-status" role="status" aria-live="polite">
    <span class="processing-dot"></span>
    <span class="processing-dot"></span>
    <span class="processing-dot"></span>
    <span class="processing-text">Processing your response...</span>
  </div>
{/if}

<style>
  .controls {
    margin-bottom: 20px;
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .record-button {
    background: #f97316;
    border: none;
    border-radius: 50%;
    width: 68px;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .record-button:is(:hover, :focus) {
    transform: scale(1.05);
    box-shadow: 0 8px 18px rgba(249, 115, 22, 0.4);
  }

  .record-button.isRecording {
    background: #ef4444;
    animation: pulse-recording 1.5s ease-in-out infinite;
  }

  @keyframes pulse-recording {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
    }
    50% {
      transform: scale(1.08);
      box-shadow: 0 0 20px 8px rgba(239, 68, 68, 0.25);
    }
  }

  .record-button.isEvaluating {
    background: #f59e0b;
    cursor: wait;
    animation: pulse-processing 1s ease-in-out infinite;
  }

  .record-button:disabled {
    cursor: wait;
  }

  @keyframes pulse-processing {
    0%, 100% {
      transform: scale(1);
      box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.4);
    }
    50% {
      transform: scale(1.05);
      box-shadow: 0 0 24px 12px rgba(245, 158, 11, 0.3);
    }
  }

  .dev-back {
    background: #111827;
    color: white;
    border: none;
    padding: 10px 14px;
    border-radius: 8px;
    cursor: pointer;
  }

  .mic {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    padding: 8px 10px;
    border-radius: 12px;
  }

  .micLabel {
    font-weight: 800;
    color: #374151;
    font-size: 0.9rem;
  }

  .micSelect {
    border: 1px solid #d1d5db;
    border-radius: 10px;
    padding: 6px 8px;
    background: #fff;
    color: #111827;
    font-weight: 700;
    min-width: 220px;
    max-width: min(420px, 70vw);
  }

  .micRefresh {
    border: 1px solid #d1d5db;
    background: #fff;
    color: #111827;
    border-radius: 10px;
    padding: 6px 10px;
    cursor: pointer;
    font-weight: 900;
  }

  .micRefresh:disabled,
  .micSelect:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .wave {
    width: 100%;
    max-width: 400px;
    height: 48px;
    border: 2px solid #f97316;
    border-radius: 8px;
    margin-bottom: 10px;
    background: linear-gradient(180deg, #fff 0%, #fef3e8 100%);
    box-shadow: 0 2px 8px rgba(249, 115, 22, 0.15);
  }

  .processing-status {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 10px 16px;
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(245, 158, 11, 0.2);
  }

  .processing-dot {
    width: 8px;
    height: 8px;
    background: #f59e0b;
    border-radius: 50%;
    animation: bounce-dot 1.4s ease-in-out infinite;
  }

  .processing-dot:nth-child(1) {
    animation-delay: 0s;
  }
  .processing-dot:nth-child(2) {
    animation-delay: 0.2s;
  }
  .processing-dot:nth-child(3) {
    animation-delay: 0.4s;
  }

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

  .processing-text {
    font-weight: 600;
    color: #92400e;
    font-size: 0.95rem;
    margin-left: 4px;
  }
</style>
