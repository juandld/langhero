<script>
  export let imageUrl = '';
  export let isTimeStopped = true;
  export let loading = false;

  let imageLoaded = false;
  let imageError = false;

  $: showPlaceholder = !imageUrl || imageError;

  function handleImageLoad() {
    imageLoaded = true;
    imageError = false;
  }

  function handleImageError() {
    imageError = true;
    imageLoaded = false;
  }

  // Reset states when image URL changes
  $: if (imageUrl) {
    imageLoaded = false;
    imageError = false;
  }
</script>

<div class="game-scene" class:time-stopped={isTimeStopped} class:live-mode={!isTimeStopped}>
  {#if loading}
    <div class="scene-placeholder shimmer">
      <div class="shimmer-animation"></div>
      <span class="loading-text">Generating scene...</span>
    </div>
  {:else if showPlaceholder}
    <div class="scene-placeholder gradient">
      <span class="placeholder-icon">🌸</span>
    </div>
  {:else}
    <div class="scene-image-container" class:loaded={imageLoaded}>
      <img
        src={imageUrl}
        alt="Scene"
        class="scene-image"
        on:load={handleImageLoad}
        on:error={handleImageError}
      />
      {#if !imageLoaded}
        <div class="scene-placeholder gradient loading-overlay">
          <span class="placeholder-icon">🌸</span>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Time stop overlay effect -->
  {#if isTimeStopped && !loading}
    <div class="time-stop-overlay"></div>
    <div class="time-stop-particles">
      <div class="particle p1"></div>
      <div class="particle p2"></div>
      <div class="particle p3"></div>
      <div class="particle p4"></div>
    </div>
  {/if}

  <!-- Vignette for cinematic feel -->
  <div class="vignette"></div>
</div>

<style>
  .game-scene {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 300px;
    overflow: hidden;
    background: #0f172a;
  }

  .scene-image-container {
    width: 100%;
    height: 100%;
    position: relative;
  }

  .scene-image {
    width: 100%;
    height: 100%;
    object-fit: cover;
    opacity: 0;
    transition: opacity 0.4s ease;
  }

  .scene-image-container.loaded .scene-image {
    opacity: 1;
  }

  /* Time stop visual effect */
  .game-scene.time-stopped .scene-image {
    filter: saturate(0.6) brightness(0.9);
    transition: filter 0.4s ease, opacity 0.4s ease;
  }

  .game-scene.live-mode .scene-image {
    filter: saturate(1.1) brightness(1.05);
  }

  .time-stop-overlay {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse at center,
      transparent 40%,
      rgba(99, 102, 241, 0.15) 100%
    );
    pointer-events: none;
    animation: pulse-glow 3s ease-in-out infinite;
  }

  @keyframes pulse-glow {
    0%, 100% {
      opacity: 0.6;
    }
    50% {
      opacity: 1;
    }
  }

  .time-stop-particles {
    position: absolute;
    inset: 0;
    pointer-events: none;
    overflow: hidden;
  }

  .particle {
    position: absolute;
    width: 4px;
    height: 4px;
    background: rgba(199, 210, 254, 0.8);
    border-radius: 50%;
    animation: float 6s ease-in-out infinite;
  }

  .p1 { left: 20%; top: 30%; animation-delay: 0s; }
  .p2 { left: 70%; top: 20%; animation-delay: 1.5s; }
  .p3 { left: 40%; top: 60%; animation-delay: 3s; }
  .p4 { left: 80%; top: 70%; animation-delay: 4.5s; }

  @keyframes float {
    0%, 100% {
      transform: translateY(0) scale(1);
      opacity: 0.4;
    }
    50% {
      transform: translateY(-20px) scale(1.2);
      opacity: 0.8;
    }
  }

  .vignette {
    position: absolute;
    inset: 0;
    background: radial-gradient(
      ellipse at center,
      transparent 50%,
      rgba(15, 23, 42, 0.4) 100%
    );
    pointer-events: none;
  }

  .scene-placeholder {
    width: 100%;
    height: 100%;
    min-height: 300px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  .scene-placeholder.gradient {
    background: linear-gradient(135deg, #1e293b, #334155, #475569, #334155);
    background-size: 400% 400%;
    animation: gradientShift 8s ease infinite;
  }

  @keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  .scene-placeholder.shimmer {
    background: linear-gradient(135deg, #1e293b, #334155);
  }

  .shimmer-animation {
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(
      90deg,
      transparent,
      rgba(255, 255, 255, 0.1),
      transparent
    );
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
  }

  .placeholder-icon {
    font-size: 4rem;
    opacity: 0.3;
    animation: gentle-bounce 3s ease-in-out infinite;
  }

  @keyframes gentle-bounce {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
  }

  .loading-text {
    position: absolute;
    bottom: 20%;
    font-size: 0.9rem;
    color: rgba(255, 255, 255, 0.5);
    font-weight: 500;
  }

  .loading-overlay {
    position: absolute;
    inset: 0;
    margin: 0;
    border-radius: 0;
  }

  .scene-image-container.loaded .loading-overlay {
    display: none;
  }
</style>
