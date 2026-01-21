<script>
  import { createEventDispatcher } from 'svelte';

  export let requireRepeat = false;
  export let selectedOption = null;
  export let lastHeard = '';
  export let evaluating = false;
  export let lives = 0;
  export let localSuggestions = null;
  export let speakingSuggestions = null;
  export let myNativeText = '';
  export let translating = false;
  export let isNativeRecording = false;
  export let fallbackOptions = [];
  export let mode = 'beginner';
  export let judgeFocus = 0; // 0 = learning-first, 1 = story-first
  export let languageOverride = ''; // '' = auto, else language name

  const dispatch = createEventDispatcher();

  const handleSelectOption = (option) => {
    if (!option) return;
    dispatch('selectOption', option);
  };

  const handleRepeatPrompt = () => {
    dispatch('playPrompt');
  };

  const handleTranslate = () => {
    dispatch('translate');
  };

  const handleToggleNativeRecording = () => {
    dispatch('toggleNativeRecording');
  };

  $: normalizedMode = (mode || '').toLowerCase() === 'advanced' ? 'advanced' : 'beginner';
  $: isTimeStopMode = normalizedMode !== 'advanced';
  $: prepMessage = isTimeStopMode
    ? 'Time Stop tools — experiment safely here before you risk a rewind.'
    : 'Live mode tools — translator + make-your-own stay safe between live turns.';
  $: makeNoteText = isTimeStopMode
    ? 'Translates while time is frozen — no lives at risk.'
    : 'Translates without costing lives even while the live mic is active.';

  const clamp01 = (v) => {
    const num = Number(v);
    if (!Number.isFinite(num)) return 0;
    return Math.min(1, Math.max(0, num));
  };

  const handleJudgeInput = (event) => {
    judgeFocus = clamp01(event?.currentTarget?.value);
  };

  $: judgeFocus = clamp01(judgeFocus);
  $: judgePresetLabel = judgeFocus >= 0.66 ? 'Story-first' : (judgeFocus <= 0.34 ? 'Learning-first' : 'Balanced');
  $: judgeHint = judgeFocus >= 0.66
    ? 'More permissive: prioritize story progression.'
    : (judgeFocus <= 0.34 ? 'Stricter: prioritize target-language performance.' : 'Balanced: mix learning and story goals.');

  const normalizeLanguage = (v) => {
    const raw = String(v || '').trim();
    if (!raw) return '';
    const lowered = raw.toLowerCase();
    if (['auto', 'default', 'none'].includes(lowered)) return '';
    if (['ja', 'jp', 'japanese'].includes(lowered)) return 'Japanese';
    if (['en', 'eng', 'english'].includes(lowered)) return 'English';
    if (['es', 'spa', 'spanish', 'espanol', 'español'].includes(lowered)) return 'Spanish';
    return raw;
  };

  const handleLanguageChange = (event) => {
    languageOverride = normalizeLanguage(event?.currentTarget?.value);
  };

  $: languageOverride = normalizeLanguage(languageOverride);
</script>

<div class="options-block">
  <div class={`prep-banner ${isTimeStopMode ? 'time-stop' : 'live-mode'}`} role="note">
    {prepMessage}
  </div>
  <div class="judge-panel" role="group" aria-label="Judge focus">
    <div class="judge-header">
      <div class="judge-title">Judge focus</div>
      <div class="judge-pill">{judgePresetLabel}</div>
    </div>
    <div class="judge-row">
      <div class="judge-side">Learning</div>
      <input
        class="judge-slider"
        type="range"
        min="0"
        max="1"
        step="0.05"
        value={judgeFocus}
        on:input={handleJudgeInput}
      />
      <div class="judge-side">Story</div>
    </div>
    <div class="judge-hint">{judgeHint}</div>
  </div>
  <div class="language-panel" role="group" aria-label="Target language">
    <div class="language-header">
      <div class="language-title">Target language</div>
    </div>
    <select class="language-select" value={languageOverride} on:change={handleLanguageChange}>
      <option value="">Auto</option>
      <option value="English">English</option>
      <option value="Spanish">Spanish</option>
      <option value="Japanese">Japanese</option>
    </select>
  </div>
  {#if localSuggestions || speakingSuggestions}
    <h3 class="prompt-question">
      {requireRepeat
        ? 'Say this'
        : ((localSuggestions?.question || speakingSuggestions?.question) || 'What do you say?')}
    </h3>

    {#if requireRepeat && selectedOption}
      <div class="say-panel">
        {#if selectedOption.example?.native}
          <div class="line-native">{selectedOption.example.native}</div>
        {/if}
        <div class="line-target">{selectedOption.example?.target}</div>
        {#if selectedOption.example?.pronunciation}
          <div class="line-pron">{selectedOption.example.pronunciation}</div>
        {/if}
        <div class="lives">Lives: {lives}</div>
        <div class="say-actions">
          <button
            type="button"
            class="chip-advance"
            on:click={handleRepeatPrompt}
          >▶</button>
        </div>
        {#if lastHeard}
          <div class="heard">Heard: <em>{lastHeard}</em>{evaluating ? ' …' : ''}</div>
        {/if}
      </div>
    {/if}

    {#each (localSuggestions ? localSuggestions.options : speakingSuggestions.options) as opt, index}
      {#if opt.examples && opt.examples.length}
        <div class="chips" role="list">
          <div class="chip-group" role="group" aria-label="Example option">
            <button
              type="button"
              class="chip-advance"
              on:click={() =>
                handleSelectOption({
                  next_scenario: opt.next_scenario,
                  example: opt.examples[0]
                })
              }
            >
              <div class="line-native">▶ {opt.examples[0].native || opt.examples[0].target}</div>
              <div class="line-target">{opt.examples[0].target || opt.examples[0].native}</div>
              {#if opt.examples[0].pronunciation}
                <div class="line-pron">{opt.examples[0].pronunciation}</div>
              {/if}
            </button>
          </div>
        </div>
      {/if}
    {/each}
  {:else}
    <div class="debug-options">
      <p class="debug-label">Quick options</p>
      {#each fallbackOptions as option}
        <button
          type="button"
          class="chip-advance"
          on:click={() =>
            handleSelectOption({
              next_scenario: option.next_scenario,
              example: { native: option.text, target: option.text }
            })
          }
        >
          <div class="line-native">▶ {option.text}</div>
          <div class="line-target">{option.text}</div>
        </button>
      {/each}
    </div>
  {/if}

  <div class="make-own">
    <div class="make-label">Make your own line</div>
    <div class="make-note">{makeNoteText}</div>
    <div class="make-row">
      <input
        class="make-input"
        bind:value={myNativeText}
        placeholder="Type in your language"
      />
      <button
        class="make-btn"
        on:click={handleTranslate}
        disabled={translating}
      >
        {translating ? '...' : 'Translate'}
      </button>
      <button
        class="make-btn"
        on:click={handleToggleNativeRecording}
      >
        {isNativeRecording ? 'Stop' : '🎤 Speak'}
      </button>
    </div>
  </div>
</div>

<style>
  .options-block {
    width: 100%;
    margin-top: 8px;
    text-align: left;
  }

  .prep-banner {
    background: #ecfdf5;
    border: 1px solid #6ee7b7;
    color: #047857;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 0.9rem;
    margin-bottom: 10px;
  }

  .prep-banner.live-mode {
    background: #eff6ff;
    border-color: #93c5fd;
    color: #1d4ed8;
  }

  .judge-panel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 12px;
  }

  .judge-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }

  .judge-title {
    font-weight: 700;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .judge-pill {
    font-size: 0.8rem;
    padding: 2px 10px;
    border-radius: 999px;
    background: #e0e7ff;
    color: #312e81;
    font-weight: 700;
    letter-spacing: 0.02em;
  }

  .judge-row {
    display: grid;
    grid-template-columns: 72px 1fr 56px;
    gap: 10px;
    align-items: center;
  }

  .judge-side {
    font-size: 0.85rem;
    color: #334155;
    font-weight: 600;
  }

  .judge-slider {
    width: 100%;
  }

  .judge-hint {
    margin-top: 6px;
    font-size: 0.85rem;
    color: #475569;
  }

  .language-panel {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 12px;
  }

  .language-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
  }

  .language-title {
    font-weight: 700;
    color: #0f172a;
    font-size: 0.95rem;
  }

  .language-select {
    width: 100%;
    background: white;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    padding: 8px 10px;
    font-size: 0.9rem;
    color: #0f172a;
  }

  .prompt-question {
    margin: 6px 0 10px;
    font-size: 1rem;
    color: #374151;
  }

  .say-panel {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
    margin-bottom: 8px;
  }

  .say-actions {
    display: inline-flex;
    gap: 8px;
  }

  .line-native {
    font-size: 0.85rem;
    color: #4b5563;
  }

  .line-target {
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
  }

  .line-pron {
    font-size: 0.85rem;
    color: #6b7280;
    font-style: italic;
  }

  .lives {
    margin-left: 6px;
    font-size: 0.9rem;
    color: #6b7280;
  }

  .heard {
    margin-left: 6px;
    font-size: 0.9rem;
    color: #6b7280;
    margin-top: 4px;
  }

  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .chip-group {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .chip-advance {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 6px 10px;
    font-size: 0.9rem;
    cursor: pointer;
  }

  .chip-advance:hover {
    background: #e5e7eb;
  }

.make-own {
  margin-top: 16px;
  background: #f9fafb;
  padding: 12px;
  border-radius: 10px;
}

.make-label {
  font-weight: 600;
  margin-bottom: 6px;
  color: #374151;
}

.make-note {
  font-size: 0.8rem;
  color: #4b5563;
  margin-bottom: 6px;
}

  .make-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .make-input {
    flex: 1;
    padding: 8px 10px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
  }

  .make-btn {
    padding: 8px 10px;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f9fafb;
    cursor: pointer;
  }

  .make-btn:hover {
    background: #f3f4f6;
  }

  .debug-options {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .debug-label {
    width: 100%;
    font-size: 0.85rem;
    color: #6b7280;
    margin: 0;
  }
</style>
