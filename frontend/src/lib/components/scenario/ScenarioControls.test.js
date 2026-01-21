import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import ScenarioControls from './ScenarioControls.svelte';

describe('ScenarioControls', () => {
  it('uses time-stop copy in beginner mode', () => {
    const { html } = render(ScenarioControls, {
      props: { isRecording: false, devMode: false, mode: 'beginner' }
    });
    expect(html).toContain('aria-label="Start high-stakes response recording"');
    expect(html).toContain('title="Record answer (rewind spent if wrong)"');
    expect(html).not.toContain('<canvas');
  });

  it('uses live streaming copy in advanced mode', () => {
    const { html } = render(ScenarioControls, {
      props: { isRecording: false, devMode: false, mode: 'advanced' }
    });
    expect(html).toContain('aria-label="Start live streaming answer"');
    expect(html).toContain('title="Start live mic (lives burn immediately)"');
  });

  it('shows wave canvas + stop copy when recording', () => {
    const { html } = render(ScenarioControls, {
      props: { isRecording: true, devMode: true, mode: 'advanced' }
    });
    expect(html).toMatch(/class="record-button[^"]*isRecording/);
    expect(html).toContain('aria-label="Stop live streaming answer"');
    expect(html).toContain('<canvas');
    expect(html).toContain('⟲ Back');
  });
});

