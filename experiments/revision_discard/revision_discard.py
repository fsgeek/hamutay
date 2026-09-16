#!/usr/bin/env python3
"""What is lost when most revisions of a file are discarded?

For a file with n revisions in git, keep a subset K under several policies and
measure what the discarded revisions contained that no kept revision does.

Units are non-blank lines (stripped). A line is *preserved* if it appears in any
kept revision. Lifetime of a line = number of revisions it appears in.

Policies:
  head_only     keep only the newest revision (the "throw it all away" oracle)
  random        keep round(p*n) revisions uniformly at random (many seeds)
  random+head   same, but the newest revision is always kept
  uniform       every (n/k)-th revision, newest always kept
  largest_diff  the k revisions with the largest change from their predecessor

Metrics (per kept set):
  content_loss       fraction of distinct lines ever present that no kept rev has
  char_loss          same, weighted by characters
  transient_loss     content_loss restricted to lines absent from HEAD
                     (the trimmings: things added and later removed)
  loss_L<bucket>     content_loss by lifetime bucket
  recon              mean over discarded revs of min over kept revs of
                     |symmetric difference| / |lines in discarded rev|
  bracket            mean over lines of the width, in revisions, of the interval
                     of kept revisions that brackets the line's first appearance
"""
import csv
import random
import subprocess
import sys
from collections import defaultdict
from statistics import mean

REPO, PATH = sys.argv[1], sys.argv[2]
P = float(sys.argv[3]) if len(sys.argv) > 3 else 0.10
SEEDS = int(sys.argv[4]) if len(sys.argv) > 4 else 200
OUT = sys.argv[5] if len(sys.argv) > 5 else None


def git(*args):
    return subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True, check=True).stdout


# Oldest -> newest, following renames.
log = git("log", "--follow", "--format=%H", "--name-only", "--", PATH).split("\n")
revs = []  # (sha, path-at-that-rev)
sha = None
for line in log:
    line = line.strip()
    if not line:
        continue
    if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
        sha = line
    else:
        revs.append((sha, line))
revs.reverse()  # oldest -> newest (git --follow does not combine with --reverse)

contents = []
for sha, path in revs:
    try:
        text = git("show", f"{sha}:{path}")
    except subprocess.CalledProcessError:
        continue
    contents.append([l.strip() for l in text.splitlines() if l.strip()])

n = len(contents)
k = max(1, round(P * n))
presence = defaultdict(set)
for i, lines in enumerate(contents):
    for l in set(lines):
        presence[l].add(i)
head_lines = set(contents[-1])
all_lines = list(presence)
first_seen = {l: min(s) for l, s in presence.items()}
lifetime = {l: len(s) for l, s in presence.items()}
BUCKETS = [(1, 1), (2, 3), (4, 9), (10, 21), (22, 10**9)]
# Resurrected: present, absent, present again (the author wanted it back)
resurrected = {l for l, s in presence.items() if max(s) - min(s) + 1 > len(s)}

diff_from_prev = [0] + [len(set(contents[i]) ^ set(contents[i - 1])) for i in range(1, n)]


def score(K):
    K = sorted(set(K))
    kept_lines = set()
    for i in K:
        kept_lines.update(contents[i])
    lost = [l for l in all_lines if l not in kept_lines]
    m = {}
    m["content_loss"] = len(lost) / len(all_lines)
    m["char_loss"] = sum(len(l) for l in lost) / sum(len(l) for l in all_lines)
    transient = [l for l in all_lines if l not in head_lines]
    m["transient_loss"] = (sum(1 for l in transient if l not in kept_lines) / len(transient)) if transient else 0.0
    for lo, hi in BUCKETS:
        b = [l for l in all_lines if lo <= lifetime[l] <= hi]
        m[f"loss_L{lo}-{hi if hi < 10**9 else 'max'}"] = (sum(1 for l in b if l not in kept_lines) / len(b)) if b else float("nan")
    m["resurrected_loss"] = (sum(1 for l in resurrected if l not in kept_lines) / len(resurrected)) if resurrected else float("nan")
    kept_sets = [set(contents[i]) for i in K]
    recon = []
    for i in range(n):
        if i in K:
            continue
        s = set(contents[i])
        recon.append(min(len(s ^ ks) for ks in kept_sets) / max(1, len(s)))
    m["recon"] = mean(recon) if recon else 0.0
    widths = []
    for l in all_lines:
        i = first_seen[l]
        after = [j for j in K if j >= i]
        before = [j for j in K if j < i]
        hi = after[0] if after else n
        lo = before[-1] if before else -1
        widths.append(hi - lo)
    m["bracket"] = mean(widths)
    return m


rows = []


def add(policy, seed, K):
    m = score(K)
    m.update(policy=policy, seed=seed, n=n, k=len(set(K)))
    rows.append(m)


add("head_only", 0, [n - 1])
stride = n / k
add("uniform", 0, sorted({n - 1 - int(round(j * stride)) for j in range(k)}))
add("largest_diff", 0, sorted(range(n), key=lambda i: -diff_from_prev[i])[:k])
for seed in range(SEEDS):
    rng = random.Random(seed)
    K = rng.sample(range(n), k)
    add("random", seed, K)
    K2 = rng.sample(range(n - 1), k - 1) + [n - 1] if k > 1 else [n - 1]
    add("random+head", seed, K2)

if OUT:
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

# Summary
print(f"{PATH}: n={n} revisions, k={k} kept (p={P}), {len(all_lines)} distinct lines, "
      f"{sum(1 for l in all_lines if l not in head_lines)} not in HEAD")
lt = sorted(lifetime.values())
print(f"resurrected lines (removed then restored): {len(resurrected)}")
print("lifetime distribution of lines (revisions present):",
      {f"L{lo}-{hi if hi < 10**9 else 'max'}": sum(1 for v in lt if lo <= v <= hi) for lo, hi in BUCKETS})
cols = ["content_loss", "char_loss", "transient_loss", "resurrected_loss", "recon", "bracket"] + [f"loss_L{lo}-{hi if hi < 10**9 else 'max'}" for lo, hi in BUCKETS]
print(f"{'policy':13s}" + "".join(f"{c[:14]:>15s}" for c in cols))
for policy in ["head_only", "uniform", "largest_diff", "random", "random+head"]:
    rs = [r for r in rows if r["policy"] == policy]
    line = f"{policy:13s}"
    for c in cols:
        vals = [r[c] for r in rs if r[c] == r[c]]
        if len(vals) > 1:
            lo, hi = sorted(vals)[int(0.05 * len(vals))], sorted(vals)[int(0.95 * len(vals)) - 1]
            line += f"{mean(vals):6.3f} [{lo:.2f},{hi:.2f}]"
        else:
            line += f"{vals[0]:15.3f}" if vals else f"{'nan':>15s}"
    print(line)
