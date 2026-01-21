<script>
  import { createEventDispatcher } from 'svelte';

  export let isRecording = false;
  export let devMode = false;
  export let mode = 'beginner';
  export let micDevices = [];
  export let micDeviceId = '';

  const dispatch = createEventDispatcher();
  export let waveCanvas;

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
    on:click={toggleRecording}
    aria-label={ariaLabel}
    title={titleText}
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
  <canvas bind:this={waveCanvas} width="300" height="40" class="wave"></canvas>
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
    height: 40px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    margin-bottom: 10px;
  }
</style>
