<script>
  export let speakerEmoji = '';
  export let dialogueTarget = '';
  export let dialogueNative = '';
  export let visible = true;
</script>

{#if visible && (dialogueTarget || dialogueNative)}
  <div class="dialogue-box">
    <div class="dialogue-content">
      {#if speakerEmoji}
        <span class="speaker-emoji">{speakerEmoji}</span>
      {/if}
      <div class="dialogue-text">
        {#if dialogueTarget}
          <p class="target-text">{dialogueTarget}</p>
        {/if}
        {#if dialogueNative}
          <p class="native-text">{dialogueNative}</p>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .dialogue-box {
    position: relative;
    width: 100%;
    max-width: 520px;
    margin: 0 auto;
  }

  .dialogue-content {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 14px 18px;
    box-shadow:
      0 4px 20px rgba(0, 0, 0, 0.15),
      0 0 0 1px rgba(255, 255, 255, 0.1);
  }

  .speaker-emoji {
    font-size: 1.8rem;
    line-height: 1;
    flex-shrink: 0;
  }

  .dialogue-text {
    flex: 1;
    min-width: 0;
  }

  .target-text {
    margin: 0;
    font-size: 1.35rem;
    font-weight: 600;
    color: #0f172a;
    line-height: 1.4;
    word-wrap: break-word;
  }

  .native-text {
    margin: 4px 0 0;
    font-size: 0.95rem;
    color: #64748b;
    font-style: italic;
    line-height: 1.4;
  }
</style>
