import { describe, expect, it } from 'vitest';
import { render } from 'svelte/server';
import ScenarioStatus from './ScenarioStatus.svelte';

describe('ScenarioStatus', () => {
  it('renders beginner mode label + lives/score', () => {
    const { html } = render(ScenarioStatus, {
      props: { lives: 2, livesTotal: 3, score: 10, penaltyMessage: '', mode: 'beginner' }
    });
    expect(html).toContain('Time Stop • Planning');
    expect(html).toContain('Lives: 2/3');
    expect(html).toContain('Score: 10');
    expect(html).toMatch(/data-mode="beginner"/);
    expect(html).not.toContain('role="alert"');
  });

  it('renders advanced mode label', () => {
    const { html } = render(ScenarioStatus, {
      props: { lives: 1, livesTotal: 3, score: 0, penaltyMessage: '', mode: 'advanced' }
    });
    expect(html).toContain('Live • Streaming');
    expect(html).toMatch(/data-mode="advanced"/);
  });

  it('shows penalty banner when message present', () => {
    const { html } = render(ScenarioStatus, {
      props: { lives: 0, livesTotal: 3, score: 0, penaltyMessage: 'Try again.', mode: 'beginner' }
    });
    expect(html).toContain('Try again.');
    expect(html).toContain('role="alert"');
  });
});

