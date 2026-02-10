<script>
  import { createEventDispatcher } from 'svelte';

  export let japanese = '私は...';
  export let romaji = 'Watashi wa...';
  export let english = '"I am..."';
  export let hasListened = false;
  export let hasPracticed = false;
  export let isRecording = false;

  const dispatch = createEventDispatcher();
</script>

<div class="phrase-card" class:listened={hasListened}>
  <div class="phrase-japanese">{japanese}</div>
  <div class="phrase-romaji">{romaji}</div>
  <div class="phrase-english">{english}</div>

  {#if !hasListened}
    <button class="action-btn listen" on:click={() => dispatch('listen')}>
      <span class="icon">🔊</span>
      <span>Tap to listen</span>
    </button>
  {:else if !hasPracticed}
    <button
      class="action-btn practice"
      class:recording={isRecording}
      on:click={() => dispatch('practice')}
    >
      <span class="icon">{isRecording ? '⏹' : '🎤'}</span>
      <span>{isRecording ? 'Listening...' : 'Say it to me'}</span>
    </button>
  {:else}
    <div class="success-indicator">
      <span class="check">✓</span>
      <span>Got it!</span>
    </div>
  {/if}
</div>

<style>
  .phrase-card {
    background: rgba(255,255,255,0.95);
    border-radius: 16px;
    padding: 24px;
    text-align: center;
    width: 100%;
    max-width: 300px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    transition: all 0.3s ease;
  }

  .phrase-card.listened {
    border: 2px solid #8b5cf6;
  }

  .phrase-japanese {
    font-size: 2rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 8px;
  }

  .phrase-romaji {
    font-size: 1.1rem;
    color: #6366f1;
    margin-bottom: 4px;
  }

  .phrase-english {
    font-size: 0.9rem;
    color: #64748b;
    margin-bottom: 16px;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 14px;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .action-btn.listen {
    background: #6366f1;
    color: white;
  }

  .action-btn.listen:hover {
    background: #4f46e5;
  }

  .action-btn.practice {
    background: #f97316;
    color: white;
  }

  .action-btn.practice.recording {
    background: #ef4444;
    animation: pulse-record 1s ease-in-out infinite;
  }

  @keyframes pulse-record {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.02); }
  }

  .success-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: #10b981;
    font-weight: 600;
    font-size: 1.1rem;
  }

  .check {
    font-size: 1.5rem;
  }

  .icon {
    font-size: 1.2rem;
  }
</style>
