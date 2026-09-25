# Creator publish safety regression

Date: 2026-09-25. Viewport: 1920 × 1080. Standard Mode.

This is an isolated browser regression of the actual React Creator. Vite serves
the application on port 9002; Playwright intercepts every API request with local
mock responses and rejects requests to any other origin. It does not use the live
backend on port 9000 and does not claim real story publication or E2E completion.

**External paid media requests: 0.**

Run from `frontend/`:

```bash
node tests/publish_safety.mjs
```

The script owns and shuts down its isolated Vite server. It requires port 9002 to
be available and an installed Playwright Chromium browser.

## Reproduced defects

`before_fix.json` records five browser failures before the fix:

- Review available before the pending save completed.
- Failed save did not prevent publication.
- Newer server draft was published with an older review.
- An obsolete successful checklist was used without a fresh check.
- Same-tick clicks produced three publish requests, allowing duplicate sessions.

## Current result

`publish_safety.json`: **9 passed / 0 failed**. The above five cases pass, as do
changes arriving while the fresh check is in progress and Creator tab navigation
during an in-flight publish. A normalized saved draft converges without a reload
loop and can be published after a new manual review. Successful publication clears review; no test or
production path automatically checks the review checkbox.

The ninth case reproduces the hidden warning on a successful character-asset
check. `visual_warning_before_fix.json` records that failure. The repaired UI
shows a natural-language missing-image warning even when the gate is green,
keeps internal character IDs and `CANONICAL` out of Standard Mode, and allows
text publication after an explicit review. `text_publish_visual_warning.png`
shows that state. This case intercepts the publication request locally; it is
not evidence of another live publication.

The frontend now waits for the final queued save to succeed, reads the saved
draft, binds review and checklist to that draft, repeats the checklist immediately
before publication, and rejects intervening changes. A synchronous lock shared by
both publish actions survives Creator tab changes. Screenshots show the resulting
disabled/review-required states.

This protects the browser interaction. It is not a server-side multi-client
publication transaction or a claim that full-page reloads replay requests safely.
The formal backend publish gate still validates every request.
