# Contributing to Ghostmark

Thanks for looking. Small, focused changes are the easiest to review.

## Ways to help
* **Test photos and results:** run the Python or JavaScript reader on your own photos and open an issue with what failed (no need to share the photo, a z-score and the edit you applied are enough).
* **Bug reports:** use the issue template. Say which engine (Android, Python, JavaScript) and the status you got (`ok`, `part`, `damaged`, `none`).
* **Code:** Kotlin engine in `engine/`, Python engine in `python/`, JavaScript reference in `reference/`.

## The one rule: the three engines must stay compatible
`reference/wm-engine.js` defines the mark format. A change to the format needs a new format version and a note in `engine/FORMAT-SPEC.md`. A change inside one engine must not change what it writes or how it reads existing marks.

## Run the tests
```bash
cd python && pip install -e .[test] && pytest -q          # 14 tests
./gradlew :engine:testDebugUnitTest                         # 29 tests (Android SDK needed)
```

## Pull requests
1. Fork, branch, keep the change small.
2. Add or update a test.
3. Do not commit generated media unless the change is about the media (`tools/` rebuilds it).
4. By contributing you agree that your contribution is licensed under Apache-2.0 (see `LICENSE`).
