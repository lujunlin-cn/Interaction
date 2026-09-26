# Opening failure and crawl readability — 2026-09-26

Baseline: `150c8384c321852a241eae2674c4974d6d685c1e`.

## Actual failure

The failed Biohazard opening `sess_00049_9cfbcf` successfully called the local Nemotron Director (5912 ms), Step 3.7 Narrative (16452 ms) and local Production Planner (4030 ms). Fal accepted the video job, but its result endpoint returned HTTP 422 `file_download_error` for reference image index 1, asset `ca_00016_628682`. The original CDN URL now returns 404 with a browser User-Agent (403 with a generic client). The adapter then incorrectly guessed a `/response` suffix, producing HTTP 405 and hiding the actual download error. See `original_failure.json`.

Nemotron was independently verified with `/models` and one direct inference. The configured Lightning model returned `服务正常` in 107 ms, using 25 input / 5 output tokens. This is a health measurement, not a Director latency benchmark; see `nemotron_probe.json`.

## Changes

- Preserve exact image bytes in a durable reference cache. Generated character images are archived after their Candidate record is saved. Archive failure retains the paid Candidate for recovery instead of silently losing it or generating another one.
- Fal image references are resolved to controlled public copies before any paid submit. Image order and identity mapping remain unchanged. Missing remote sources block the submit. Transport hashes/URLs are recorded in submission trace and scene provenance.
- Treat a completed Fal queue job with a 422 result as a failed generation, preserving a safe error category and reference index. Do not guess another result URL or expose echoed signed inputs.
- Restore 16 existing 4K references without new image generation. The expired canonical original was available locally and matches its historical SHA-256 exactly. Character versions, pinned asset IDs and published snapshots were not edited. All 16 controlled public URLs passed HTTP range-download checks.
- Enlarge opening crawl text from 15 px to responsive 24–44 px (36 px at 1440 px desktop width). Increase heading size and reduce perspective compression. Keep readable static scrolling for reduced-motion settings.
- Add a bottom-right `返回故事库` button beside `跳过前情`. Returning retains the session so the library can offer `继续当前游玩`.

## Validation

- Backend: **272 passed / 0 failed**, 96.34 seconds; `backend.txt`.
- Frontend: **PASS**; `frontend.txt`. Python compile and dependency checks also pass.
- Browser: desktop, phone and reduced-motion layouts, return/resume/skip, no overflow and zero navigation-triggered API writes: **PASS**; `browser.json` and screenshots. These layout checks use isolated fixtures and are not live media evidence.
- Public references: **16/16** accessible; `public_reference_checks.json`.
- Media submission error regression: covers expired sources, byte-preserving recovery, reference order, no paid submit on missing reference, truthful 422 handling and preservation of generated Candidates.

## Live verification and limits

An explicit Standard Player retry on the original failed session was blocked by the existing duplicate-submission guard, which retains the old submitted job ID. It created **zero** new H3 jobs. See `retry_failure.json`. This historical session still needs a separate job-reconciliation feature before it can directly retry; its history is preserved.

One fresh Session was then started through the actual Story Library `开始游玩` button to verify the repaired opening path. The new session is `sess_00027_85e25d`, based on the already published story. Only one H3 job is permitted for this verification, with 480P / 16:9 / 8 seconds. No automatic retry or recommended-branch media pre-generation is enabled. The provider has fetched all eight references from the controlled public URLs successfully; the queue remains `IN_PROGRESS` after the verification window; no second submission was made. The local service records the single job as recoverable and the same request can be resumed after Fal completes.

This is a targeted opening recovery check, not a new FULL E2E or a claim of character identity QA. Fal billing totals are not inferred from queue HTTP status.
