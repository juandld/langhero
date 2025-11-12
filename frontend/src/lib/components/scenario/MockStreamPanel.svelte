<script>
  export let streamingEnabled = false;
  export let streamMode = 'real';
  export let streamStatus = 'disabled';
  export let liveTranscript = '';
  export let streamEvents = [];
</script>

{#if streamingEnabled}
  <div class="mock-stream-panel">
    <div class="mock-stream-header">
      <span>{streamMode === 'mock' ? 'Mock Stream' : 'Streaming Debug'}</span>
      <span class={`mock-stream-status status-${streamStatus}`}>Status: {streamStatus}</span>
    </div>
    {#if liveTranscript}
      <div class="mock-stream-live">Live: <em>{liveTranscript}</em></div>
    {/if}
    <ul class="mock-stream-events">
      {#if streamEvents.length === 0}
        <li class="placeholder">No events yet. Start recording to stream chunks.</li>
      {:else}
        {#each [...streamEvents].reverse() as evt}
          <li>
            <code>{evt.event}</code>
            {#if evt.transcript}
              <span>{evt.transcript}</span>
            {:else if evt.message}
              <span>{evt.message}</span>
            {:else if evt.preview}
              <span>bytes: {evt.bytes} • preview: {evt.preview}</span>
            {/if}
          </li>
        {/each}
      {/if}
    </ul>
  </div>
{/if}

<style>
  .mock-stream-panel {
    width: 100%;
    margin-top: 24px;
    padding: 12px;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    background: #f9fafb;
  }

  .mock-stream-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-weight: 600;
    margin-bottom: 8px;
  }

  .mock-stream-status {
    font-size: 0.9rem;
    padding: 2px 8px;
    border-radius: 999px;
    background: #e5e7eb;
    color: #1f2937;
  }

  .mock-stream-live {
    margin-bottom: 8px;
    font-size: 0.95rem;
  }

  .mock-stream-events {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 180px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 0.85rem;
  }

  .mock-stream-events li {
    display: flex;
    gap: 8px;
    align-items: baseline;
  }

  .mock-stream-events code {
    background: #111827;
    color: white;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 0.75rem;
  }

  .mock-stream-events .placeholder {
    color: #6b7280;
    font-style: italic;
  }
</style>
