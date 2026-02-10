<script>
  import { scale } from 'svelte/transition';

  export let speaking = false;
</script>

<div class="bimbo-orb" class:speaking transition:scale={{ duration: 300 }}>
  <div class="orb-glow"></div>
  <div class="orb-core">🔮</div>
</div>

<style>
  .bimbo-orb {
    position: absolute;
    bottom: 100px;
    left: 20px;
    z-index: 50;
    width: 50px;
    height: 50px;
  }

  .orb-glow {
    position: absolute;
    inset: -8px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.4) 0%, transparent 70%);
    animation: pulse-glow 2s ease-in-out infinite;
  }

  .bimbo-orb.speaking .orb-glow {
    animation: pulse-glow-speaking 0.5s ease-in-out infinite;
  }

  @keyframes pulse-glow {
    0%, 100% { opacity: 0.5; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
  }

  @keyframes pulse-glow-speaking {
    0%, 100% { opacity: 0.7; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.2); }
  }

  .orb-core {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    background: linear-gradient(135deg, #1e1b4b, #312e81);
    border-radius: 50%;
    border: 2px solid rgba(139, 92, 246, 0.5);
  }
</style>
