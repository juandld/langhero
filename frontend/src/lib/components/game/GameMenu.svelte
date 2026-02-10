<script>
  import { createEventDispatcher } from 'svelte';
  import { profileStore } from '$lib/profileStore';

  export let visible = false;
  export let judgeFocus = 0;
  export let languageOverride = '';
  export let micDevices = [];
  export let micDeviceId = '';
  export let scenariosCompleted = 0;

  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }

  function handleBackdropClick(e) {
    if (e.target === e.currentTarget) {
      close();
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      close();
    }
  }

  function updateJudgeFocus(e) {
    const val = parseFloat(e.currentTarget.value);
    if (Number.isFinite(val)) {
      dispatch('updateJudgeFocus', Math.min(1, Math.max(0, val)));
    }
  }

  function updateLanguage(e) {
    dispatch('updateLanguage', e.currentTarget.value);
  }

  function updateMic(e) {
    dispatch('updateMic', e.currentTarget.value);
  }

  function exitToMenu() {
    dispatch('exit');
  }

  function replayTutorial() {
    dispatch('replayTutorial');
    close();
  }

  $: profile = $profileStore;
  $: rankProgress = profile?.rankProgress || 0;
  $: currentRank = profile?.currentRank || 'Novice';

  $: judgeLabel = judgeFocus >= 0.66 ? 'Story-first' : (judgeFocus <= 0.34 ? 'Learning-first' : 'Balanced');

  const languageOptions = [
    { value: '', label: 'Auto' },
    { value: 'Japanese', label: 'Japanese' },
    { value: 'English', label: 'English' },
    { value: 'Spanish', label: 'Spanish' },
  ];
</script>

<svelte:window on:keydown={handleKeydown}/>

{#if visible}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="menu-backdrop" on:click={handleBackdropClick}>
    <div class="menu-panel" role="dialog" aria-label="Game menu">
      <header class="menu-header">
        <button class="back-btn" on:click={close} aria-label="Close menu">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
          Back
        </button>
        <h2 class="menu-title">Game Menu</h2>
      </header>

      <section class="profile-card">
        <div class="rank-badge">
          <span class="rank-icon">🎭</span>
          <span class="rank-name">{currentRank}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" style="width: {rankProgress * 100}%"></div>
        </div>
        <div class="progress-label">{Math.round(rankProgress * 100)}% to next rank</div>
        <div class="scenarios-count">
          <span class="count-icon">📚</span>
          <span class="count-text">{scenariosCompleted} scenarios completed</span>
        </div>
      </section>

      <hr class="divider"/>

      <section class="settings-section">
        <h3 class="section-title">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
            <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
          </svg>
          Settings
        </h3>

        <div class="setting-item">
          <label class="setting-label" for="language-select">Language</label>
          <select id="language-select" class="setting-select" value={languageOverride} on:change={updateLanguage}>
            {#each languageOptions as opt}
              <option value={opt.value}>{opt.label}</option>
            {/each}
          </select>
        </div>

        <div class="setting-item">
          <label class="setting-label">
            Difficulty
            <span class="setting-badge">{judgeLabel}</span>
          </label>
          <div class="slider-row">
            <span class="slider-end">Learning</span>
            <input
              type="range"
              class="setting-slider"
              min="0"
              max="1"
              step="0.05"
              value={judgeFocus}
              on:input={updateJudgeFocus}
            />
            <span class="slider-end">Story</span>
          </div>
        </div>

        <div class="setting-item">
          <label class="setting-label" for="mic-select">Microphone</label>
          <select id="mic-select" class="setting-select" value={micDeviceId} on:change={updateMic}>
            <option value="">Default</option>
            {#each micDevices as d}
              <option value={d.deviceId}>{d.label || 'Microphone'}</option>
            {/each}
          </select>
        </div>
      </section>

      <hr class="divider"/>

      <section class="actions-section">
        <button class="action-btn tutorial" on:click={replayTutorial}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
          </svg>
          Replay Tutorial
        </button>

        <button class="action-btn exit" on:click={exitToMenu}>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/>
          </svg>
          Exit to Menu
        </button>
      </section>
    </div>
  </div>
{/if}

<style>
  .menu-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
    z-index: 1000;
    display: flex;
    justify-content: flex-start;
    animation: fade-in 0.2s ease;
  }

  @keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .menu-panel {
    width: 100%;
    max-width: 360px;
    height: 100%;
    background: #0f172a;
    color: #e2e8f0;
    overflow-y: auto;
    animation: slide-in 0.25s ease;
    padding: 20px;
  }

  @keyframes slide-in {
    from { transform: translateX(-100%); }
    to { transform: translateX(0); }
  }

  .menu-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    border-radius: 10px;
    padding: 8px 12px;
    color: #e2e8f0;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .back-btn:hover {
    background: rgba(255, 255, 255, 0.15);
  }

  .menu-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin: 0;
    color: #f8fafc;
  }

  .profile-card {
    background: linear-gradient(135deg, #1e293b, #334155);
    border-radius: 16px;
    padding: 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .rank-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
  }

  .rank-icon {
    font-size: 1.5rem;
  }

  .rank-name {
    font-size: 1.2rem;
    font-weight: 700;
    color: #f8fafc;
  }

  .progress-bar {
    height: 8px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    overflow: hidden;
    margin-bottom: 6px;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-label {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-bottom: 10px;
  }

  .scenarios-count {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
    color: #cbd5e1;
  }

  .count-icon {
    font-size: 1rem;
  }

  .divider {
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin: 20px 0;
  }

  .settings-section {
    margin-bottom: 16px;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.95rem;
    font-weight: 700;
    color: #f8fafc;
    margin: 0 0 14px;
  }

  .setting-item {
    margin-bottom: 14px;
  }

  .setting-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #cbd5e1;
    margin-bottom: 6px;
  }

  .setting-badge {
    font-size: 0.75rem;
    padding: 2px 8px;
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    border-radius: 20px;
    font-weight: 700;
  }

  .setting-select {
    width: 100%;
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    padding: 10px 12px;
    color: #f8fafc;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .setting-select:focus {
    outline: none;
    border-color: #6366f1;
  }

  .slider-row {
    display: grid;
    grid-template-columns: 60px 1fr 50px;
    gap: 8px;
    align-items: center;
  }

  .slider-end {
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .setting-slider {
    width: 100%;
    accent-color: #6366f1;
  }

  .actions-section {
    margin-top: 16px;
  }

  .action-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 12px 16px;
    border: none;
    border-radius: 12px;
    font-size: 0.95rem;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s ease, transform 0.1s ease;
  }

  .action-btn.tutorial {
    background: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    border: 1px solid rgba(99, 102, 241, 0.3);
    margin-bottom: 10px;
  }

  .action-btn.tutorial:hover {
    background: rgba(99, 102, 241, 0.3);
  }

  .action-btn.exit {
    background: rgba(239, 68, 68, 0.2);
    color: #fca5a5;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }

  .action-btn.exit:hover {
    background: rgba(239, 68, 68, 0.3);
  }
</style>
