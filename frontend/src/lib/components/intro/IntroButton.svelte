<script>
  import { fade, scale } from 'svelte/transition';
  import { createEventDispatcher } from 'svelte';

  export let variant = 'continue';  // 'continue' | 'frozen' | 'choice' | 'start' | 'release'
  export let delay = 200;

  const dispatch = createEventDispatcher();
</script>

{#if variant === 'release'}
  <button class="release-btn" on:click={() => dispatch('click')} in:scale={{ delay }}>
    <span class="release-icon">⏯</span>
    <slot>RELEASE TIME & SPEAK</slot>
  </button>
{:else}
  <button
    class="btn"
    class:continue={variant === 'continue'}
    class:frozen={variant === 'frozen'}
    class:choice={variant === 'choice'}
    class:start={variant === 'start'}
    on:click={() => dispatch('click')}
    in:fade={{ delay }}
  >
    <slot />
  </button>
{/if}

<style>
  .btn {
    padding: 14px 28px;
    border-radius: 14px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .btn.continue {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
  }

  .btn.continue:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 28px rgba(99, 102, 241, 0.5);
  }

  .btn.frozen {
    background: linear-gradient(135deg, #8b5cf6, #a855f7);
    color: white;
    box-shadow: 0 4px 20px rgba(139, 92, 246, 0.4);
  }

  .btn.frozen:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 28px rgba(139, 92, 246, 0.5);
  }

  .btn.choice {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
  }

  .btn.start {
    background: linear-gradient(135deg, #f97316, #ea580c);
    color: white;
    padding: 18px 36px;
    font-size: 1.1rem;
    box-shadow: 0 4px 20px rgba(249, 115, 22, 0.4);
  }

  .btn.start:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 28px rgba(249, 115, 22, 0.5);
  }

  .release-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 24px 48px;
    background: linear-gradient(135deg, #8b5cf6, #6366f1);
    border: none;
    border-radius: 20px;
    color: white;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
    box-shadow: 0 0 40px rgba(139, 92, 246, 0.5);
    animation: pulse-release 2s ease-in-out infinite;
  }

  @keyframes pulse-release {
    0%, 100% { box-shadow: 0 0 40px rgba(139, 92, 246, 0.5); }
    50% { box-shadow: 0 0 60px rgba(139, 92, 246, 0.8); }
  }

  .release-icon {
    font-size: 2rem;
  }
</style>
