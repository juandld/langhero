<script>
  /**
   * StoryOrchestrator - Master component for narrative flow.
   *
   * Manages progression through:
   *   intro → tutorial → transition → story_intro → drop → awakening → playing
   *
   * Aesthetic transitions:
   *   HOLOGRAPHIC (intro, tutorial, story_intro) → CINEMATIC (awakening, playing)
   */
  import { onMount, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import {
    storyManager,
    storyState,
    currentStory,
    currentDialogue,
    currentDialogueLine,
    currentDialogueKey,
    dialogueIndex,
    isDialogueComplete,
    tutorialProgress,
    STORY_STATES,
  } from '$lib/storyManager.js';
  import { storyStore } from '$lib/storyStore.js';
  import { getApiBase } from '$lib/api';

  // Sub-components
  import AestheticProvider from './AestheticProvider.svelte';
  import DialogueOverlay from './DialogueOverlay.svelte';
  import DropSequence from './DropSequence.svelte';
  import AwakeningCutscene from './AwakeningCutscene.svelte';
  import FirstChallenge from './FirstChallenge.svelte';
  import GameView from '$lib/components/game/GameView.svelte';
  import VolumeControl from '$lib/components/game/VolumeControl.svelte';

  export let storyId = 'shogun';
  export let language = 'Japanese';
  export let panelStoryId = null;
  export let panelSource = 'legacy';

  const dispatch = createEventDispatcher();

  let loading = true;
  let error = null;

  // First challenge scenario (scenario 100)
  let firstChallengeScenario = null;

  // Panel system - now uses line-indexed objects instead of arrays
  let currentPanels = {};  // Line-indexed: {"0": panel, "1": panel, ...}
  let panelCache = {};  // Cache panels by dialogue key
  let panelsLoading = false;
  let storyPanelsById = {};
  let storyPanelOrder = [];
  let storyPanelsLoaded = false;

  const SHOGUN_TEST_DIALOGUE_MAP = {
    tutorial_intro: [
      'pro_01_stars',
      'pro_02_bimbo_appears',
      'pro_02b_conversation',
      'pro_02c_warning',
      'pro_03_decision',
      'pro_04_japan',
    ],
    tutorial_to_story: [
      'pro_02c_warning',
      'pro_03_decision',
      'pro_04_japan',
    ],
    shogun_intro: [
      'pro_01_stars',
      'pro_02_bimbo_appears',
      'pro_02b_conversation',
      'pro_02c_warning',
      'pro_03_decision',
      'pro_04_japan',
    ],
    shogun_drop: [
      'pro_04_japan',
      'ch1_01_wake',
    ],
    awakening: [
      'ch1_01_wake',
      'ch1_01b_memory',
      'ch1_02_farmers_approach',
      'ch1_03_time_freeze',
      'ch1_04_bimbo_teaches',
      'ch1_05_time_resumes',
      'ch1_06_speak',
      'ch1_06b_stop',
    ],
    time_freeze_lesson: [
      'ch1_03_time_freeze',
      'ch1_04_bimbo_teaches',
      'ch1_04b_explain',
      'ch1_05_time_resumes',
    ],
    first_success: [
      'ch1_09_umi_kara',
      'ch1_09b_nod',
      'ch1_10_kite',
      'ch1_10b_end',
    ],
  };

  const SHOGUN_TEST_SCENARIO_MAP = {
    100: 'ch1_06_speak',
    101: 'ch1_07_hana_steps',
    102: 'ch1_08_freeze_doko',
    103: 'ch1_09_umi_kara',
  };

  // Aesthetic mode based on story state
  $: aestheticMode = (() => {
    switch ($storyState) {
      case STORY_STATES.INTRO:
      case STORY_STATES.TUTORIAL:
      case STORY_STATES.TUTORIAL_COMPLETE:
      case STORY_STATES.STORY_INTRO:
      case STORY_STATES.DROP:
        return 'holographic';
      case STORY_STATES.AWAKENING:
      case STORY_STATES.TIME_FREEZE:
      case STORY_STATES.FIRST_CHALLENGE:
      case STORY_STATES.FIRST_SUCCESS:
      case STORY_STATES.PLAYING:
        return 'cinematic';
      default:
        return 'holographic';
    }
  })();

  // Fetch panels when dialogue key changes
  $: if ($currentDialogueKey && !panelCache[$currentDialogueKey]) {
    fetchPanelsForDialogue($currentDialogueKey);
  }

  // Ensure story panels are loaded for story-panels mode
  $: if (panelSource === 'story-panels' && !storyPanelsLoaded) {
    loadStoryPanels(panelStoryId || storyId);
  }

  // Update current panels when dialogue key changes
  $: currentPanels = panelCache[$currentDialogueKey] || {};

  // Current panel for dialogue-driven states
  $: dialoguePanel = (() => {
    const panels = currentPanels;
    if (!panels || Object.keys(panels).length === 0) return null;
    const lineKey = String($dialogueIndex);
    return panels[lineKey] || panels["0"] || null;
  })();

  // Scenario-driven panel for gameplay (Shogun test mapping)
  $: gamePanel = (() => {
    if (panelSource !== 'story-panels') return null;
    if (!showGameView) return null;
    const scenarioId = $storyStore?.id;
    const panelId = SHOGUN_TEST_SCENARIO_MAP[scenarioId];
    if (panelId && storyPanelsById[panelId]) return storyPanelsById[panelId];
    return storyPanelOrder[0] || null;
  })();

  $: currentPanel = gamePanel || dialoguePanel;

  // Background image URL from current panel (with fallback)
  $: panelImageUrl = currentPanel?.image_url || currentPanel?.image || getFallbackImage(aestheticMode);

  // Fallback images when panels haven't loaded
  function getFallbackImage(mode) {
    if (mode === 'holographic') {
      return 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=1200&q=80';
    } else {
      return 'https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=1200&q=80';
    }
  }

  async function fetchPanelsForDialogue(dialogueKey) {
    if (panelsLoading || panelCache[dialogueKey]) return;

    panelsLoading = true;
    try {
      if (panelSource === 'story-panels') {
        if (!storyPanelsLoaded) {
          await loadStoryPanels(panelStoryId || storyId);
        }
        const ids = SHOGUN_TEST_DIALOGUE_MAP[dialogueKey];
        if (ids && ids.length) {
          const lineCount = $currentDialogue?.length || ids.length;
          const resultPanels = {};
          for (let i = 0; i < lineCount; i += 1) {
            const panelId = ids[i] || ids[ids.length - 1];
            if (panelId && storyPanelsById[panelId]) {
              resultPanels[String(i)] = storyPanelsById[panelId];
            }
          }
          panelCache[dialogueKey] = resultPanels;
          panelCache = panelCache; // Trigger reactivity
        }
      } else {
        const apiBase = getApiBase();
        const res = await fetch(`${apiBase}/api/panels/sequence/${dialogueKey}?story_id=${storyId}`);
        if (res.ok) {
          const data = await res.json();
          panelCache[dialogueKey] = data.panels || {};
          panelCache = panelCache; // Trigger reactivity
        }
      }
    } catch (e) {
      console.warn('Failed to fetch panels:', e);
    }
    panelsLoading = false;
  }

  async function loadStoryPanels(storyIdToLoad) {
    if (!storyIdToLoad || storyPanelsLoaded) return;
    try {
      const apiBase = getApiBase();
      const res = await fetch(`${apiBase}/api/story-panels/stories/${storyIdToLoad}`);
      if (!res.ok) return;
      const data = await res.json();
      const byId = {};
      const order = [];
      for (const chapter of data?.chapters || []) {
        for (const panel of chapter?.panels || []) {
          if (panel?.id) {
            byId[panel.id] = panel;
            order.push(panel);
          }
        }
      }
      storyPanelsById = byId;
      storyPanelOrder = order;
      storyPanelsLoaded = true;
    } catch (e) {
      console.warn('Failed to load story panels:', e);
    }
  }

  // Load story on mount
  onMount(async () => {
    try {
      if (storyId) {
        await storyManager.loadStory(storyId);
      } else if (language) {
        await storyManager.loadStoryForLanguage(language);
      }
      loading = false;
    } catch (e) {
      console.error('Failed to load story:', e);
      error = e.message;
      loading = false;
    }
  });

  // Load first challenge scenario when entering TIME_FREEZE state
  $: if ($storyState === STORY_STATES.TIME_FREEZE && !firstChallengeScenario) {
    loadFirstChallengeScenario();
  }

  async function loadFirstChallengeScenario() {
    try {
      const apiBase = getApiBase();
      const firstScenarioId = storyManager.getFirstScenarioId();
      if (firstScenarioId) {
        const res = await fetch(`${apiBase}/api/scenarios/${firstScenarioId}`);
        if (res.ok) {
          firstChallengeScenario = await res.json();
        }
      }
    } catch (e) {
      console.warn('Failed to load first challenge scenario:', e);
    }
  }

  // Handle dialogue advancement
  function handleDialogueAdvance() {
    if ($isDialogueComplete) {
      handleDialogueComplete();
    } else {
      storyManager.advanceDialogue();
    }
  }

  // Handle dialogue completion based on current state
  function handleDialogueComplete() {
    switch ($storyState) {
      case STORY_STATES.INTRO:
        storyManager.startTutorial();
        loadTutorialScenarios();
        break;

      case STORY_STATES.TUTORIAL_COMPLETE:
        storyManager.startStoryIntro();
        break;

      case STORY_STATES.STORY_INTRO:
        storyManager.startDrop();
        break;

      case STORY_STATES.DROP:
        storyManager.startAwakening();
        break;

      case STORY_STATES.AWAKENING:
        // After awakening, go to time freeze lesson
        storyManager.startTimeFreeze();
        break;

      case STORY_STATES.TIME_FREEZE:
        // After lesson, start the first interactive challenge
        storyManager.startFirstChallenge();
        break;

      case STORY_STATES.FIRST_SUCCESS:
        // After success celebration, begin main gameplay
        storyManager.startPlaying();
        loadMainStoryScenarios();
        break;
    }
  }

  // Load tutorial scenarios into storyStore
  function loadTutorialScenarios() {
    const tutorialScenarioIds = storyManager.getTutorialScenarios();
    // For now, the built-in scenarios are already loaded
    // In the future, we might fetch specific scenarios
    if (tutorialScenarioIds.length > 0) {
      storyStore.goToScenario(tutorialScenarioIds[0]);
    }
  }

  // Load main story scenarios
  function loadMainStoryScenarios() {
    const firstScenarioId = storyManager.getFirstScenarioId();
    if (firstScenarioId) {
      storyStore.goToScenario(firstScenarioId);
    }
  }

  // Handle scenario completion during tutorial
  function handleScenarioComplete(event) {
    const { scenarioId, nextScenarioId } = event.detail || {};

    if ($storyState === STORY_STATES.TUTORIAL) {
      storyManager.completeTutorialScenario(scenarioId);

      // If still in tutorial, go to next scenario
      if ($storyState === STORY_STATES.TUTORIAL && nextScenarioId) {
        storyStore.goToScenario(nextScenarioId);
      }
    }
  }

  // Handle drop sequence completion
  function handleDropComplete() {
    storyManager.startAwakening();
  }

  // Handle awakening cutscene completion
  function handleAwakeningComplete() {
    storyManager.startTimeFreeze();
  }

  // Handle time freeze lesson completion
  function handleTimeFreezeComplete() {
    storyManager.startFirstChallenge();
  }

  // Handle first challenge success
  function handleFirstChallengeSuccess() {
    storyManager.startFirstSuccess();
  }

  // Handle first success dialogue completion
  function handleFirstSuccessComplete() {
    storyManager.startPlaying();
    loadMainStoryScenarios();
  }

  // Skip to playing (dev mode)
  function skipToPlaying() {
    storyManager.skipToPlaying();
    loadMainStoryScenarios();
  }

  // Replay from beginning
  function replay() {
    storyManager.reset($currentStory?.id);
    storyManager.loadStory($currentStory?.id || storyId, true);
  }

  // Get background for current state
  $: backgroundClass = (() => {
    switch ($storyState) {
      case STORY_STATES.INTRO:
      case STORY_STATES.STORY_INTRO:
        return 'bg-future';
      case STORY_STATES.DROP:
        return 'bg-vortex';
      case STORY_STATES.TUTORIAL:
      case STORY_STATES.TUTORIAL_COMPLETE:
        return 'bg-tutorial';
      case STORY_STATES.AWAKENING:
      case STORY_STATES.TIME_FREEZE:
      case STORY_STATES.FIRST_CHALLENGE:
      case STORY_STATES.FIRST_SUCCESS:
        return 'bg-cinematic';
      default:
        return 'bg-default';
    }
  })();

  // Show dialogue overlay for dialogue states
  $: showDialogue = [
    STORY_STATES.INTRO,
    STORY_STATES.TUTORIAL_COMPLETE,
    STORY_STATES.STORY_INTRO,
  ].includes($storyState);

  // Show game view for tutorial and playing states
  $: showGameView = [
    STORY_STATES.TUTORIAL,
    STORY_STATES.PLAYING,
  ].includes($storyState);

  $: usePanelBackdropInGame = panelSource === 'story-panels';

  // Show time freeze lesson (uses AwakeningCutscene with time-frozen visuals)
  $: showTimeFreeze = $storyState === STORY_STATES.TIME_FREEZE;

  // Show first challenge (interactive speaking moment)
  $: showFirstChallenge = $storyState === STORY_STATES.FIRST_CHALLENGE;

  // Show first success (uses AwakeningCutscene for celebration)
  $: showFirstSuccess = $storyState === STORY_STATES.FIRST_SUCCESS;

  // Show drop sequence
  $: showDrop = $storyState === STORY_STATES.DROP;

  // Show awakening cutscene
  $: showAwakening = $storyState === STORY_STATES.AWAKENING;
</script>

<AestheticProvider mode={aestheticMode}>
  <div class="story-orchestrator {backgroundClass}">
    <!-- Panel Background Image -->
    {#key currentPanel?.id || aestheticMode}
      <div
        class="panel-background"
        class:holographic={aestheticMode === 'holographic'}
        class:cinematic={aestheticMode === 'cinematic'}
        style="background-image: url({panelImageUrl})"
        in:fade={{ duration: 400 }}
        out:fade={{ duration: 200 }}
      ></div>
    {/key}

    <!-- Aesthetic overlay effects -->
    {#if aestheticMode === 'holographic'}
      <div class="holographic-overlay"></div>
    {:else if aestheticMode === 'cinematic'}
      <div class="cinematic-overlay"></div>
    {/if}

    {#if loading}
      <div class="loading-state" transition:fade>
        <div class="loading-spinner"></div>
        <p>Loading story...</p>
      </div>
    {:else if error}
      <div class="error-state" transition:fade>
        <p>Failed to load story: {error}</p>
        <button on:click={() => location.reload()}>Retry</button>
      </div>
    {:else}
      <!-- Dialogue Overlay (intro, transition, story intro) -->
      {#if showDialogue}
        <DialogueOverlay
          line={$currentDialogueLine}
          isComplete={$isDialogueComplete}
          state={$storyState}
          on:advance={handleDialogueAdvance}
          on:skip={skipToPlaying}
        />
      {/if}

      <!-- Drop Sequence -->
      {#if showDrop}
        <DropSequence
          dialogue={$currentDialogueLine}
          on:complete={handleDropComplete}
        />
      {/if}

      <!-- Awakening Cutscene -->
      {#if showAwakening}
        <AwakeningCutscene
          dialogue={$currentDialogueLine}
          isComplete={$isDialogueComplete}
          panel={currentPanel}
          on:advance={handleDialogueAdvance}
          on:complete={handleAwakeningComplete}
          on:skip={skipToPlaying}
        />
      {/if}

      <!-- Time Freeze Lesson (Bimbo teaches first phrase) -->
      {#if showTimeFreeze}
        <AwakeningCutscene
          dialogue={$currentDialogueLine}
          isComplete={$isDialogueComplete}
          panel={currentPanel}
          on:advance={handleDialogueAdvance}
          on:complete={handleTimeFreezeComplete}
          on:skip={skipToPlaying}
        />
      {/if}

      <!-- First Challenge (interactive speaking moment) -->
      {#if showFirstChallenge}
        <FirstChallenge
          scenario={firstChallengeScenario}
          panel={currentPanel}
          on:success={handleFirstChallengeSuccess}
          on:skip={skipToPlaying}
        />
      {/if}

      <!-- First Success celebration -->
      {#if showFirstSuccess}
        <AwakeningCutscene
          dialogue={$currentDialogueLine}
          isComplete={$isDialogueComplete}
          panel={currentPanel}
          on:advance={handleDialogueAdvance}
          on:complete={handleFirstSuccessComplete}
          on:skip={skipToPlaying}
        />
      {/if}

      <!-- Game View (tutorial and playing) -->
      {#if showGameView}
        <GameView
          showBackdrop={!usePanelBackdropInGame}
          transparentBackground={usePanelBackdropInGame}
          on:scenarioComplete={handleScenarioComplete}
        />
      {:else}
        <!-- Volume control for non-game states -->
        <!-- svelte-ignore a11y-click-events-have-key-events -->
        <!-- svelte-ignore a11y-no-static-element-interactions -->
        <div class="story-volume-control" on:click|stopPropagation>
          <VolumeControl />
        </div>
      {/if}

      <!-- Dev controls -->
      {#if import.meta.env.DEV}
        <div class="dev-controls">
          <span class="state-badge">{$storyState}</span>
          <span class="aesthetic-badge">{aestheticMode}</span>
          <button on:click={skipToPlaying}>Skip to Story</button>
          <button on:click={replay}>Replay</button>
        </div>
      {/if}
    {/if}
  </div>
</AestheticProvider>

<style>
  .story-orchestrator {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: background 0.5s ease;
  }

  /* Background states */
  .bg-future {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 50%, #16213e 100%);
  }

  .bg-tutorial {
    background: #0f172a;
  }

  .bg-vortex {
    background: radial-gradient(ellipse at center, #2d1b4e 0%, #0a0a1a 70%);
  }

  .bg-cinematic {
    background: linear-gradient(135deg, #1a1515 0%, #261f1f 50%, #2d2424 100%);
  }

  .bg-default {
    background: #0f172a;
  }

  /* Panel background image */
  .panel-background {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    z-index: 0;
  }

  .panel-background.holographic {
    filter: saturate(1.1) brightness(0.85);
  }

  .panel-background.holographic::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      rgba(139, 92, 246, 0.1) 0%,
      transparent 30%,
      transparent 70%,
      rgba(6, 182, 212, 0.15) 100%
    );
    pointer-events: none;
  }

  .panel-background.cinematic {
    filter: saturate(0.9) contrast(1.1);
  }

  .panel-background.cinematic::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      rgba(0, 0, 0, 0.3) 0%,
      transparent 20%,
      transparent 80%,
      rgba(0, 0, 0, 0.5) 100%
    );
    pointer-events: none;
  }

  /* Holographic overlay - scan lines + grid */
  .holographic-overlay {
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background:
      repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(139, 92, 246, 0.03) 2px,
        rgba(139, 92, 246, 0.03) 4px
      );
    animation: scan-drift 8s linear infinite;
  }

  .holographic-overlay::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      linear-gradient(90deg, transparent 95%, rgba(139, 92, 246, 0.1) 100%),
      linear-gradient(0deg, transparent 95%, rgba(6, 182, 212, 0.1) 100%);
    background-size: 40px 40px;
    opacity: 0.3;
  }

  @keyframes scan-drift {
    0% { transform: translateY(0); }
    100% { transform: translateY(4px); }
  }

  /* Cinematic overlay - film grain + vignette */
  .cinematic-overlay {
    position: absolute;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background: radial-gradient(
      ellipse at center,
      transparent 0%,
      transparent 50%,
      rgba(0, 0, 0, 0.4) 100%
    );
  }

  .cinematic-overlay::before {
    content: '';
    position: absolute;
    inset: 0;
    opacity: 0.05;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    animation: grain 0.5s steps(10) infinite;
  }

  @keyframes grain {
    0%, 100% { transform: translate(0, 0); }
    10% { transform: translate(-1%, -1%); }
    20% { transform: translate(1%, 1%); }
    30% { transform: translate(-1%, 1%); }
    40% { transform: translate(1%, -1%); }
    50% { transform: translate(-1%, 0%); }
    60% { transform: translate(1%, 0%); }
    70% { transform: translate(0%, 1%); }
    80% { transform: translate(0%, -1%); }
    90% { transform: translate(1%, 1%); }
  }

  /* Loading state */
  .loading-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    color: #e2e8f0;
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: #8b5cf6;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Error state */
  .error-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 16px;
    color: #fca5a5;
  }

  .error-state button {
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #fca5a5;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
  }

  /* Dev controls */
  .dev-controls {
    position: fixed;
    bottom: 16px;
    right: 16px;
    display: flex;
    gap: 8px;
    align-items: center;
    z-index: 9999;
  }

  .state-badge {
    background: rgba(139, 92, 246, 0.3);
    color: #c4b5fd;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .aesthetic-badge {
    background: rgba(6, 182, 212, 0.3);
    color: #67e8f9;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .dev-controls button {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.7);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    cursor: pointer;
  }

  .dev-controls button:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  /* Volume control for story/dialogue states */
  .story-volume-control {
    position: fixed;
    top: 16px;
    left: 16px;
    z-index: 200;
  }
</style>
