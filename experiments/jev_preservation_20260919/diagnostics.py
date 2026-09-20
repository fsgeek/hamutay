"""Post-hoc diagnostics for REPORT.md: deletion clustering by cycle, cluster-bootstrap CIs
for AUC, Jev repeat noise on identical inputs (60 extra calls, persisted to jev_raw_repeat.jsonl).
Run: uv run --with typesafe-sdk python experiments/jev_preservation_20260919/diagnostics.py
"""
import json, time, random
from pathlib import Path
from collections import Counter
import numpy as np
from sklearn.metrics import roc_auc_score
HERE = Path(__file__).resolve().parent
L = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); L.append(s)
def load(p): return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

rows = load(HERE / "rows_elder.jsonl"); raw = load(HERE / "jev_raw_elder.jsonl")
jev1 = np.array([r["response"]["answers"]["keep_1"]["noul"] for r in raw])
jev10 = np.array([r["response"]["answers"]["keep_10"]["noul"] for r in raw])
cent = np.array([r["response"]["answers"]["centrality"]["score"] for r in raw])
cyc = np.array([r["cycle"] for r in rows])

P("## Elder: where do non-survivals happen? (per sampled cycle: n entries, n lost by c+1, by c+10, n unstable by c+10)")
lost1 = Counter(); lost10 = Counter(); unst = Counter(); n = Counter()
for r in rows:
    n[r["cycle"]] += 1; lost1[r["cycle"]] += 1 - r["survive_1"]; lost10[r["cycle"]] += 1 - r["survive_10"]; unst[r["cycle"]] += 1 - r["stable_10"]
tot1 = sum(lost1.values()); tot10 = sum(lost10.values())
P(f"total lost@1={tot1} lost@10={tot10} unstable@10={sum(unst.values())} over {len(n)} cycles")
top = sorted(lost10.items(), key=lambda x: -x[1])[:8]
P("cycles with most loss@10 (cycle: lost/n):", ", ".join(f"{c}: {lost10[c]}/{n[c]}" for c, _ in top))
P(f"share of all loss@10 in the top 3 cycles: {sum(v for _, v in top[:3])/max(tot10,1):.3f}; cycles with zero loss@10: {sum(1 for c in n if lost10[c]==0)}/{len(n)}")
P("cycles with loss@1 (cycle: lost/n):", ", ".join(f"{c}: {lost1[c]}/{n[c]}" for c in sorted(n) if lost1[c]))
P("per-cycle n_entries:", ", ".join(f"{c}:{n[c]}" for c in sorted(n)))

P("\n## Which keys are lost? (survive_10=0, elder) key -> count of (cycle) rows lost, with age at loss")
lostkeys = Counter(); ages = {}
for r in rows:
    if not r["survive_10"]:
        lostkeys[r["key"]] += 1; ages.setdefault(r["key"], []).append(r["age"])
P(", ".join(f"{k}({v}; age {min(ages[k])}-{max(ages[k])})" for k, v in lostkeys.most_common(25)))
P(f"distinct keys lost@10: {len(lostkeys)}; mean age of lost rows={np.mean([a for v in ages.values() for a in v]):.1f} vs all rows={np.mean([r['age'] for r in rows]):.1f}")

P("\n## Cluster bootstrap (by cycle, 2000 resamples) 95% CI for AUC, elder")
rng = np.random.default_rng(0); cycles = sorted(set(cyc))
def boot_auc(y, p):
    aucs = []
    for _ in range(2000):
        pick = rng.choice(cycles, len(cycles), replace=True)
        idx = np.concatenate([np.where(cyc == c)[0] for c in pick])
        if 0 < y[idx].mean() < 1: aucs.append(roc_auc_score(y[idx], p[idx]))
    return np.percentile(aucs, [2.5, 97.5]), np.mean(aucs)
for label, p, nm in (("survive_1", jev1, "keep_1"), ("survive_10", jev10, "keep_10"), ("stable_10", jev10, "keep_10"), ("stable_10", cent, "centrality"), ("survive_10", cent, "centrality")):
    y = np.array([r[label] for r in rows])
    (lo, hi), m = boot_auc(y, p); P(f"{label} ~ jev {nm}: point AUC={roc_auc_score(y,p):.3f}  boot mean={m:.3f}  95% CI=[{lo:.3f}, {hi:.3f}]")

P("\n## Jev repeat noise: 30 elder rows re-sent twice each (identical state), 60 calls")
from typesafe_sdk import TypeSafeClient, Noul, Score
questions = {k: (Noul(instructions=v) if k != "centrality" else Score(instructions=v, criteria=["peripheral", "background", "active", "central"])) for k, v in {
    "keep_1": "Will this entry still be present in the resident's state one wake from now?",
    "keep_10": "Will this entry still be present in the resident's state ten wakes from now?",
    "centrality": "How central is this entry to what the resident is doing right now?"}.items()}
client = TypeSafeClient(timeout=60); random.seed(0); pick = random.sample(range(len(raw)), 30)
out = (HERE / "jev_raw_repeat.jsonl").open("w"); d1 = []; d10 = []; dc = []; lat = []; intok = 0
for i in pick:
    st = raw[i]["state"]; reps = []
    for rep in range(2):
        t = time.perf_counter(); r = client.system_one(state=st, questions=questions); dt = time.perf_counter() - t; lat.append(dt)
        body = json.loads(r.raw_http_response.content); intok += r.usage.input_tokens or 0
        out.write(json.dumps({"row_index": i, "rep": rep, "state": st, "latency_s": round(dt, 4), "usage": r.usage.model_dump(), "response": body, "error": None}) + "\n")
        reps.append(body["answers"])
    orig = raw[i]["response"]["answers"]
    for a in reps:
        d1.append(abs(a["keep_1"]["noul"] - orig["keep_1"]["noul"])); d10.append(abs(a["keep_10"]["noul"] - orig["keep_10"]["noul"])); dc.append(abs(a["centrality"]["score"] - orig["centrality"]["score"]))
out.close()
P(f"calls={len(lat)} input_tokens={intok} latency mean={np.mean(lat):.4f}; |delta vs original| keep_1 mean={np.mean(d1):.4f} max={max(d1):.3f}; keep_10 mean={np.mean(d10):.4f} max={max(d10):.3f}; centrality mean={np.mean(dc):.4f} max={max(dc):.3f}")
P(f"for scale: sd of keep_1 across all 1486 elder rows = {jev1.std():.4f}, keep_10 sd = {jev10.std():.4f}, centrality sd = {cent.std():.4f}")
(HERE / "diag_output.txt").write_text("\n".join(L) + "\n")
