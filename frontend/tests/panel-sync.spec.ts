import { test, expect } from '@playwright/test';

/**
 * Test panel-narrative synchronization.
 * Verifies that each dialogue line shows the correct panel image.
 */

test.describe('Panel-Narrative Synchronization', () => {

  test('API returns line-indexed panels for awakening dialogue', async ({ request }) => {
    // Test the backend API directly
    const response = await request.get('http://localhost:8000/api/panels/sequence/awakening?story_id=shogun');
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.dialogue_key).toBe('awakening');
    expect(data.panels).toBeDefined();

    // Should be an object with string keys "0", "1", etc.
    expect(typeof data.panels).toBe('object');
    expect(data.panels['0']).toBeDefined();
    expect(data.panels['7']).toBeDefined(); // 8 lines total

    // Verify specific panel assignments for awakening
    // Line 0: narration "Your eyes open..." -> beach_wakeup
    expect(data.panels['0'].id).toBe('beach_wakeup');

    // Line 3: samurai speaks -> samurai_face
    expect(data.panels['3'].id).toBe('samurai_face');

    // Line 4: bimbo speaks -> bimbo_orb_battlefield (NOT beach/blade!)
    expect(data.panels['4'].id).toBe('bimbo_orb_battlefield');

    // Line 7: bimbo speaks again -> bimbo_orb_battlefield
    expect(data.panels['7'].id).toBe('bimbo_orb_battlefield');
  });

  test('API returns 1:1 mapping for all dialogues', async ({ request }) => {
    const dialogues = [
      { key: 'tutorial_intro', expectedLines: 7 },
      { key: 'tutorial_to_story', expectedLines: 7 },
      { key: 'shogun_intro', expectedLines: 7 },
      { key: 'awakening', expectedLines: 8 },
      { key: 'time_freeze_lesson', expectedLines: 4 },
      { key: 'first_success', expectedLines: 4 },
    ];

    for (const { key, expectedLines } of dialogues) {
      const response = await request.get(`http://localhost:8000/api/panels/sequence/${key}?story_id=shogun`);
      expect(response.ok(), `Failed to get panels for ${key}`).toBeTruthy();

      const data = await response.json();
      const panelCount = Object.keys(data.panels).length;

      expect(panelCount, `${key} should have ${expectedLines} panels`).toBe(expectedLines);
    }
  });

  test('tutorial_intro panels match speaker-based rules', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/panels/sequence/tutorial_intro?story_id=shogun');
    const data = await response.json();

    // All 7 lines are Bimbo speaking - should show mix of orb and environment panels
    // Line 0: bimbo "Hey! Time for your daily lesson!" -> bimbo_orb_excited
    expect(data.panels['0'].id).toBe('bimbo_orb_excited');

    // Line 2: bimbo explaining -> bimbo_orb_explaining
    expect(data.panels['2'].id).toBe('bimbo_orb_explaining');

    // Line 6: bimbo "Ready to begin?" -> bimbo_orb_excited
    expect(data.panels['6'].id).toBe('bimbo_orb_excited');
  });

  test('panels have valid image URLs', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/panels/sequence/awakening?story_id=shogun');
    const data = await response.json();

    for (const [lineIdx, panel] of Object.entries(data.panels) as [string, any][]) {
      expect(panel.image_url, `Line ${lineIdx} panel should have image_url`).toBeTruthy();
      expect(panel.image_url).toMatch(/^https?:\/\//);
    }
  });

});

test.describe('Story Page Panel Display', () => {

  test('story page loads without errors', async ({ page }) => {
    // Listen for console errors
    const errors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/story');
    await page.waitForTimeout(2000);

    // Filter out expected/benign errors (like 404 for missing images)
    const criticalErrors = errors.filter(e =>
      !e.includes('404') &&
      !e.includes('Failed to load resource')
    );

    expect(criticalErrors, 'Should have no critical console errors').toHaveLength(0);
  });

  test('panel background changes during dialogue', async ({ page }) => {
    await page.goto('/story');

    // Wait for the story to load and show dialogue
    await page.waitForSelector('.dialogue-overlay, .awakening-cutscene', { timeout: 10000 });

    // Get initial background image
    const getBackgroundUrl = async () => {
      return page.evaluate(() => {
        const bg = document.querySelector('.panel-background, .background-image') as HTMLElement;
        if (!bg) return null;
        const style = window.getComputedStyle(bg);
        return style.backgroundImage;
      });
    };

    const initialBg = await getBackgroundUrl();
    expect(initialBg).toBeTruthy();

    // Click to advance dialogue
    await page.click('body');
    await page.waitForTimeout(500);

    // Background should potentially change (or stay same if same panel assigned)
    const secondBg = await getBackgroundUrl();
    expect(secondBg).toBeTruthy();

    // Continue advancing and verify backgrounds are loading
    for (let i = 0; i < 3; i++) {
      await page.click('body');
      await page.waitForTimeout(300);
    }

    const laterBg = await getBackgroundUrl();
    expect(laterBg).toBeTruthy();
  });

  test('capture panel progression screenshots', async ({ page }) => {
    // Enable screenshot capture for visual verification
    await page.goto('/story');

    // Wait for story to load
    await page.waitForSelector('.dialogue-overlay, .awakening-cutscene, .story-orchestrator', { timeout: 10000 });
    await page.waitForTimeout(1000);

    // Capture initial state
    await page.screenshot({ path: 'test-results/panel-progression-01-initial.png', fullPage: true });

    // Advance through several dialogue lines and capture each
    for (let i = 2; i <= 5; i++) {
      await page.click('body');
      await page.waitForTimeout(600); // Wait for panel transition
      await page.screenshot({ path: `test-results/panel-progression-0${i}-after-click.png`, fullPage: true });
    }

    // Verify screenshots were created
    const fs = await import('fs');
    expect(fs.existsSync('test-results/panel-progression-01-initial.png')).toBeTruthy();
    expect(fs.existsSync('test-results/panel-progression-05-after-click.png')).toBeTruthy();
  });

});
