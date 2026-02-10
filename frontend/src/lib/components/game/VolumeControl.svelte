<script>
  /**
   * AudioControl - Expandable audio settings (volume + speed).
   *
   * Features:
   * - Collapsed by default (speaker icon only)
   * - Expands on tap/click to show volume and speed sliders
   * - Uses shared audioStore for global settings
   * - Auto-collapses after inactivity
   * - Visual feedback for current levels
   */
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { masterVolume, setVolume, playbackSpeed, setSpeed } from '$lib/audioStore.js';
  import { STORAGE_KEYS, getString, setString } from '$lib/utils/storage';

  const dispatch = createEventDispatcher();
  const VOLUME_KEY = 'LANGHERO_VOLUME_V1';

  let expanded = false;
  let collapseTimer = null;
  let isDragging = false;
  let volume = 1.0;
  let speed = 1.25;

  // Mic state
  let micDevices = [];
  let selectedMicId = '';

  // Sync with the shared stores
  $: volume = $masterVolume;
  $: speed = $playbackSpeed;

  // Speed label
  $: speedLabel = speed.toFixed(2).replace(/\.?0+$/, '') + 'x';

  function toggleExpanded() {
    expanded = !expanded;
    if (expanded) {
      scheduleCollapse();
      if (micDevices.length === 0) loadMicDevices();
    }
  }

  function scheduleCollapse() {
    if (collapseTimer) {
      clearTimeout(collapseTimer);
    }
    collapseTimer = setTimeout(() => {
      if (!isDragging) {
        expanded = false;
      }
    }, 4000);
  }

  function handleVolumeChange(e) {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    dispatch('volumeChange', newVolume);
    scheduleCollapse();
  }

  function handleSpeedChange(e) {
    const newSpeed = parseFloat(e.target.value);
    setSpeed(newSpeed);
    dispatch('speedChange', newSpeed);
    scheduleCollapse();
  }

  function handleSliderStart() {
    isDragging = true;
  }

  function handleSliderEnd() {
    isDragging = false;
    scheduleCollapse();
  }

  function toggleMute() {
    if (volume > 0) {
      try {
        localStorage.setItem(VOLUME_KEY + '_prev', String(volume));
      } catch (_) {}
      setVolume(0);
    } else {
      try {
        const prev = parseFloat(localStorage.getItem(VOLUME_KEY + '_prev') || '1');
        setVolume(isNaN(prev) ? 1 : Math.max(0.1, prev));
      } catch (_) {
        setVolume(1);
      }
    }
    dispatch('volumeChange', $masterVolume);
    scheduleCollapse();
  }

  async function loadMicDevices() {
    try {
      // Request permission first so labels are populated
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(t => t.stop());

      const devices = await navigator.mediaDevices.enumerateDevices();
      micDevices = devices.filter(d => d.kind === 'audioinput');
      selectedMicId = getString(STORAGE_KEYS.MIC_DEVICE_ID, '');
      // Validate stored ID still exists
      if (selectedMicId && !micDevices.find(d => d.deviceId === selectedMicId)) {
        selectedMicId = '';
      }
    } catch (err) {
      console.warn('[Mic] Could not enumerate devices:', err);
    }
  }

  function handleMicChange(e) {
    selectedMicId = e.target.value;
    setString(STORAGE_KEYS.MIC_DEVICE_ID, selectedMicId);
    dispatch('micChange', selectedMicId);
    scheduleCollapse();
  }

  function handleClickOutside(e) {
    if (expanded && !e.target.closest('.audio-control')) {
      expanded = false;
    }
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
  });

  onDestroy(() => {
    if (collapseTimer) {
      clearTimeout(collapseTimer);
    }
    document.removeEventListener('click', handleClickOutside);
  });
</script>

<div class="audio-control" class:expanded>
  <!-- Expandable panel (positioned absolute, before button in DOM for proper stacking) -->
  {#if expanded}
    <div
      class="settings-panel"
      class:visible={expanded}
    >
      <div class="settings-panel-inner">
      <!-- Volume row -->
        <div class="setting-row">
          <span class="setting-icon" title="Volume">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 5L6 9H2v6h4l5 4V5z" />
            </svg>
          </span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={volume}
            on:input={handleVolumeChange}
            on:mousedown={handleSliderStart}
            on:mouseup={handleSliderEnd}
            on:touchstart={handleSliderStart}
            on:touchend={handleSliderEnd}
            class="slider volume-slider"
            aria-label="Volume"
            style="--fill-percent: {volume * 100}%"
          />
          <span class="setting-value">{Math.round(volume * 100)}%</span>
        </div>

        <!-- Speed row -->
        <div class="setting-row">
          <span class="setting-icon" title="Playback Speed">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </span>
          <input
            type="range"
            min="0.5"
            max="2"
            step="0.05"
            value={speed}
            on:input={handleSpeedChange}
            on:mousedown={handleSliderStart}
            on:mouseup={handleSliderEnd}
            on:touchstart={handleSliderStart}
            on:touchend={handleSliderEnd}
            class="slider speed-slider"
            aria-label="Playback Speed"
            style="--fill-percent: {((speed - 0.5) / 1.5) * 100}%"
          />
          <span class="setting-value">{speedLabel}</span>
        </div>

        <!-- Mic selector row -->
        {#if micDevices.length > 0}
          <div class="setting-row mic-row">
            <span class="setting-icon" title="Microphone">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </span>
            <select
              class="mic-select"
              value={selectedMicId}
              on:change={handleMicChange}
              aria-label="Microphone"
            >
              <option value="">Default mic</option>
              {#each micDevices as device}
                <option value={device.deviceId}>
                  {device.label || `Mic ${micDevices.indexOf(device) + 1}`}
                </option>
              {/each}
            </select>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <!-- Main button -->
  <button
    class="audio-btn"
    class:muted={volume === 0}
    on:click={toggleExpanded}
    aria-label={expanded ? 'Close sound settings' : (volume === 0 ? 'Sound muted - tap to adjust' : 'Sound settings')}
    title={volume === 0 ? 'Sound muted' : 'Sound settings'}
  >
    <!-- Sliders/equalizer icon for sound settings -->
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <line x1="4" y1="21" x2="4" y2="14" />
      <line x1="4" y1="10" x2="4" y2="3" />
      <line x1="12" y1="21" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12" y2="3" />
      <line x1="20" y1="21" x2="20" y2="16" />
      <line x1="20" y1="12" x2="20" y2="3" />
      <line x1="1" y1="14" x2="7" y2="14" />
      <line x1="9" y1="8" x2="15" y2="8" />
      <line x1="17" y1="16" x2="23" y2="16" />
    </svg>
  </button>
</div>

<style>
  .audio-control {
    position: relative;
    display: flex;
    align-items: center;
  }

  .audio-btn {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 50%;
    cursor: pointer;
    transition: background 0.2s ease, border-color 0.2s ease;
    padding: 0;
    flex-shrink: 0;
    z-index: 2;
  }

  .audio-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.25);
  }

  .audio-btn:active {
    transform: scale(0.95);
  }

  .audio-btn svg {
    width: 20px;
    height: 20px;
    color: rgba(255, 255, 255, 0.8);
  }

  .audio-control.expanded .audio-btn {
    background: rgba(139, 92, 246, 0.3);
    border-color: rgba(139, 92, 246, 0.5);
  }

  .audio-control.expanded .audio-btn svg {
    color: #c4b5fd;
  }

  /* Muted state - pulsing animation to indicate audio is off */
  .audio-btn.muted {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.4);
    animation: muted-pulse 2s ease-in-out infinite;
  }

  .audio-btn.muted svg {
    color: #fca5a5;
  }

  .audio-btn.muted:hover {
    background: rgba(239, 68, 68, 0.3);
    border-color: rgba(239, 68, 68, 0.5);
    animation: none;
  }

  @keyframes muted-pulse {
    0%, 100% {
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4);
      transform: scale(1);
    }
    50% {
      box-shadow: 0 0 12px 4px rgba(239, 68, 68, 0.3);
      transform: scale(1.05);
    }
  }

  .settings-panel {
    position: absolute;
    left: 50%;
    top: 100%;
    transform: translateX(-50%);
    margin-top: 8px;
    z-index: 1;
  }

  .settings-panel-inner {
    display: flex;
    flex-direction: column;
    gap: 10px;
    background: rgba(0, 0, 0, 0.85);
    backdrop-filter: blur(12px);
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    animation: slideDown 0.2s ease-out forwards;
    opacity: 0;
    transform: translateY(-4px);
  }

  @keyframes slideDown {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .setting-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .setting-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
    opacity: 0.6;
  }

  .setting-icon svg {
    width: 100%;
    height: 100%;
    color: rgba(255, 255, 255, 0.7);
  }

  .slider {
    width: 90px;
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: linear-gradient(
      to right,
      rgba(139, 92, 246, 0.8) 0%,
      rgba(139, 92, 246, 0.8) var(--fill-percent, 100%),
      rgba(255, 255, 255, 0.2) var(--fill-percent, 100%),
      rgba(255, 255, 255, 0.2) 100%
    );
    border-radius: 2px;
    outline: none;
    cursor: pointer;
  }

  .slider::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 14px;
    height: 14px;
    background: #fff;
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
    transition: transform 0.15s ease;
  }

  .slider::-webkit-slider-thumb:hover {
    transform: scale(1.15);
  }

  .slider::-webkit-slider-thumb:active {
    transform: scale(1.25);
  }

  .slider::-moz-range-thumb {
    width: 14px;
    height: 14px;
    background: #fff;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  }

  .setting-value {
    font-size: 0.7rem;
    color: rgba(255, 255, 255, 0.7);
    min-width: 36px;
    text-align: right;
    font-variant-numeric: tabular-nums;
    font-weight: 500;
  }

  .mic-row {
    padding-top: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
  }

  .mic-select {
    flex: 1;
    min-width: 0;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 6px;
    color: rgba(255, 255, 255, 0.85);
    font-size: 0.7rem;
    padding: 5px 8px;
    cursor: pointer;
    appearance: none;
    -webkit-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6'%3E%3Cpath d='M0 0l5 6 5-6z' fill='rgba(255,255,255,0.5)'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 6px center;
    padding-right: 20px;
    max-width: 140px;
    text-overflow: ellipsis;
  }

  .mic-select:focus {
    outline: none;
    border-color: rgba(139, 92, 246, 0.5);
  }

  .mic-select option {
    background: #1a1a2e;
    color: #fff;
  }

  /* Mobile adjustments */
  @media (max-width: 500px) {
    .audio-btn {
      width: 36px;
      height: 36px;
    }

    .audio-btn svg {
      width: 18px;
      height: 18px;
    }

    .settings-panel-inner {
      padding: 10px 12px;
    }

    .slider {
      width: 70px;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .audio-btn,
    .slider::-webkit-slider-thumb {
      transition: none;
    }

    .audio-btn.muted {
      animation: none;
      /* Keep the visual indicator without motion */
      box-shadow: 0 0 8px 2px rgba(239, 68, 68, 0.3);
    }

    .settings-panel-inner {
      animation: none;
      opacity: 1;
      transform: none;
    }
  }
</style>
