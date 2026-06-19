# Phase 2 Code Review — IoT & Media Data Generators

Scope: `source/iot-simulator.py`, `source/media-uploader.py`, `source/seed-oltp.py`, `source/schema-oltp.sql`, `source/schemas/*`, `source/requirements.txt`.
Verdict: ship-ready with two HIGH fixes recommended pre-run.

## CRITICAL
None.

## HIGH

1. **Kafka outlier event will fail bronze `additionalProperties:false` validation when downstream tightens** — `iot-simulator.py:78-91` `build_event` emits **9 fields** (incl. `lat`, `lon`, `fw_version`). Schema `iot-event.schema.json:8` lists only 6 required, but `additionalProperties:false` is set. Today `lat/lon/fw_version` ARE declared in `properties`, so this passes — verified OK. **However**, since silver/PERMISSIVE will silently drop unknown fields rather than reject, and `value` has no `minimum/maximum`, the schema cannot catch the ±5σ outliers as schema-invalid (intended). Confirm Phase 5 detector is the only line of defense — flag this in phase-05 review. Severity HIGH because contract is load-bearing.

2. **`producer.flush(timeout=10)` may leave messages undelivered** — `iot-simulator.py:163`. At rate=50/s with `linger.ms=50` + `batch.size=64KB`, 10s flush is generous, but on a slow CI broker startup the timeout returns silently with messages still queued. Return value (number of remaining msgs) is ignored. Add `remaining = producer.flush(10); if remaining: LOG.error("flush timed out, %d undelivered", remaining); return 1`.

## MEDIUM

3. **`delivery_callback` only logs at WARNING — no counter / no non-zero exit** — `iot-simulator.py:108-110`. A pod with 100 % delivery failure prints noise and exits 0. POC is fine; production would lie. Acceptable for this slice; record as known.

4. **boto3 client thread-safety on `put_object`** — `media-uploader.py:142-157`. boto3 low-level clients ARE thread-safe (botocore docs explicit). Concurrency=4 + shared client is correct. No change needed — your concern (Q7) is over-cautious. Documentation-only.

5. **`make_video_bytes` reads whole MP4 into memory then re-uploads** — `media-uploader.py:94`. Fine at count=60 × ~50 KB. Not an issue at POC scale; would matter at >GB/run.

6. **Faker locale list quirk** — `seed-oltp.py:121` uses `Faker(["vi_VN"])` (list form) and `Faker.seed(args.seed)` (class-method). Faker 30 class-level seed seeds **all** generators across all locales — correct for determinism. The `faker` object is then never actually used (districts come from `HANOI_DISTRICTS` const, not Faker). Dead dependency on Faker for districts, but harmless — Faker is still useful as future hook. Could drop the param `faker` from `seed_locations` (cosmetic).

7. **`device_location.assigned_from` may pre-date `devices.install_date`** — `seed-oltp.py:101-110` picks `today - rand(0..365)`; devices install at `today - rand(30..720)`. About 4 % of pairs will have `assigned_from < install_date`. Logically broken (assigned before installed). Easy fix: clamp `assigned_from = max(install_date, today - rand(0..365))`. Currently silver joins will still work since no constraint enforces it.

## LOW

8. **`media-uploader.py:159` — `as_completed` consumed only for logging; exceptions in `fut.result()` will propagate and abort remaining futures without cancelling the pool** — at concurrency 4 with `ffmpeg` missing, you'd get one RuntimeError after `make_video_bytes` already ran in the main thread (it's called before `pool.submit`, not inside — line 153). Catch around the submit loop or `fut.result()` to log + count failures. Also: video bytes are built **synchronously in the main thread** (line 153), not on the pool — concurrency only helps uploads, not generation. Intentional? OK at count=60.

9. **PNG branch silently drops GPS/EXIF** (`media-uploader.py:68-70`). Correct technically (PNG uses tEXt/iTXt chunks, not EXIF APP1). Phase 4 metadata extractor must therefore handle PNG with no GPS — flag for phase-04 review.

10. **`build_s3_key` uses `taken_at` for partition path** (`media-uploader.py:99-103`) — fine, but `taken_at = now - rand(0..120min)` so on a run that straddles midnight UTC, half the objects land in yesterday's partition. Cosmetic for POC.

11. **`Producer` config missing `message.timeout.ms`** — `iot-simulator.py:94-105`. Defaults to 300s; combined with idempotence this can stall draining if broker is unreachable. Add `"message.timeout.ms": 30000`.

12. **`requirements.txt:10` lists `ffmpeg-python` but the code never imports it** — `media-uploader.py` shells out via `subprocess.run(["ffmpeg",…])` directly. Drop `ffmpeg-python==0.2.0` from the file, or actually use it. (Q-text mentions it twice; only the shell call is implemented.)

## Answers to user's targeted questions

| # | Q | Verdict |
|---|---|---|
| 1 | Device-id space alignment | ✅ All three default `--devices=100` → `dev-0000..dev-0099`. No off-by-one. Silver joins will match 100 %. |
| 2 | EXIF DMS round-trip | ✅ Sanity-checked math: seconds × 1000 stays well under uint32; rationals are valid piexif input. Pillow can read it. |
| 3 | Outlier honesty | ✅ 5σ × stddev = ±17.5 °C for temp, ±100 µg/m³ for pm25 — comfortably outside 3σ. ~1 % rate → ~30 outliers/min at rate=50. |
| 4 | Determinism | ✅ `Faker.seed()` seeds class-level shared RNG. Districts are constants, so Faker-driven non-determinism is moot in practice; OWNER_ORGS / DEVICE_MODELS use `rng` not Faker. Reproducible across runs at same seed. |
| 5 | Media idempotency | ⚠️ **Intentional accumulation** — confirm with operator. Each `make seed-media` writes fresh ULID keys; no overwrite, no dedup. Document explicitly in Makefile help or README that `make clean-hybrid` (or MinIO bucket purge) is the reset path. Not a defect — but undocumented surprise risk. |
| 6 | ffmpeg leakage | ✅ `shutil.which("ffmpeg")` guards only the video branch. Image-only runs (`--ratio 60:0`) work without ffmpeg. Document in Makefile target comment. |
| 7 | boto3 thread-safety | ✅ Shared client is fine for `put_object`. No change needed. |
| 8 | TRUNCATE CASCADE | ✅ Targets dev-local `postgres-oltp` Docker container; safe. README/Makefile should warn against pointing it at prod creds. |
| 9 | Env vs CLI precedence | ✅ CLI overrides env via `default=os.environ.get(...)` in argparse. Consistent across all three scripts. |
| 10 | First-run bombs | See HIGH #2 (flush silent timeout), MEDIUM #7 (FK-logical inversion), LOW #8 (ffmpeg-missing failure mode), LOW #11 (no message.timeout.ms). No Pillow EXIF tag missing — `piexif.GPSIFD.GPSLatitudeRef` etc. all exist in 1.1.3. JSON events always valid against schema by construction. |

## Recommended actions (priority order)

1. (HIGH-2) Capture `producer.flush()` return and exit non-zero if non-empty.
2. (MEDIUM-7) Clamp `device_location.assigned_from >= install_date`.
3. (LOW-11) Add `message.timeout.ms: 30000` to producer config.
4. (LOW-12) Remove unused `ffmpeg-python` from `requirements.txt`.
5. (Q5 doc) Add a one-line note to `media-uploader.py` docstring: "objects accumulate across runs; reset via MinIO bucket purge."

## Unresolved questions

- Q5: confirm with operator that media accumulation is intentional vs add a `--purge-prefix` flag.
- Phase 5 (silver) review must verify 3σ detector actually fires on the 5σ outliers and counts ≈ 1 % of stream.
- Phase 4 (media metadata) must handle PNG-without-EXIF and not blow up.
