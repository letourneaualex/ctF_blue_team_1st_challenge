import random
import time
from payloads import ALL_PAYLOADS, HYGIENE_CHECKS

FLAG_THRESHOLDS = [
    (1,  "FLAG{f1r5t_bl00d_d3f3nd3r}"),
    (3,  "FLAG{g3tt1ng_th3_h4ng_0f_1t}"),
    (6,  "FLAG{bl03_t34m_v3t3r4n}"),
    (10, "FLAG{f0rtr3ss_m0d3_4ct1v4t3d}"),
]


def run_barrage():
    # 1. Hygiene checks (docker exec)
    hygiene_results = []
    for check in HYGIENE_CHECKS:
        try:
            hygiene_results.append(check())
        except Exception as e:
            hygiene_results.append({
                "id": check.__name__, "name": check.__name__,
                "type": "hygiene", "succeeded": False,
                "detail": f"Error: {e}"})

    # 2. Shuffle and fire network payloads
    shuffled = ALL_PAYLOADS[:]
    random.shuffle(shuffled)

    payload_results = []
    for fn in shuffled:
        try:
            result = fn()
        except Exception as e:
            result = {"id": fn.__name__, "name": fn.__name__,
                      "type": "unknown", "succeeded": False,
                      "detail": f"Error: {e}"}
        payload_results.append(result)
        time.sleep(random.uniform(0.1, 0.5))  # jitter

    # 3. Score
    # +1 per malicious payload blocked   (attacks_blocked)
    # -1 per legitimate payload that fails (legit_failed)
    # +1 per hygiene check that passes   (hyg_passed)
    # Fresh unpatched app: 0 blocked, 0 legit failed, 0 hygiene passed → score = 0
    # Perfect app: 10 + 0 + 5 = 15
    mal_blocked  = sum(1 for r in payload_results
                       if r["type"] == "malicious"  and not r["succeeded"])
    legit_failed = sum(1 for r in payload_results
                       if r["type"] == "legitimate" and not r["succeeded"])
    hyg_passed   = sum(1 for r in hygiene_results   if r["succeeded"])

    score = mal_blocked - legit_failed + hyg_passed
    flags = [f for t, f in FLAG_THRESHOLDS if score >= t]

    return {
        "score": score,
        "breakdown": {
            "mal_blocked":  mal_blocked,  "malicious_total": 10,
            "legit_failed": legit_failed, "legit_total":     15,
            "hyg_passed":   hyg_passed,   "hygiene_total":    5,
        },
        "flags": flags,
        "payload_results": payload_results,
        "hygiene_results": hygiene_results,
    }
