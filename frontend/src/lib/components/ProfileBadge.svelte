<script lang="ts">
  import { displayTitle, rankProgress, currentStreak, scenariosCompleted } from '$lib/profileStore';

  export let compact = false;

  $: title = $displayTitle;
  $: progress = $rankProgress;
  $: streak = $currentStreak;
  $: completed = $scenariosCompleted;
</script>

{#if compact}
  <div class="profile-badge compact" title="{title} ({completed} scenarios)">
    <span class="badge-icon">🎭</span>
    <span class="badge-text">{title}</span>
    {#if streak > 1}
      <span class="streak" title="{streak} day streak">🔥{streak}</span>
    {/if}
  </div>
{:else}
  <div class="profile-badge full">
    <div class="badge-header">
      <span class="badge-icon">🎭</span>
      <span class="badge-title">{title}</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" style="width: {progress}%"></div>
    </div>
    <div class="badge-stats">
      <span class="stat" title="Scenarios completed">📚 {completed}</span>
      {#if streak > 0}
        <span class="stat streak" title="{streak} day streak">🔥 {streak}</span>
      {/if}
    </div>
  </div>
{/if}

<style>
  .profile-badge {
    font-family: system-ui, -apple-system, sans-serif;
  }

  .profile-badge.compact {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: linear-gradient(135deg, #f3e8ff, #e9d5ff);
    border: 1px solid rgba(168, 85, 247, 0.3);
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6b21a8;
    box-shadow: 0 2px 8px rgba(168, 85, 247, 0.15);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .profile-badge.compact:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(168, 85, 247, 0.2);
  }

  .badge-icon {
    font-size: 1rem;
    line-height: 1;
  }

  .badge-text {
    white-space: nowrap;
  }

  .streak {
    font-size: 0.8rem;
    opacity: 0.9;
  }

  .profile-badge.full {
    background: linear-gradient(135deg, #faf5ff, #f3e8ff);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-radius: 16px;
    padding: 16px;
    min-width: 200px;
    box-shadow: 0 4px 16px rgba(168, 85, 247, 0.1);
  }

  .badge-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .badge-header .badge-icon {
    font-size: 1.3rem;
  }

  .badge-title {
    font-size: 1rem;
    font-weight: 700;
    color: #6b21a8;
    letter-spacing: -0.01em;
  }

  .progress-bar {
    height: 6px;
    background: rgba(168, 85, 247, 0.15);
    border-radius: 999px;
    overflow: hidden;
    margin-bottom: 10px;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #a855f7, #7c3aed);
    border-radius: 999px;
    transition: width 0.4s ease;
  }

  .badge-stats {
    display: flex;
    gap: 16px;
    font-size: 0.85rem;
    color: #7c3aed;
  }

  .stat {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .stat.streak {
    color: #ea580c;
  }
</style>
