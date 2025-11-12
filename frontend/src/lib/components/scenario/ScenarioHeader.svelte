<script>
  export let imageUrl = '';
  export let dialogueJp = '';
  export let dialogueEn = '';
  export let description = '';
</script>

{#if imageUrl}
  <img
    src={imageUrl}
    alt="Scenario"
    class="scenario-image"
    on:error={(e) => e.currentTarget && (e.currentTarget.style.display = 'none')}
  />
{/if}

<div class="dialogue-box">
  <p class="character-dialogue-jp">{dialogueJp}</p>
  <p class="character-dialogue-en"><em>{dialogueEn}</em></p>
</div>

{#if description}
  <p class="user-prompt">{description}</p>
{/if}

<style>
  .scenario-image {
    width: 100%;
    height: auto;
    border-radius: 12px;
    margin-bottom: 20px;
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
