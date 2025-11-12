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
</script>

<div class="options-block">
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
  }

  .make-label {
    font-weight: 600;
    margin-bottom: 6px;
    color: #374151;
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
