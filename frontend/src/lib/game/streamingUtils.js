/**
 * WebSocket streaming utilities for live game mode.
 * Handles real-time audio streaming and server communication.
 */

import { getBackendUrl } from '$lib/config';
import { getAuthToken } from '$lib/auth';

/**
 * Create a streaming connection for live mode
 */
export function createStreamConnection({
  mode = 'real',
  onReady,
  onPartial,
  onPenalty,
  onFinal,
  onError,
  onClose,
  onStatusChange,
}) {
  let socket = null;
  let status = 'idle';

  const setStatus = (newStatus) => {
    status = newStatus;
    onStatusChange?.(status);
  };

  const connect = (initPayload = {}) => {
    const backend = getBackendUrl();
    const path = mode === 'mock' ? '/stream/mock' : '/stream/interaction';
    const wsUrl = backend.replace(/^http/, backend.startsWith('https') ? 'wss' : 'ws') + path;

    try {
      const ws = new WebSocket(wsUrl);
      ws.binaryType = 'arraybuffer';
      setStatus('connecting');

      ws.onopen = () => {
        setStatus('open');
        const authToken = getAuthToken();
        const payload = { ...initPayload };
        if (authToken) {
          payload.auth_token = authToken;
        }
        try {
          ws.send(JSON.stringify(payload));
        } catch (err) {
          console.error('Stream init failed:', err);
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
        setStatus('error');
        onError?.();
      };

      ws.onclose = () => {
        if (status !== 'final') {
          setStatus('closed');
        }
        socket = null;
        onClose?.();
      };

      socket = ws;
    } catch (err) {
      console.error('Stream connection error:', err);
      setStatus('error');
      onError?.();
    }
  };

  const handleEvent = (data) => {
    if (!data || typeof data !== 'object') return;

    const evt = data.event;

    switch (evt) {
      case 'ready':
      case 'reset':
        setStatus('open');
        onReady?.(data);
        break;

      case 'partial':
        setStatus('streaming');
        onPartial?.(data);
        break;

      case 'penalty':
        setStatus('penalty');
        onPenalty?.(data);
        break;

      case 'final':
        setStatus('final');
        onFinal?.(data);
        break;

      case 'error':
        setStatus('error');
        onError?.(data);
        break;
    }
  };

  const sendChunk = async (blob) => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (!blob || !blob.size) return;

    try {
      const buffer = await blob.arrayBuffer();
      socket.send(buffer);
    } catch (err) {
      console.error('Stream send error:', err);
    }
  };

  const signalStop = (reason = 'stop') => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    try {
      socket.send(reason);
    } catch (err) {
      console.error('Stream stop error:', err);
    }
  };

  const close = (reason = 'cleanup') => {
    if (!socket) return;
    try {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(reason);
      }
      socket.close();
    } catch (err) {
      console.error('Stream close error:', err);
    } finally {
      socket = null;
    }
  };

  const isOpen = () => socket && socket.readyState === WebSocket.OPEN;
  const isConnecting = () => socket && socket.readyState === WebSocket.CONNECTING;
  const getStatus = () => status;

  return {
    connect,
    sendChunk,
    signalStop,
    close,
    isOpen,
    isConnecting,
    getStatus,
  };
}
