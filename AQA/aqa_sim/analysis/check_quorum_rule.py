# save as analysis/check_quorum_rule.py
print(f"{'k':>4} {'f':>3} {'Q_impl':>7} {'2Q-k':>6} {'need>f':>7} {'SAFE?':>7}")
print("-" * 42)
bad = 0
for k in [3,4,5,6,7,10,12,15,20,25,50]:
    f = (k - 1) // 3
    if f < 1: continue
    Q = min(max(2*f + 1, (k+f)//2 + 1), k)
    inter = 2*Q - k
    safe = inter > f
    if not safe: bad += 1
    print(f"{k:>4} {f:>3} {Q:>7} {inter:>6} {f:>7} {'YES' if safe else 'NO':>7}")
print(f"\nUnsafe configurations: {bad}")
print("Correct rule would be Q = floor((k+f)/2) + 1")