<script>
  export let lives = 0;
  export let livesTotal = 0;
  export let score = 0;
  export let penaltyMessage = '';
</script>

<div class="status-strip">
  <div class="status-item">Lives: {lives}/{livesTotal}</div>
  <div class="status-item">Score: {score}</div>
</div>
{#if penaltyMessage}
  <div class="penalty-banner" role="alert">{penaltyMessage}</div>
{/if}

<style>
  .status-strip {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin: 8px 0;
    font-weight: 600;
    color: #374151;
  }

  .status-item {
    background: #f3f4f6;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.9rem;
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
