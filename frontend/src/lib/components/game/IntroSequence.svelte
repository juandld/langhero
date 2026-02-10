<script>
  /**
   * IntroSequence - Orchestrates the intro narrative flow.
   *
   * Uses modular scene components for each phase.
   * Handles dialogue progression, recording, and phase transitions.
   */
  import { createEventDispatcher, onMount, onDestroy } from 'svelte';
  import { fade } from 'svelte/transition';
  import { playTTS, getIntroPanels } from '$lib/api';

  // Import intro components
  import {
    PHASES,
    LESSON_STATES,
    PANEL_PHASE_ASSIGNMENTS,
    getDialogueForPhase,
    getPhaseName,
    IntroBackground,
    BimboOrb,
    FutureScene,
    SetupScene,
    DropScene,
    AwakeningScene,
    TimeFreezeScene,
    LessonScene,
    ReleaseScene,
    ReleasingScene,
    CompleteScene,
  } from '$lib/components/intro';

  export let visible = true;

  const dispatch = createEventDispatcher();

  // Panel data
  let panelsLoaded = false;
  let panelsByPhase = {};

  // Phase management
  let phase = 0;
  let transitioning = false;

  // Dialogue state
  let currentLine = 0;
  let textComplete = false;
  let lessonState = LESSON_STATES.INITIAL;

  // Lesson interaction state
  let hasListened = false;
  let hasPracticed = false;
  let isRecording = false;
  let showReleaseButton = false;
  let isReleasing = false;

  // Recording
  let mediaRecorder;
  let audioChunks = [];

  // Derived state
  $: currentDialogue = getDialogueForPhase(phase, lessonState);
  $: currentLineData = currentDialogue[currentLine] || null;
  $: phaseName = getPhaseName(phase);
  $: currentPhasePanels = panelsByPhase[phaseName] || [];
  $: currentPanelIndex = Math.min(currentLine, currentPhasePanels.length - 1);
  $: activePanel = currentPhasePanels[Math.max(0, currentPanelIndex)] || null;
  $: isFrozen = phase >= PHASES.TIME_FREEZE && phase < PHASES.RELEASE;
  $: isLive = phase === PHASES.AWAKENING || isReleasing || phase === PHASES.COMPLETE;

  // ─────────────────────────────────────────────────────────────
  // Lifecycle
  // ─────────────────────────────────────────────────────────────

  onMount(async () => {
    await loadPanels();
    startTextSequence();
  });

  onDestroy(() => {
    stopRecording();
  });

  async function loadPanels() {
    try {
      const response = await getIntroPanels();
      const panels = response.panels || [];
      const panelMap = Object.fromEntries(panels.map(p => [p.id, p]));

      PANEL_PHASE_ASSIGNMENTS.forEach(({ id, phases }) => {
        const panel = panelMap[id];
        if (panel) {
          phases.forEach(phaseName => {
            panelsByPhase[phaseName] = panelsByPhase[phaseName] || [];
            panelsByPhase[phaseName].push(panel);
          });
        }
      });
      panelsByPhase = panelsByPhase;
      panelsLoaded = true;
    } catch (err) {
      console.warn('Failed to load intro panels:', err);
      panelsLoaded = true;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Text & Phase Navigation
  // ─────────────────────────────────────────────────────────────

  function startTextSequence() {
    currentLine = 0;
    textComplete = false;
  }

  function advanceText() {
    if (transitioning) return;
    if (currentLine < currentDialogue.length - 1) {
      currentLine += 1;
    } else {
      textComplete = true;
    }
  }

  function nextPhase() {
    if (transitioning) return;
    transitioning = true;

    setTimeout(() => {
      phase += 1;
      currentLine = 0;
      textComplete = false;
      transitioning = false;

      // Phase-specific setup
      if (phase === PHASES.DROP) {
        setTimeout(startTextSequence, 500);
      } else if (phase === PHASES.TIME_FREEZE) {
        startTextSequence();
      } else if (phase === PHASES.LESSON) {
        startTextSequence();
        hasListened = false;
        hasPracticed = false;
        lessonState = LESSON_STATES.INITIAL;
      } else if (phase === PHASES.RELEASE) {
        startTextSequence();
        showReleaseButton = true;
      } else if (phase === PHASES.COMPLETE) {
        startTextSequence();
      }
    }, 300);
  }

  // ─────────────────────────────────────────────────────────────
  // Lesson Phase Handlers
  // ─────────────────────────────────────────────────────────────

  async function handleListen() {
    await playExamplePhrase();
    hasListened = true;
    setTimeout(() => {
      currentLine = 0;
      lessonState = LESSON_STATES.LISTENED;
    }, 1500);
  }

  async function handlePractice() {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording(() => {
        hasPracticed = true;
        setTimeout(() => {
          currentLine = 0;
          lessonState = LESSON_STATES.SUCCESS;
          textComplete = false;
        }, 500);
      });

      // Auto-stop after 3 seconds
      setTimeout(() => {
        if (isRecording) stopRecording();
      }, 3000);
    }
  }

  function handleRelease() {
    isReleasing = true;
    showReleaseButton = false;

    setTimeout(async () => {
      await startRecording(() => {
        isReleasing = false;
        phase = PHASES.COMPLETE;
        startTextSequence();
      });

      // Auto-stop after 2.5 seconds
      setTimeout(() => {
        if (isRecording) stopRecording();
      }, 2500);
    }, 1000);
  }

  // ─────────────────────────────────────────────────────────────
  // Audio Helpers
  // ─────────────────────────────────────────────────────────────

  async function playExamplePhrase() {
    try {
      await playTTS('私は', {
        language: 'Japanese',
        role: 'player_example',
        voice: 'nova',
      });
    } catch (err) {
      console.warn('TTS failed, using fallback:', err);
      if ('speechSynthesis' in window) {
        const utter = new SpeechSynthesisUtterance('私は');
        utter.lang = 'ja-JP';
        utter.rate = 0.8;
        window.speechSynthesis.speak(utter);
      }
    }
  }

  async function startRecording(onComplete) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
      mediaRecorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        onComplete?.();
      };

      mediaRecorder.start();
      isRecording = true;
    } catch (err) {
      console.error('Mic access error:', err);
      onComplete?.(); // Fallback: proceed anyway
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    isRecording = false;
  }

  // ─────────────────────────────────────────────────────────────
  // Keyboard & Skip
  // ─────────────────────────────────────────────────────────────

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      dispatch('complete');
    } else if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      if (textComplete) {
        if (phase === PHASES.COMPLETE) {
          dispatch('complete');
        } else if (phase === PHASES.LESSON && hasListened && hasPracticed) {
          nextPhase();
        } else if (phase !== PHASES.LESSON && phase !== PHASES.RELEASE) {
          nextPhase();
        }
      } else {
        advanceText();
      }
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if visible}
  <div
    class="intro-container"
    class:frozen={isFrozen}
    class:live={isLive}
    class:releasing={isReleasing}
    transition:fade={{ duration: 400 }}
  >
    <IntroBackground {phase} {activePanel} {panelsLoaded} {isFrozen} />

    <button class="skip-btn" on:click={() => dispatch('complete')}>Skip</button>

    {#if phase >= PHASES.FUTURE}
      <BimboOrb speaking={currentLineData?.speaker === 'bimbo'} />
    {/if}

    <div class="content-area">
      {#if phase === PHASES.FUTURE}
        <FutureScene
          line={currentLineData}
          {textComplete}
          on:advance={advanceText}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.SETUP}
        <SetupScene
          line={currentLineData}
          {textComplete}
          on:advance={advanceText}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.DROP}
        <DropScene
          line={currentLineData}
          {textComplete}
          on:advance={advanceText}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.AWAKENING}
        <AwakeningScene
          line={currentLineData}
          {textComplete}
          {transitioning}
          on:advance={advanceText}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.TIME_FREEZE}
        <TimeFreezeScene
          line={currentLineData}
          {textComplete}
          on:advance={advanceText}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.LESSON}
        <LessonScene
          line={currentLineData}
          {textComplete}
          {hasListened}
          {hasPracticed}
          {isRecording}
          on:listen={handleListen}
          on:practice={handlePractice}
          on:next={nextPhase}
        />
      {:else if phase === PHASES.RELEASE && !isReleasing}
        <ReleaseScene
          line={currentLineData}
          {showReleaseButton}
          on:release={handleRelease}
        />
      {:else if isReleasing}
        <ReleasingScene />
      {:else if phase === PHASES.COMPLETE}
        <CompleteScene
          line={currentLineData}
          {textComplete}
          on:advance={advanceText}
          on:complete={() => dispatch('complete')}
        />
      {/if}
    </div>

    <audio style="display: none;"></audio>
  </div>
{/if}

<style>
  .intro-container {
    position: fixed;
    inset: 0;
    z-index: 10000;
    display: flex;
    flex-direction: column;
    font-family: system-ui, -apple-system, sans-serif;
    overflow: hidden;
  }

  .skip-btn {
    position: absolute;
    top: 16px;
    right: 16px;
    z-index: 100;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.5);
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .skip-btn:hover {
    background: rgba(255,255,255,0.2);
    color: rgba(255,255,255,0.8);
  }

  .content-area {
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: 60px 24px;
    max-width: 500px;
    margin: 0 auto;
    width: 100%;
    z-index: 10;
  }
</style>
