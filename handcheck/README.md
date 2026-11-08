# Hand check of the 558 early drop-off posts (7 Nov 2026)

The discovery engine counted 558 early drop-off moments in public posts. To test that number directly, 40 of the
558 were drawn at random (seed 20261107) and labelled by hand in `handcheck.html`, without the engine's label shown.

- `sample.json`: the 40 posts, with the engine's own label for each
- `labels.txt`: the hand labels, one letter per post (V stop or thinking of it, F failed debit, P paused, N not a drop-off).
  Post 1 was changed from N to V on a second read.
- `score.py`: prints the results below

| Result | Value |
| --- | --- |
| Real drop-off moments | 15 of 40 (38%, likely range 24% to 53%) |
| Likely true count in the 558 | about 135 to 300 |
| Among the 15: stopping or thinking of it / failed debit / paused | 9 / 5 / 1 |
| Failed debits among real drop-offs | 33% (likely range 15% to 58%), against 8% in the engine's count |
| Engine agrees with the exact hand label | 12 of 40 |

The engine's main mistake is reading "which fund should I pick?" as "thinking of stopping". All 4 posts it called
failed debits really were. So the 558 is a ceiling, and shares built on it are directional.
