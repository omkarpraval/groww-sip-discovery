"""Hand check of the 558 early drop-off posts: 40 posts drawn at random (seed 20261107), labelled by hand.

labels.txt holds one letter per post, in the order of sample.json:
  V = stopping or thinking of stopping (also stopped, reduced, redeemed)   F = failed debit
  P = paused or skipped                                                     N = not a drop-off at all
Run: python handcheck/score.py
"""
import collections
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MAP = {"considering_stop": "V", "stopped_or_cancelled": "V", "reduced": "V", "redeemed": "V",
       "failed_involuntary": "F", "paused_or_skipped": "P"}


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(100 * (c - h)), round(100 * (c + h))


S = json.load(open(os.path.join(HERE, "sample.json"), encoding="utf-8"))
H = open(os.path.join(HERE, "labels.txt")).read().strip().split(":")[1]
E = [MAP.get(x["engine"]["sip_action"] if isinstance(x["engine"], dict) else x["engine"], "N") for x in S]
assert len(S) == len(H) == 40
c = collections.Counter(H)
real = len(H) - c["N"]
print("human labels:", dict(c))
print(f"real drop-offs: {real} of 40 ({100 * real / 40:.1f}%), 95% range {wilson(real, 40)}%")
print(f"likely true count in the 558: {round(558 * wilson(real, 40)[0] / 100)} to {round(558 * wilson(real, 40)[1] / 100)}")
print(f"among real drop-offs: stop {c['V']}, failed debit {c['F']} ({100 * c['F'] / real:.0f}%, range {wilson(c['F'], real)}%), paused {c['P']}")
print("engine agrees with the hand label on", sum(a == b for a, b in zip(E, H)), "of 40")
