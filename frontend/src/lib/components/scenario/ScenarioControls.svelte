<script>
  import { createEventDispatcher } from 'svelte';

  export let isRecording = false;
  export let devMode = false;

  const dispatch = createEventDispatcher();
  export let waveCanvas;

  const toggleRecording = () => dispatch('toggle');
  const handleDevBack = () => dispatch('devBack');
</script>

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

  .wave {
    width: 100%;
    max-width: 400px;
    height: 40px;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    margin-bottom: 10px;
  }
</style>
