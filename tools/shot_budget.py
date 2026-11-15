"""P-019 section 9: every per-video limit computed from the length M in minutes. The Doctor uses these as pass/fail.
python tools/shot_budget.py 10"""
import json, math, sys


def budget(minutes):
    M = float(minutes)
    return {
        'minutes': M,
        'shots': [round(M * 15), round(M * 20)],
        'shot_len_s': [1.5, 8.0],
        'avg_shot_s': [3.0, 4.0],
        'locations': [math.ceil(M * 4), math.ceil(M * 5)],
        'interrupt_gap_s': [12, 15],
        'chapters': [max(1, math.ceil(M * 60 / 90)), max(1, math.floor(M * 60 / 60))],
        'chapter_s': [60, 90],
        'hook_s': 8,
        'hook_min_shots': 3,
        'wpm': [125, 150],
        'lufs': -14.0,
        'true_peak_max': -1.5,
        'background_gap_s': 20,
        'jaccard_max': 0.30,
    }


if __name__ == '__main__':
    print(json.dumps(budget(sys.argv[1] if len(sys.argv) > 1 else 10), indent=1))
