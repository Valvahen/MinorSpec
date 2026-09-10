"""Verify Theorem 1 numerically: does Q > (k+f)/2 guarantee 2Q-k > f?

Also verifies the implementation formula satisfies the condition.
"""
failures_theorem = []
failures_impl = []

for n in range(4, 101):
    for f in range(1, (n - 1) // 3 + 1):        # all valid f < n/3
        for k in range(2 * f + 1, n + 1):        # active set sizes
            # --- Check the theorem's condition implies agreement ---
            Q_min_theory = (k + f) // 2 + 1      # smallest Q satisfying Q > (k+f)/2
            if not (2 * Q_min_theory - k > f):
                failures_theorem.append((n, f, k, Q_min_theory, 2*Q_min_theory - k))

            # --- Check OUR implementation formula ---
            Q_impl = min(max(2 * f + 1, (k + f) // 2 + 1), k)
            if not (2 * Q_impl - k > f):
                failures_impl.append((n, f, k, Q_impl, 2*Q_impl - k))

print("=" * 60)
print("  THEOREM 1 VERIFICATION")
print("=" * 60)
print(f"Theorem condition failures: {len(failures_theorem)}")
if failures_theorem:
    for c in failures_theorem[:10]:
        print(f"  n={c[0]} f={c[1]} k={c[2]} Q={c[3]}: 2Q-k={c[4]}, need > {c[1]}")

print(f"Implementation formula failures: {len(failures_impl)}")
if failures_impl:
    for c in failures_impl[:10]:
        print(f"  n={c[0]} f={c[1]} k={c[2]} Q={c[3]}: 2Q-k={c[4]}, need > {c[1]}")

if not failures_theorem and not failures_impl:
    print("\n  BOTH VERIFIED: theorem holds and implementation satisfies it.")
print("=" * 60)