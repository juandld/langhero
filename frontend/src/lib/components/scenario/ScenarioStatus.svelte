<script>
  export let lives = 0;
  export let livesTotal = 0;
  export let score = 0;
  export let penaltyMessage = '';
  export let confidence = null;
  export let matchType = '';
  export let mode = 'beginner';

  $: normalizedMode = (mode || '').toLowerCase() === 'advanced' ? 'advanced' : 'beginner';
  $: modeLabel = normalizedMode === 'advanced' ? 'Live • Streaming' : 'Time Stop • Planning';
  $: confValue = Number(confidence);
  $: hasConfidence = Number.isFinite(confValue);
  $: confPct = hasConfidence ? Math.round(Math.max(0, Math.min(1, confValue)) * 100) : null;
</script>

<div class="status-strip">
  <div class="mode-pill" data-mode={normalizedMode}>{modeLabel}</div>
  <div class="status-item">Lives: {lives}/{livesTotal}</div>
  <div class="status-item">Score: {score}</div>
  {#if hasConfidence}
    <div class="status-item confidence" title={matchType ? `match: ${matchType}` : 'match confidence'}>
      <span>Confidence: {confPct}%</span>
      <span class="bar" aria-hidden="true"><span class="fill" style={`width:${confPct}%`}></span></span>
    </div>
  {/if}
</div>
{#if penaltyMessage}
  <div class="penalty-banner" role="alert">{penaltyMessage}</div>
{/if}

<style>
  .status-strip {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin: 8px 0;
    font-weight: 600;
    color: #374151;
    flex-wrap: wrap;
  }

  .status-item {
    background: #f3f4f6;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.9rem;
    display: inline-flex;
    align-items: center;
    gap: 8px;
  }

  .confidence .bar {
    width: 82px;
    height: 8px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.12);
    overflow: hidden;
  }

  .confidence .fill {
    display: block;
    height: 100%;
    background: linear-gradient(90deg, rgba(239, 68, 68, 0.9), rgba(245, 158, 11, 0.9), rgba(34, 197, 94, 0.9));
  }

  .mode-pill {
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    background: #e0e7ff;
    color: #312e81;
  }

  .mode-pill[data-mode='advanced'] {
    background: #dbeafe;
    color: #1d4ed8;
  }

  .penalty-banner {
    margin: 4px 0 12px;
    padding: 8px 12px;
    background: #fee2e2;
    color: #b91c1c;
    border-radius: 12px;
    font-size: 0.9rem;
  }
</style>
