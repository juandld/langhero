<script>
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();
</script>

<button class="tap-overlay" on:click={() => dispatch('tap')}>
  <span class="tap-hint">Tap to continue</span>
</button>

<style>
  .tap-overlay {
    position: absolute;
    inset: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: flex-end;
    justify-content: center;
    padding-bottom: 40px;
  }

  .tap-hint {
    font-size: 0.85rem;
    color: rgba(255,255,255,0.4);
    animation: pulse-hint 2s ease-in-out infinite;
  }

  @keyframes pulse-hint {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.7; }
  }
</style>
