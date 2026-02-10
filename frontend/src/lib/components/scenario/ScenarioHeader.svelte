<script>
  export let imageUrl = '';
  export let aiImageUrl = '';
  export let dialogueJp = '';
  export let dialogueEn = '';
  export let description = '';
  export let loading = false;

  let imageLoaded = false;
  let imageError = false;

  $: effectiveImageUrl = aiImageUrl || imageUrl;
  $: showPlaceholder = !effectiveImageUrl || imageError;

  function handleImageLoad() {
    imageLoaded = true;
    imageError = false;
  }

  function handleImageError() {
    imageError = true;
    imageLoaded = false;
  }

  // Reset states when image URL changes
  $: if (effectiveImageUrl) {
    imageLoaded = false;
    imageError = false;
  }
</script>

<div class="scene-header">
  {#if loading}
    <div class="image-placeholder shimmer">
      <div class="shimmer-animation"></div>
      <span class="loading-text">Generating scene...</span>
    </div>
  {:else if showPlaceholder}
    <div class="image-placeholder gradient">
      <span class="placeholder-icon">🎌</span>
    </div>
  {:else}
    <div class="image-container" class:loaded={imageLoaded}>
      <img
        src={effectiveImageUrl}
        alt="Scenario scene"
        class="scenario-image"
        on:load={handleImageLoad}
        on:error={handleImageError}
      />
      {#if !imageLoaded}
        <div class="image-placeholder gradient loading-behind">
          <span class="placeholder-icon">🎌</span>
        </div>
      {/if}
    </div>
  {/if}
</div>

<div class="dialogue-box">
  <p class="character-dialogue-jp">{dialogueJp}</p>
  <p class="character-dialogue-en"><em>{dialogueEn}</em></p>
</div>

{#if description}
  <p class="user-prompt">{description}</p>
{/if}

<style>
  .scene-header {
    width: 100%;
    margin-bottom: 20px;
  }

  .image-container {
    position: relative;
    width: 100%;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .image-container .scenario-image {
    display: block;
    width: 100%;
    height: auto;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .image-container.loaded .scenario-image {
    opacity: 1;
  }

  .image-container .loading-behind {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    margin: 0;
    border-radius: 0;
  }

  .image-container.loaded .loading-behind {
    display: none;
  }

  .image-placeholder {
    width: 100%;
    height: 200px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  .image-placeholder.gradient {
    background: linear-gradient(135deg, #fce7f3, #fbcfe8, #f9a8d4, #f472b6);
    background-size: 200% 200%;
    animation: gradientShift 8s ease infinite;
  }

  @keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  .image-placeholder.shimmer {
    background: linear-gradient(135deg, #e2e8f0, #f1f5f9);
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
      rgba(255, 255, 255, 0.4),
      transparent
    );
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { left: -100%; }
    100% { left: 100%; }
  }

  .placeholder-icon {
    font-size: 3rem;
    opacity: 0.5;
  }

  .loading-text {
    position: absolute;
    bottom: 12px;
    font-size: 0.85rem;
    color: #64748b;
    font-weight: 500;
  }

  .scenario-image {
    width: 100%;
    height: auto;
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .dialogue-box {
    background-color: #f0f0f0;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 20px;
    width: 100%;
  }

  .character-dialogue-jp {
    font-size: 1.5rem;
    font-weight: bold;
    margin: 0;
  }

  .character-dialogue-en {
    font-size: 1rem;
    color: #555;
    margin: 5px 0 0 0;
  }

  .user-prompt {
    font-size: 1.2rem;
    font-weight: 500;
    margin-bottom: 20px;
  }
</style>
