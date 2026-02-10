<script>
  import { onMount } from 'svelte';
  import { fade, fly } from 'svelte/transition';

  export let message = '';
  export let styleGained = '';
  export let sentiment = 'neutral'; // 'positive', 'neutral', 'negative'
  export let duration = 3000;
  export let onDismiss = () => {};

  let visible = true;

  $: sentimentClass = sentiment === 'positive' ? 'positive' : sentiment === 'negative' ? 'negative' : 'neutral';

  const styleEmojis = {
    polite: '🎩',
    direct: '🎯',
    tricky: '🎭',
    charming: '✨',
    bold: '💪',
    humble: '🙏',
    evasive: '💨',
    respectful: '🙇',
    casual: '👋',
    rude: '😤'
  };

  $: styleEmoji = styleGained ? (styleEmojis[styleGained] || '🏅') : '';

  onMount(() => {
    const timer = setTimeout(() => {
      visible = false;
      setTimeout(onDismiss, 300);
    }, duration);
    return () => clearTimeout(timer);
  });
</script>

{#if visible}
  <div
    class="social-toast {sentimentClass}"
    in:fly={{ y: -20, duration: 300 }}
    out:fade={{ duration: 200 }}
    role="status"
    aria-live="polite"
  >
    <div class="toast-content">
      <span class="sentiment-icon">
        {#if sentiment === 'positive'}
          😊
        {:else if sentiment === 'negative'}
          😕
        {:else}
          🤔
        {/if}
      </span>
      <span class="message">{message}</span>
    </div>
    {#if styleGained}
      <div class="style-gained">
        <span class="style-emoji">{styleEmoji}</span>
        <span class="style-label">+{styleGained}</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .social-toast {
    position: fixed;
    top: 80px;
    left: 50%;
    transform: translateX(-50%);
    min-width: 280px;
    max-width: 400px;
    padding: 12px 20px;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    z-index: 1000;
    display: flex;
    flex-direction: column;
    gap: 6px;
    backdrop-filter: blur(8px);
    font-family: system-ui, -apple-system, sans-serif;
  }

  .social-toast.positive {
    background: linear-gradient(135deg, rgba(236, 253, 245, 0.95), rgba(209, 250, 229, 0.95));
    border: 1px solid rgba(52, 211, 153, 0.4);
    color: #065f46;
  }

  .social-toast.neutral {
    background: linear-gradient(135deg, rgba(249, 250, 251, 0.95), rgba(229, 231, 235, 0.95));
    border: 1px solid rgba(156, 163, 175, 0.4);
    color: #374151;
  }

  .social-toast.negative {
    background: linear-gradient(135deg, rgba(254, 242, 242, 0.95), rgba(254, 226, 226, 0.95));
    border: 1px solid rgba(252, 165, 165, 0.4);
    color: #991b1b;
  }

  .toast-content {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .sentiment-icon {
    font-size: 1.3rem;
    line-height: 1;
  }

  .message {
    font-size: 0.95rem;
    font-weight: 500;
    line-height: 1.4;
  }

  .style-gained {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-left: 32px;
    font-size: 0.85rem;
    opacity: 0.8;
  }

  .style-emoji {
    font-size: 0.9rem;
  }

  .style-label {
    font-weight: 600;
    text-transform: capitalize;
    letter-spacing: 0.02em;
  }

  .social-toast.positive .style-label {
    color: #059669;
  }

  .social-toast.neutral .style-label {
    color: #6b7280;
  }

  .social-toast.negative .style-label {
    color: #dc2626;
  }
</style>
