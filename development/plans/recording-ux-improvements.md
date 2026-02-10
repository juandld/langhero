# Recording UX Improvements Plan

## Problem Statement

The gameplay is fun but:
1. **Recording feedback is unclear** - Users don't know if recording is actually capturing audio
2. **Processing feels slow** - No visual indication during the evaluation wait (1-3 seconds)
3. **State transitions are subtle** - Only a red button color change indicates recording

## Current State Analysis

### What exists:
- Record button changes from orange → red when recording
- Wave canvas element exists but has **NO animation code** (it's static/empty)
- `evaluating` state shows only ellipsis text: `"Heard: {lastHeard}…"`
- Mic selector disables during recording (opacity change)

### Key code locations:
- `ScenarioControls.svelte` lines 31-95 (record button)
- `ScenarioControls.svelte` lines 61-62, 148-155 (empty wave canvas)
- `ScenarioDisplay.svelte` lines 541-627 (recording state management)
- `ScenarioDisplay.svelte` line 55 (`evaluating` flag)
- `ScenarioDisplay.svelte` line 982 (ellipsis display)
- `ScenarioStatus.svelte` (status strip)

## Proposed Improvements

### 1. Real-time Waveform Visualization (High Impact)

**Goal:** Show live audio levels while recording so users know their voice is being captured.

**Implementation:**
- Create `AudioContext` + `AnalyserNode` when recording starts
- Draw animated frequency bars on the existing wave canvas
- Animate at 60fps using `requestAnimationFrame`

**Visual design:**
- 20-30 vertical bars
- Height responds to audio frequency data
- Orange color matching the button theme
- Smooth transitions between frames

**Files to modify:**
- `ScenarioDisplay.svelte` - Add AudioContext setup in `toggleRecording()`
- `ScenarioControls.svelte` - Accept `analyser` prop and draw to canvas

### 2. Processing State Indicator (High Impact)

**Goal:** Make it obvious the system is processing after recording stops.

**Implementation:**
- Add pulse/breathe animation on record button when `evaluating = true`
- Show "Processing your response..." text in status area
- Optional: indeterminate progress bar below controls

**Visual design:**
- Button scales 0.95 → 1.05 with soft glow animation
- Status text appears with fade-in
- Subtle pulsing opacity on the button

**CSS animation:**
```css
@keyframes pulse-processing {
  0%, 100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(249, 115, 22, 0.4); }
  50% { transform: scale(1.05); box-shadow: 0 0 20px 10px rgba(249, 115, 22, 0.2); }
}
```

**Files to modify:**
- `ScenarioControls.svelte` - Add `evaluating` prop and CSS class
- `ScenarioDisplay.svelte` - Pass `evaluating` to controls
- `ScenarioStatus.svelte` - Add processing message slot

### 3. Recording Duration Display (Medium Impact)

**Goal:** Show how long the user has been recording.

**Implementation:**
- Start a timer when recording begins
- Display `0:03`, `0:04`, etc. near the record button
- Stop timer when recording stops

**Visual design:**
- Small monospace text below or beside the button
- Format: `MM:SS` or just seconds for short recordings

**Files to modify:**
- `ScenarioControls.svelte` - Add duration display element
- `ScenarioDisplay.svelte` - Manage timer state

### 4. State-Aware Status Strip (Medium Impact)

**Goal:** Make the status strip reflect current activity state.

**Implementation:**
- Add states: `idle` | `recording` | `processing` | `result`
- Different background colors or border accents per state
- Recording: pulsing red accent
- Processing: pulsing orange accent
- Result: green flash on success, red flash on penalty

**Files to modify:**
- `ScenarioStatus.svelte` - Accept `activityState` prop
- `ScenarioDisplay.svelte` - Compute and pass activity state

### 5. Audio Feedback Sounds (Low Impact, Nice-to-Have)

**Goal:** Subtle audio cues for state changes.

**Implementation:**
- Soft "boop" when recording starts
- Different tone when recording stops
- Reuse existing `playBeep()` function with different frequencies

**Files to modify:**
- `ScenarioDisplay.svelte` - Add calls in `toggleRecording()`

## Implementation Order

1. **Phase 1: Core feedback** (addresses "don't know if recording")
   - [ ] Waveform visualization
   - [ ] Processing pulse animation

2. **Phase 2: Enhanced clarity**
   - [ ] Recording duration display
   - [ ] Processing text message

3. **Phase 3: Polish**
   - [ ] Status strip state colors
   - [ ] Audio feedback sounds (optional)

## Technical Notes

### AudioContext Setup Pattern
```javascript
let audioContext = null;
let analyser = null;

function setupAudioAnalyser(stream) {
  audioContext = new (window.AudioContext || window.webkitAudioContext)();
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 64;

  const source = audioContext.createMediaStreamSource(stream);
  source.connect(analyser);

  return analyser;
}
```

### Canvas Drawing Pattern
```javascript
function drawWaveform(canvas, analyser) {
  if (!canvas || !analyser) return;

  const ctx = canvas.getContext('2d');
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);

  function draw() {
    if (!isRecording) return;
    requestAnimationFrame(draw);

    analyser.getByteFrequencyData(dataArray);

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const barWidth = canvas.width / bufferLength;
    let x = 0;

    for (let i = 0; i < bufferLength; i++) {
      const barHeight = (dataArray[i] / 255) * canvas.height;
      ctx.fillStyle = '#f97316';
      ctx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);
      x += barWidth;
    }
  }

  draw();
}
```

## Success Metrics

- User can clearly see audio levels while speaking
- Processing state is unmistakably visible
- Total visual feedback gap between "stop recording" and "see result" feels active, not idle

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| AudioContext browser compatibility | Use feature detection; fallback to static indicator |
| Performance on low-end devices | Throttle animation to 30fps if needed |
| Canvas resize issues | Use fixed dimensions, handle container resize |

## References

- Current UX vision: `development/ux.md`
- Scenario progression: `development/scenario-progression.md`
- Streaming architecture: `development/streaming-plan.md`
