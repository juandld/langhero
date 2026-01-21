# `/demo` Smoke Checklist (M4)

Use this as a quick manual sanity check for the mode-toggle HUD (beginner time-stop vs advanced streaming).

## Setup

1. Start backend + frontend (one terminal):
   - `./dev.sh`
2. Open the demo route:
   - `http://localhost:5173/demo`
3. (Optional) Try story import:
   - `http://localhost:5173/import`

Optional URL flags:
- `?dev=1` shows the back button (separate from the Dev Tools dock toggle).
- `?stream=real|mock|off` sets streaming mode for advanced scenarios.

## Beginner (Scenario 1)

1. Click **Beginner (Scenario 1)**.
2. Confirm the status strip shows **Time Stop • Planning** and lives/score render.
3. Confirm the prep banner reads **Time Stop tools — experiment safely here…**.
4. Confirm **Judge focus** slider is present; set it to **Learning-first**.
5. Confirm **Target language** dropdown is present (Auto/English/Spanish/Japanese). Leave on Auto.
4. Click a suggested phrase chip (or a quick option if present) and confirm the “Say this” panel appears with the selected line.
5. Click **Translate** (with text entered) or **🎤 Speak** and confirm these tools do not decrement lives (no penalty banner).

## Advanced (Scenario 4)

1. Click **Advanced (Scenario 4)**.
2. Confirm the status strip shows **Live • Streaming** and lives/score render.
3. Confirm the prep banner reads **Live mode tools — translator + make-your-own stay safe…**.
4. Set **Judge focus** to **Story-first** and confirm language mismatch penalties are less aggressive (in real runs; mock stream does not enforce).
5. Set **Target language** override to something different and confirm it changes the “stay in X” live-mode copy.
4. With `?stream=mock`, start the mic and confirm:
   - status switches to live/streaming states (if backend is running),
   - partial transcript updates show up in the mock stream panel,
   - final event updates deltas (score/lives) and clears penalty banner on success.
5. With `?stream=off`, confirm the page calls out streaming-disabled and the flow falls back to time-stop behavior.

## Notes

- Any penalties should surface as a red banner under the status strip.
- Use `./tests/test.sh` plus `npm run test:run` (in `frontend/`) before hand-off.
- Or run both via `bash tests/test_all.sh`.
