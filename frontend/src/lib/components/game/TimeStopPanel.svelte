<script>
  import { createEventDispatcher } from 'svelte';

  export let options = [];
  export let selectedOption = null;
  export let previewedOption = null;
  export let isPreviewPlaying = false;
  export let visible = true;
  export let draftText = '';
  export let bimboHint = null;
  export let askingBimbo = false;

  const dispatch = createEventDispatcher();

  function previewOption(option) {
    dispatch('previewOption', option);
  }

  function handleDraftInput(e) {
    dispatch('draftChange', e.target.value);
  }

  function handleAskBimbo() {
    const text = (draftText || '').trim();
    if (!text || askingBimbo) return;
    dispatch('askBimbo', text);
  }

  function handlePlayTranslation() {
    if (!bimboHint?.translation) return;
    dispatch('playBimboTranslation', {
      target: bimboHint.translation,
      pronunciation: bimboHint.pronunciation,
      native: bimboHint.playerText,
    });
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAskBimbo();
    }
  }

  $: previewTarget = previewedOption?.example?.target;
  $: canAsk = (draftText || '').trim().length > 0 && !askingBimbo;
</script>

{#if visible}
  <div class="time-stop-panel">
    <div class="time-indicator">
      <span class="time-icon">⏸</span>
      <span class="time-text">TIME STOPPED - How will you respond?</span>
    </div>

    <!-- Draft input with Ask button -->
    <div class="draft-area">
      <div class="draft-row">
        <input
          type="text"
          class="draft-input"
          placeholder="Tell Bimbo what you want to say..."
          value={draftText}
          on:input={handleDraftInput}
          on:keydown={handleKeydown}
        />
        <button
          class="ask-btn"
          class:ask-btn--loading={askingBimbo}
          disabled={!canAsk}
          on:click={handleAskBimbo}
        >
          {#if askingBimbo}
            <span class="ask-spinner"></span>
          {:else}
            Ask
          {/if}
        </button>
      </div>
    </div>

    <!-- Bimbo hint -->
    {#if bimboHint}
      <div class="bimbo-hint">
        <span class="bimbo-hint-label">Bimbo:</span>
        <span class="bimbo-hint-text">{bimboHint.bimboSays}</span>
      </div>

      <!-- Pronunciation card for translation -->
      {#if bimboHint.translation}
        <button class="translation-card" on:click={handlePlayTranslation}>
          <div class="translation-target">{bimboHint.translation}</div>
          {#if bimboHint.pronunciation}
            <div class="translation-pron">{bimboHint.pronunciation}</div>
          {/if}
          {#if bimboHint.playerText}
            <div class="translation-native">"{bimboHint.playerText}"</div>
          {/if}
          <span class="translation-speaker" aria-label="Tap to hear">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
              <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
            </svg>
          </span>
        </button>
      {/if}
    {/if}

    {#if options.length > 0}
      <div class="suggestions-label">Suggestions — tap to hear</div>
      <div class="choices-grid">
        {#each options as opt, i}
          {#if opt.examples && opt.examples.length > 0}
            {@const isActive = previewTarget === opt.examples[0].target}
            {@const isBimboMatch = bimboHint && bimboHint.matchedIndex === i && bimboHint.confidence !== 'none'}
            <button
              class="choice-btn"
              class:choice-btn--active={isActive}
              class:choice-btn--bimbo-match={isBimboMatch}
              on:click={() => previewOption({ next_scenario: opt.next_scenario, example: opt.examples[0] })}
            >
              <div class="choice-target">{opt.examples[0].target || opt.examples[0].native}</div>
              {#if opt.examples[0].pronunciation}
                <div class="choice-pron">{opt.examples[0].pronunciation}</div>
              {/if}
              <div class="choice-native">{opt.examples[0].native || ''}</div>
              <span class="choice-indicator" aria-label="Tap to hear">
                {#if isActive && isPreviewPlaying}
                  <span class="waveform-bars">
                    <span class="bar"></span>
                    <span class="bar"></span>
                    <span class="bar"></span>
                    <span class="bar"></span>
                  </span>
                {:else}
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                    <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02z"/>
                  </svg>
                {/if}
              </span>
            </button>
          {/if}
        {/each}
      </div>
    {:else}
      <div class="no-choices">
        <span class="no-choices-text">Speak freely in the target language</span>
      </div>
    {/if}
  </div>
{/if}

<style>
  .time-stop-panel {
    width: 100%;
    max-width: 520px;
    margin: 0 auto;
  }

  .time-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 16px;
    margin-bottom: 12px;
    background: rgba(99, 102, 241, 0.15);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 20px;
    color: #a5b4fc;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    animation: pulse-indicator 2s ease-in-out infinite;
  }

  @keyframes pulse-indicator {
    0%, 100% { opacity: 0.8; }
    50% { opacity: 1; }
  }

  .time-icon {
    font-size: 1rem;
  }

  .draft-area {
    margin-bottom: 12px;
  }

  .draft-row {
    display: flex;
    gap: 8px;
  }

  .draft-input {
    flex: 1;
    padding: 10px 14px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    color: #f1f5f9;
    font-size: 1rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s, background 0.15s;
    box-sizing: border-box;
    min-width: 0;
  }

  .draft-input::placeholder {
    color: rgba(255, 255, 255, 0.3);
  }

  .draft-input:focus {
    border-color: #818cf8;
    background: rgba(255, 255, 255, 0.1);
  }

  .ask-btn {
    padding: 10px 18px;
    background: rgba(168, 85, 247, 0.25);
    border: 1px solid rgba(168, 85, 247, 0.4);
    border-radius: 10px;
    color: #c4b5fd;
    font-size: 0.9rem;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, opacity 0.15s;
    white-space: nowrap;
    min-width: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .ask-btn:hover:not(:disabled) {
    background: rgba(168, 85, 247, 0.4);
    border-color: rgba(168, 85, 247, 0.6);
  }

  .ask-btn:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .ask-btn--loading {
    pointer-events: none;
  }

  .ask-spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(196, 181, 253, 0.3);
    border-top-color: #c4b5fd;
    border-radius: 50%;
    animation: ask-spin 0.6s linear infinite;
  }

  @keyframes ask-spin {
    to { transform: rotate(360deg); }
  }

  /* Bimbo hint bar */
  .bimbo-hint {
    margin-bottom: 12px;
    padding: 10px 14px;
    background: rgba(168, 85, 247, 0.12);
    border: 1px solid rgba(168, 85, 247, 0.3);
    border-radius: 10px;
    font-size: 0.9rem;
    line-height: 1.4;
    color: #e9d5ff;
  }

  .bimbo-hint-label {
    font-weight: 700;
    color: #c084fc;
    margin-right: 6px;
  }

  .bimbo-hint-text {
    color: #d8b4fe;
  }

  /* Translation pronunciation card */
  .translation-card {
    position: relative;
    width: 100%;
    margin-bottom: 12px;
    padding: 14px 44px 14px 16px;
    background: rgba(168, 85, 247, 0.1);
    border: 1px solid rgba(168, 85, 247, 0.35);
    border-radius: 12px;
    text-align: left;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
    font-family: inherit;
    color: inherit;
  }

  .translation-card:hover {
    background: rgba(168, 85, 247, 0.18);
    border-color: rgba(168, 85, 247, 0.5);
    box-shadow: 0 2px 16px rgba(168, 85, 247, 0.2);
  }

  .translation-target {
    font-size: 1.2rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 2px;
  }

  .translation-pron {
    font-size: 0.85rem;
    color: #c4b5fd;
    font-style: italic;
    margin-bottom: 4px;
  }

  .translation-native {
    font-size: 0.8rem;
    color: #94a3b8;
  }

  .translation-speaker {
    position: absolute;
    top: 50%;
    right: 14px;
    transform: translateY(-50%);
    color: rgba(196, 181, 253, 0.5);
    display: flex;
    align-items: center;
    transition: color 0.15s;
  }

  .translation-card:hover .translation-speaker {
    color: #c4b5fd;
  }

  .suggestions-label {
    font-size: 0.7rem;
    color: #52525b;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 8px;
  }

  .choices-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 10px;
  }

  .choice-btn {
    position: relative;
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(12px);
    border: 2px solid rgba(255, 255, 255, 0.15);
    border-radius: 14px;
    padding: 14px 16px;
    text-align: left;
    cursor: pointer;
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.2);
  }

  .choice-btn:hover {
    transform: translateY(-2px);
    border-color: #818cf8;
    background: rgba(255, 255, 255, 0.12);
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25);
  }

  .choice-btn--active {
    border-color: #818cf8;
    box-shadow: 0 4px 20px rgba(99, 102, 241, 0.3);
    background: rgba(99, 102, 241, 0.2);
  }

  /* Bimbo match highlight */
  .choice-btn--bimbo-match {
    border-color: #a855f7;
    box-shadow: 0 0 20px rgba(168, 85, 247, 0.4);
    background: rgba(168, 85, 247, 0.15);
    animation: bimbo-pulse 0.8s ease-in-out 2;
  }

  @keyframes bimbo-pulse {
    0%, 100% { box-shadow: 0 0 20px rgba(168, 85, 247, 0.4); }
    50% { box-shadow: 0 0 35px rgba(168, 85, 247, 0.7); }
  }

  .choice-target {
    font-size: 1.1rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 2px;
    padding-right: 28px;
  }

  .choice-pron {
    font-size: 0.8rem;
    color: #a5b4fc;
    font-style: italic;
    margin-bottom: 4px;
  }

  .choice-native {
    font-size: 0.85rem;
    color: #94a3b8;
  }

  .choice-indicator {
    position: absolute;
    top: 10px;
    right: 10px;
    color: rgba(255, 255, 255, 0.4);
    display: flex;
    align-items: center;
  }

  .choice-btn--active .choice-indicator {
    color: #a5b4fc;
  }

  .waveform-bars {
    display: flex;
    align-items: flex-end;
    gap: 2px;
    height: 16px;
  }

  .waveform-bars .bar {
    width: 3px;
    background: #a5b4fc;
    border-radius: 1px;
    animation: waveform-bounce 0.8s ease-in-out infinite;
  }

  .waveform-bars .bar:nth-child(1) { height: 40%; animation-delay: 0s; }
  .waveform-bars .bar:nth-child(2) { height: 70%; animation-delay: 0.15s; }
  .waveform-bars .bar:nth-child(3) { height: 50%; animation-delay: 0.3s; }
  .waveform-bars .bar:nth-child(4) { height: 80%; animation-delay: 0.45s; }

  @keyframes waveform-bounce {
    0%, 100% { transform: scaleY(0.4); }
    50% { transform: scaleY(1); }
  }

  .no-choices {
    text-align: center;
    padding: 16px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    border: 1px dashed rgba(255, 255, 255, 0.2);
  }

  .no-choices-text {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.95rem;
  }
</style>
