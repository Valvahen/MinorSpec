"""Numerically verify the safety bound in Theorem 1.

Checks: for all valid (n, f, k, Q), does |S1 ∩ S2| >= 2Q - k > f hold?
If any case fails, the theorem as stated is wrong.
"""

print(f"{'n':>4} {'f':>3} {'k':>4} {'Q':>4} | {'2Q-k':>6} | {'> f?':>6}")
print("-" * 44)

failures = []
for n in range(4, 61):                    # group sizes
    f = (n - 1) // 3                      # max Byzantine: f < n/3
    if f < 1:
        continue
    for k in range(2 * f + 1, n + 1):     # active set: 2f+1 <= k <= n
        for Q in range(2 * f + 1, k + 1): # quorum: 2f+1 <= Q <= k
            intersection = 2 * Q - k
            ok = intersection > f
            if not ok:
                failures.append((n, f, k, Q, intersection))

if failures:
    print(f"\n*** {len(failures)} FAILING CASES FOUND ***")
    for case in failures[:20]:
        n, f, k, Q, inter = case
        print(f"n={n} f={f} k={k} Q={Q}: 2Q-k = {inter}, need > {f}  <-- FAILS")
    print(f"\nTheorem as stated is NOT universally true.")
else:
    print("No failures. 2Q-k > f holds for all valid (n,f,k,Q).")

# Show the tightest cases (smallest margin)
print("\nTightest cases (smallest margin above f):")
tight = []
for n in range(4, 31):
    f = (n - 1) // 3
    if f < 1: continue
    for k in range(2*f+1, n+1):
        for Q in range(2*f+1, k+1):
            margin = (2*Q - k) - f
            tight.append((margin, n, f, k, Q, 2*Q-k))
tight.sort()
for margin, n, f, k, Q, inter in tight[:10]:
    print(f"  n={n:2d} f={f} k={k:2d} Q={Q:2d}: 2Q-k={inter:2d}, f={f}, margin={margin:+d}")