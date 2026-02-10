<script>
  import { fly } from 'svelte/transition';

  export let line = null;  // { speaker, text, sub? }
  export let variant = 'default';  // 'default' | 'bimbo' | 'centered' | 'small'
</script>

{#if line}
  <div
    class="dialogue-box"
    class:player={line.speaker === 'player'}
    class:samurai={line.speaker === 'samurai'}
    class:narration={line.speaker === 'narration'}
    class:bimbo-glow={variant === 'bimbo'}
    class:centered={variant === 'centered'}
    class:small={variant === 'small'}
  >
    <div in:fly={{ y: 10, duration: 200 }}>
      <p class="dialogue-text">{line.text}</p>
      {#if line.sub}
        <p class="dialogue-sub">{line.sub}</p>
      {/if}
    </div>
  </div>
{/if}

<style>
  .dialogue-box {
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(8px);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 24px;
    border: 1px solid rgba(255,255,255,0.1);
    width: 100%;
    max-width: 400px;
  }

  .dialogue-box.player {
    background: rgba(99, 102, 241, 0.2);
    border-color: rgba(99, 102, 241, 0.3);
  }

  .dialogue-box.samurai {
    background: rgba(220, 38, 38, 0.2);
    border-color: rgba(220, 38, 38, 0.3);
  }

  .dialogue-box.narration {
    background: transparent;
    border-color: transparent;
    text-align: center;
    font-style: italic;
  }

  .dialogue-box.bimbo-glow {
    background: rgba(99, 102, 241, 0.15);
    border-color: rgba(139, 92, 246, 0.4);
    box-shadow: 0 0 30px rgba(139, 92, 246, 0.2);
  }

  .dialogue-box.centered {
    text-align: center;
  }

  .dialogue-box.small {
    padding: 14px 18px;
    margin-bottom: 16px;
  }

  .dialogue-text {
    margin: 0;
    font-size: 1.15rem;
    line-height: 1.6;
    color: #e2e8f0;
  }

  .dialogue-sub {
    margin: 8px 0 0;
    font-size: 0.9rem;
    color: #94a3b8;
  }
</style>
