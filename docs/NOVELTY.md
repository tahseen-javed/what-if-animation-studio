# Novelty metrics (P-019 sections 1-2)

## Video DNA (tools/dna.py)
- 15 dimensions: palette, lighting, camGrammar, transitionSet, titleLook, uiSkin, optionCard, music, moodArc, ambience,
  pacing, intensity, outfit, theme, colourScript.
- Distance between two videos = normalized Hamming distance = (dimensions that differ) / 15.
- Gate: differ from each of the last 50 videos in >= 6 dimensions AND distance >= 0.40 from ALL earlier videos.
  Up to 2000 resamples; if none passes, the most distant candidate is kept and the Doctor reports `dna_novelty` as FAIL.

## Shot tuples (tools/director.py, registry/shots/<video>.json)
- Tuple = (set, angle, light, pose, camera move, prop, transition); expression follows the pose.
- No tuple repeats inside a video. Consecutive shots never share an angle. A set never returns within 20 s after the
  scene that used it ends.
- Combo cap N: the same (set, angle, camera move) may appear at most N times across the last 100 videos, with
  N = max(3, ceil(2 x shots_per_video x 100 / (cast_sets x angles x camera_moves))). With the Phase 1 library
  (7 cast sets, 10 angles, 15 moves) and a 1-minute video N = 4; for a 10-minute video N = 34. N falls automatically as
  the library grows (60 sets x 10 x 50 moves gives N = 3 for 10-minute videos).
- Jaccard similarity of a video's tuple set against every earlier video must stay below 0.30 (calibrate with owner ratings).

## Planned (Phase 3)
- Perceptual diversity: OpenCLIP frame embeddings vs the last 100 videos (licence to be checked before use).
- Distinct-looking locations measured by embeddings; near-duplicate set variants dropped.
