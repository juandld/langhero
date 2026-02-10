/**
 * Streaming Manager for real-time game interactions.
 *
 * Manages WebSocket connections for live speech-to-text streaming
 * and game state updates. Used by GameView and ScenarioDisplay.
 */

import { writable, get } from 'svelte/store';
import { getBackendUrl } from '$lib/config';
import { getAuthToken } from '$lib/auth';
import { playBeep } from './audioUtils';

/**
 * Stream status values
 * @type {'disabled' | 'connecting' | 'open' | 'streaming' | 'penalty' | 'final' | 'error' | 'closed'}
 */

/**
 * Create a streaming manager instance.
 * Each component should create its own instance.
 *
 * @param {Object} options
 * @param {Function} options.getScenario - Function to get current scenario
 * @param {Function} options.getLanguage - Function to get effective target language
 * @param {Function} options.getGameState - Function to get { score, lives, livesTotal, judgeFocus }
 * @param {Function} options.onStateUpdate - Callback for state updates (lives, score, etc.)
 * @param {Function} options.onTranscript - Callback for transcript updates
 * @param {Function} options.onResult - Callback for final result
 * @param {Function} options.onPenalty - Callback for penalty events
 * @param {Function} options.onError - Callback for errors
 */
export function createStreamingManager(options = {}) {
  const {
    getScenario = () => null,
    getLanguage = () => 'Japanese',
    getGameState = () => ({ score: 0, lives: 3, livesTotal: 3, judgeFocus: 0 }),
    onStateUpdate = () => {},
    onTranscript = () => {},
    onResult = () => {},
    onPenalty = () => {},
    onError = () => {},
  } = options;

  // Reactive stores
  const status = writable('disabled');
  const events = writable([]);
  const transcript = writable('');

  // Internal state
  let socket = null;
  let enabled = false;
  let mode = 'real'; // 'real' | 'mock'

  /**
   * Enable or disable streaming.
   */
  function setEnabled(value) {
    enabled = Boolean(value);
    if (!enabled) {
      close('disabled');
    }
  }

  /**
   * Set stream mode ('real' or 'mock').
   */
  function setMode(value) {
    mode = value === 'mock' ? 'mock' : 'real';
  }

  /**
   * Ensure WebSocket connection is established.
   */
  function connect() {
    if (!enabled) return;
    if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const backend = getBackendUrl();
    const path = mode === 'mock' ? '/stream/mock' : '/stream/interaction';
    const wsUrl = backend.replace(/^http/, backend.startsWith('https') ? 'wss' : 'ws') + path;

    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      status.set('connecting');
      events.set([]);

      ws.onopen = () => {
        status.set('open');
        const scenario = getScenario();
        const authToken = getAuthToken();
        const gameState = getGameState();

        const payload = {
          scenario_id: scenario?.id ?? null,
          language: getLanguage(),
          judge: gameState.judgeFocus,
          score: gameState.score,
          lives_total: gameState.livesTotal,
          lives_remaining: gameState.lives,
        };

        // Support vocab mode: pass expected_response directly
        if (scenario?.expected_response) {
          payload.expected_response = scenario.expected_response;
        }
        // Free-speak mode: pass all expected responses
        if (scenario?.expected_responses) {
          payload.expected_responses = scenario.expected_responses;
        }

        if (authToken) {
          payload.auth_token = authToken;
        }

        try {
          ws.send(JSON.stringify(payload));
        } catch (err) {
          console.error('[Stream] init failed', err);
        }
      };

      ws.onmessage = (event) => {
        let data;
        try {
          data = typeof event.data === 'string'
            ? JSON.parse(event.data)
            : JSON.parse(new TextDecoder().decode(event.data));
        } catch (err) {
          return;
        }
        handleEvent(data);
      };

      ws.onerror = () => {
        status.set('error');
        onError(new Error('WebSocket error'));
      };

      ws.onclose = () => {
        const currentStatus = get(status);
        if (currentStatus !== 'final') {
          status.set('closed');
        }
        socket = null;
      };

      socket = ws;
    } catch (err) {
      console.error('[Stream] connection error', err);
      status.set('error');
      onError(err);
    }
  }

  /**
   * Send an audio chunk to the stream.
   */
  async function sendChunk(blob) {
    if (!enabled) return;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (!blob || !blob.size) return;

    try {
      const buffer = await blob.arrayBuffer();
      socket.send(buffer);
    } catch (err) {
      console.error('[Stream] send error', err);
    }
  }

  /**
   * Signal the stream to stop (but keep connection open).
   */
  function signalStop(reason = 'stop') {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    try {
      socket.send(reason);
    } catch (err) {
      console.error('[Stream] stop signal error', err);
    }
  }

  /**
   * Close the stream connection.
   */
  function close(reason = 'cleanup') {
    if (!socket) return;
    try {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(reason);
      }
      socket.close();
    } catch (err) {
      console.error('[Stream] close error', err);
    } finally {
      socket = null;
    }
  }

  /**
   * Handle incoming stream events.
   */
  function handleEvent(data) {
    if (!data || typeof data !== 'object') return;

    // Keep last 20 events for debugging
    events.update(evts => [...evts.slice(-19), data]);

    const evt = data.event;

    // Ready/Reset - initial state sync
    if (evt === 'ready' || evt === 'reset') {
      status.set('open');
      onStateUpdate({
        livesTotal: typeof data.lives_total === 'number' ? Math.max(1, data.lives_total) : undefined,
        lives: typeof data.lives_remaining === 'number' ? data.lives_remaining : undefined,
        score: typeof data.score === 'number' ? Math.max(0, data.score) : undefined,
        runLivesInitialized: true,
        penaltyMessage: '',
      });
      return;
    }

    // Partial transcript
    if (evt === 'partial') {
      status.set('streaming');
      const text = data.transcript || '';
      transcript.set(text);
      onTranscript(text);
      return;
    }

    // Penalty (wrong language, etc.)
    if (evt === 'penalty') {
      status.set('penalty');
      const stateUpdate = {
        penaltyMessage: data.message || 'Try that again in the target language.',
      };

      if (typeof data.lives_total === 'number') {
        stateUpdate.livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        stateUpdate.lives = Math.max(0, data.lives_remaining);
      } else if (typeof data.lives_delta === 'number') {
        stateUpdate.livesDelta = data.lives_delta;
      }
      if (typeof data.score === 'number') {
        stateUpdate.score = data.score;
      }

      playBeep({ frequency: 420, duration: 160 });
      onStateUpdate(stateUpdate);
      onPenalty(data);
      return;
    }

    // Final result
    if (evt === 'final') {
      status.set('final');
      const text = data?.result?.heard || get(transcript);
      transcript.set(text);

      const stateUpdate = { penaltyMessage: '' };
      if (typeof data.score === 'number') {
        stateUpdate.score = data.score;
      }
      if (typeof data.lives_total === 'number') {
        stateUpdate.livesTotal = Math.max(1, data.lives_total);
      }
      if (typeof data.lives_remaining === 'number') {
        stateUpdate.lives = Math.max(0, data.lives_remaining);
      }

      onStateUpdate(stateUpdate);
      onResult(data?.result || {}, { fromStream: true });
      return;
    }

    // Error
    if (evt === 'error') {
      status.set('error');
      onError(new Error(data.message || 'Stream error'));
      return;
    }

    // Info event (ScenarioDisplay specific)
    if (evt === 'info') {
      // Just log for debugging
      return;
    }
  }

  /**
   * Check if streaming is currently enabled.
   */
  function isEnabled() {
    return enabled;
  }

  /**
   * Check if socket is connected.
   */
  function isConnected() {
    return socket && socket.readyState === WebSocket.OPEN;
  }

  return {
    // Stores (subscribe to these)
    status,
    events,
    transcript,

    // Methods
    setEnabled,
    setMode,
    connect,
    sendChunk,
    signalStop,
    close,
    isEnabled,
    isConnected,
  };
}
