<script>
  import { fade } from 'svelte/transition';
</script>

<div class="scene" in:fade>
  <div class="release-flash"></div>
  <div class="recording-indicator" in:fade={{ delay: 500 }}>
    <div class="rec-dot"></div>
    <span>Speak now: "Watashi wa..."</span>
  </div>
</div>

<style>
  .scene {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }

  .release-flash {
    position: absolute;
    inset: 0;
    background: white;
    animation: flash-release 0.5s ease-out forwards;
    pointer-events: none;
  }

  @keyframes flash-release {
    0% { opacity: 1; }
    100% { opacity: 0; }
  }

  .recording-indicator {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 20px 32px;
    background: rgba(239, 68, 68, 0.2);
    border: 2px solid rgba(239, 68, 68, 0.5);
    border-radius: 16px;
    color: #fca5a5;
    font-size: 1.2rem;
    font-weight: 600;
  }

  .rec-dot {
    width: 16px;
    height: 16px;
    background: #ef4444;
    border-radius: 50%;
    animation: blink 1s ease-in-out infinite;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
</style>
