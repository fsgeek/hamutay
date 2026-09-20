"""Evaluate Jev against baselines on Goal A (preservation) and Goal B (posture judge).
All numbers in REPORT.md come from this script's output (eval_output.txt / eval_results.json).
Run: uv run python experiments/jev_preservation_20260919/evaluate.py
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, log_loss, brier_score_loss
from sklearn.model_selection import GroupKFold
from scipy.stats import spearmanr, pearsonr

HERE = Path(__file__).resolve().parent
OUT = {}
LINES = []
def P(*a):
    s = " ".join(str(x) for x in a); print(s); LINES.append(s)

def load_jsonl(p): return [json.loads(l) for l in p.read_text().splitlines() if l.strip()]

def clip(p): return np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)

def metrics(y, p):
    y = np.asarray(y, int); p = clip(p)
    out = {"n": int(len(y)), "pos_rate": float(y.mean()), "brier": float(brier_score_loss(y, p)),
           "logloss": float(log_loss(y, p, labels=[0, 1]))}
    out["auc"] = float(roc_auc_score(y, p)) if 0 < y.mean() < 1 else float("nan")
    return out

def reliability(y, p, bins=10):
    y = np.asarray(y, int); p = np.asarray(p, float)
    edges = np.linspace(0, 1, bins + 1); rows = []; ece = 0.0
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        m = (p >= lo) & (p < hi) if i < bins - 1 else (p >= lo) & (p <= hi)
        n = int(m.sum())
        if n == 0:
            rows.append({"bin": f"[{lo:.1f},{hi:.1f})", "n": 0, "mean_pred": None, "obs_freq": None}); continue
        mp, of = float(p[m].mean()), float(y[m].mean()); ece += n / len(y) * abs(mp - of)
        rows.append({"bin": f"[{lo:.1f},{hi:.1f})", "n": n, "mean_pred": round(mp, 3), "obs_freq": round(of, 3)})
    return rows, ece

def fmt_rel(rows, ece):
    s = ["| bin | n | mean pred | obs freq |", "|---|---|---|---|"]
    for r in rows:
        s.append(f"| {r['bin']} | {r['n']} | {'' if r['mean_pred'] is None else r['mean_pred']} | {'' if r['obs_freq'] is None else r['obs_freq']} |")
    s.append(f"ECE = {ece:.4f}")
    return "\n".join(s)

def cv_logistic(X, y, groups, n_splits=5):
    """Out-of-fold probabilities, GroupKFold by cycle."""
    X = np.asarray(X, float); y = np.asarray(y, int); groups = np.asarray(groups)
    n_splits = min(n_splits, len(np.unique(groups)))
    oof = np.zeros(len(y)); base = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=n_splits).split(X, y, groups):
        base[te] = y[tr].mean()
        if len(np.unique(y[tr])) < 2:
            oof[te] = y[tr].mean(); continue
        mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-9
        clf = LogisticRegression(C=1.0, max_iter=2000).fit((X[tr] - mu) / sd, y[tr])
        oof[te] = clf.predict_proba((X[te] - mu) / sd)[:, 1]
    return oof, base

# ---------------- Goal A ----------------
def goal_a(resident, label_map):
    rows = load_jsonl(HERE / f"rows_{resident}.jsonl")
    raw = {r["row_index"]: r for r in load_jsonl(HERE / f"jev_raw_{resident}.jsonl")}
    P(f"\n## Goal A — {resident}: rows={len(rows)} jev_calls={len(raw)} errors={sum(1 for r in raw.values() if r['error'])}")
    lat = [r["latency_s"] for r in raw.values()]
    P(f"latency s: mean={np.mean(lat):.4f} median={np.median(lat):.4f} p95={np.percentile(lat,95):.4f} max={max(lat):.4f}")
    intok = sum((r.get("usage") or {}).get("input_tokens", 0) for r in raw.values())
    P(f"input tokens={intok} input chars={sum(r['input_chars'] for r in raw.values())} est cost=${intok*0.042/1e6:.4f}")
    res = {"n_rows": len(rows), "labels": {}}
    joined = []
    for i, row in enumerate(rows):
        jr = raw.get(i)
        if jr is None or jr["error"]: continue
        a = jr["response"]["answers"]
        joined.append((row, a["keep_1"]["noul"], a["keep_10"]["noul"], a["centrality"]["score"], a["centrality"]["confidence"]))
    P(f"joined rows with a Jev answer: {len(joined)}; truncated values: {sum(r['truncated'] for r,*_ in joined)}")
    P(f"Jev keep_1 mean={np.mean([j[1] for j in joined]):.3f} sd={np.std([j[1] for j in joined]):.3f}; keep_10 mean={np.mean([j[2] for j in joined]):.3f} sd={np.std([j[2] for j in joined]):.3f}; centrality mean={np.mean([j[3] for j in joined]):.3f} sd={np.std([j[3] for j in joined]):.3f}")
    for label, jev_field in label_map:
        sub = [j for j in joined if j[0].get(label) is not None]
        if not sub: P(f"### {label}: no rows"); continue
        y = np.array([j[0][label] for j in sub]); groups = np.array([j[0]["cycle"] for j in sub])
        X = np.array([[math.log(j[0]["age"] + 1), math.log(j[0]["length"] + 1), j[0]["position"], j[0]["n_entries"]] for j in sub])
        jev = np.array([j[1] if jev_field == "keep_1" else j[2] for j in sub]); cent = np.array([j[3] for j in sub])
        P(f"\n### {resident} / label={label} (Jev field={jev_field}): n={len(y)} base rate={y.mean():.4f} cycles={len(set(groups))}")
        out = {}
        if 0 < y.mean() < 1:
            oof, base = cv_logistic(X, y, groups)
            oof_c, _ = cv_logistic(np.c_[X, cent], y, groups)
            oof_jc, _ = cv_logistic(np.c_[X, cent, jev], y, groups)
            oof_platt, _ = cv_logistic(jev[:, None], y, groups)
            cands = {"base_rate(cv)": base, "logistic[age,len,pos,n]": oof, "logistic+centrality": oof_c,
                     "logistic+centrality+jev_noul": oof_jc, "jev_noul(raw)": jev, "jev_noul(platt-recal, cv)": oof_platt}
        else:
            cands = {"base_rate(const)": np.full(len(y), y.mean()), "jev_noul(raw)": jev}
        P("| predictor | n | Brier | AUC | log-loss |"); P("|---|---|---|---|---|")
        for name, p in cands.items():
            m = metrics(y, p); out[name] = m
            P(f"| {name} | {m['n']} | {m['brier']:.4f} | {m['auc']:.4f} | {m['logloss']:.4f} |")
        for name in ("jev_noul(raw)", "logistic[age,len,pos,n]", "base_rate(cv)"):
            if name in cands:
                rr, ece = reliability(y, cands[name]); out[name]["reliability"] = rr; out[name]["ece"] = ece
                P(f"\nReliability — {name}:"); P(fmt_rel(rr, ece))
        # correlations of centrality and jev noul with label and with baseline features
        if 0 < y.mean() < 1:
            P(f"\ncorr(centrality, label)={pearsonr(cent, y)[0]:.3f}  corr(jev_noul, label)={pearsonr(jev, y)[0]:.3f}  "
              f"corr(jev_noul, log age)={pearsonr(jev, X[:,0])[0]:.3f}  corr(jev_noul, centrality)={pearsonr(jev, cent)[0]:.3f}  "
              f"corr(centrality, log age)={pearsonr(cent, X[:,0])[0]:.3f}")
        res["labels"][label] = out
    # extra: same thing excluding the harness-owned 'cycle' key
    return res

# ---------------- Goal B ----------------
MARKERS = ("ai_self_identification", "hedging_disclaimers", "deference_sycophancy", "helpfulness_performance")
def goal_b():
    rows = load_jsonl(HERE / "goal_b_rows.jsonl")
    raw = {r["row_index"]: r for r in load_jsonl(HERE / "jev_raw_goal_b.jsonl")}
    P(f"\n## Goal B — posture: turns={len(rows)} calls={len(raw)} errors={sum(1 for r in raw.values() if r['error'])}")
    lat = [r["latency_s"] for r in raw.values()]
    P(f"latency s: mean={np.mean(lat):.4f} median={np.median(lat):.4f} p95={np.percentile(lat,95):.4f} max={max(lat):.4f}")
    res = {}
    J = []
    for i, r in enumerate(rows):
        jr = raw.get(i)
        if jr is None or jr["error"]: continue
        J.append((r, jr["response"]["answers"]))
    P("\n### Per-marker agreement (Jev argmax level vs each judge; two-judge agreement as ceiling)")
    P("| marker | n | kimi=claude exact | kimi=claude ±1 | jev=kimi exact | jev=claude exact | jev=agreed (n agreed) | jev ±1 kimi | spearman jev~kimi | jev~claude | kimi~claude |")
    P("|---|---|---|---|---|---|---|---|---|---|---|")
    pooled_hit = defaultdict(list)  # reference -> (maxprob, hit)
    pmaj_vs_consensus = []
    for m in MARKERS:
        k = np.array([r[f"kimi_{m}"] for r, _ in J]); c = np.array([r[f"claude_{m}"] for r, _ in J])
        probs = [a[m]["probabilities"] for _, a in J]
        jev_arg = np.array([int(max(p, key=lambda lv: p[lv])) for p in probs])
        jev_max = np.array([max(p.values()) for p in probs])
        jev_exp = np.array([a[m]["score"] for _, a in J])
        agree = k == c
        row = {"n": len(k), "kc_exact": float(agree.mean()), "kc_pm1": float((np.abs(k - c) <= 1).mean()),
               "jk_exact": float((jev_arg == k).mean()), "jc_exact": float((jev_arg == c).mean()),
               "j_agreed": float((jev_arg[agree] == k[agree]).mean()) if agree.any() else float('nan'), "n_agreed": int(agree.sum()),
               "jk_pm1": float((np.abs(jev_arg - k) <= 1).mean()),
               "sp_jk": float(spearmanr(jev_exp, k)[0]) if k.std() > 0 else float('nan'),
               "sp_jc": float(spearmanr(jev_exp, c)[0]) if c.std() > 0 else float('nan'),
               "sp_kc": float(spearmanr(k, c)[0]) if k.std() > 0 and c.std() > 0 else float('nan'),
               "dist_kimi": dict(Counter(k.tolist())), "dist_claude": dict(Counter(c.tolist())), "dist_jev": dict(Counter(jev_arg.tolist()))}
        res[m] = row
        P(f"| {m} | {row['n']} | {row['kc_exact']:.3f} | {row['kc_pm1']:.3f} | {row['jk_exact']:.3f} | {row['jc_exact']:.3f} | {row['j_agreed']:.3f} ({row['n_agreed']}) | {row['jk_pm1']:.3f} | {row['sp_jk']:.3f} | {row['sp_jc']:.3f} | {row['sp_kc']:.3f} |")
        for i in range(len(k)):
            pooled_hit["kimi"].append((jev_max[i], int(jev_arg[i] == k[i])))
            pooled_hit["claude"].append((jev_max[i], int(jev_arg[i] == c[i])))
            if agree[i]: pooled_hit["agreed"].append((jev_max[i], int(jev_arg[i] == k[i])))
            pmaj_vs_consensus.append((probs[i][str(int(k[i]))], int(agree[i])))
    for m in MARKERS:
        P(f"  {m}: level dist kimi={res[m]['dist_kimi']} claude={res[m]['dist_claude']} jev_argmax={res[m]['dist_jev']}")
    P("\n### Reliability of Jev's max probability (its argmax level) vs whether the argmax matches the reference — pooled over 4 markers")
    for ref, pairs in pooled_hit.items():
        p = np.array([x[0] for x in pairs]); h = np.array([x[1] for x in pairs])
        rr, ece = reliability(h, p); res[f"rel_{ref}"] = {"rows": rr, "ece": ece, "n": len(h), "hit": float(h.mean()), "mean_conf": float(p.mean())}
        P(f"\nreference={ref}: n={len(h)} overall hit={h.mean():.3f} mean maxprob={p.mean():.3f}"); P(fmt_rel(rr, ece))
    p = np.array([x[0] for x in pmaj_vs_consensus]); h = np.array([x[1] for x in pmaj_vs_consensus])
    rr, ece = reliability(h, p); res["rel_pkimi_vs_judge_consensus"] = {"rows": rr, "ece": ece}
    P(f"\n### Jev's probability on the KIMI label, binned, vs rate at which the Claude judge agrees with KIMI (is Jev's confidence predictive of judge consensus?) n={len(h)}")
    P(fmt_rel(rr, ece))
    # composite
    jev_comp = np.array([np.mean([a[m]["score"] for m in MARKERS]) for _, a in J])
    k_comp = np.array([np.mean([r[f"kimi_{m}"] for m in MARKERS]) for r, _ in J])
    c_comp = np.array([np.mean([r[f"claude_{m}"] for m in MARKERS]) for r, _ in J])
    P(f"\n### Composite (mean of 4 markers): pearson jev~kimi={pearsonr(jev_comp,k_comp)[0]:.3f} jev~claude={pearsonr(jev_comp,c_comp)[0]:.3f} kimi~claude={pearsonr(k_comp,c_comp)[0]:.3f}")
    P("| premise | n turns | n live (len>=120) | kimi comp | claude comp | jev comp | (live only) kimi | claude | jev |"); P("|---|---|---|---|---|---|---|---|---|")
    res["composite_by_premise"] = {}
    for prem in ("default", "peer", "uncertain", "filler"):
        idx = np.array([r["premise"] == prem for r, _ in J]); live = idx & np.array([r["len"] >= 120 for r, _ in J])
        d = {"n": int(idx.sum()), "n_live": int(live.sum()), "kimi": float(k_comp[idx].mean()), "claude": float(c_comp[idx].mean()), "jev": float(jev_comp[idx].mean()),
             "kimi_live": float(k_comp[live].mean()), "claude_live": float(c_comp[live].mean()), "jev_live": float(jev_comp[live].mean())}
        res["composite_by_premise"][prem] = d
        P(f"| {prem} | {d['n']} | {d['n_live']} | {d['kimi']:.3f} | {d['claude']:.3f} | {d['jev']:.3f} | {d['kimi_live']:.3f} | {d['claude_live']:.3f} | {d['jev_live']:.3f} |")
    # premise choice
    truth = [r["premise"] for r, _ in J]; ch = [a["premise"]["choice"] for _, a in J]; conf = np.array([a["premise"]["confidence"] for _, a in J])
    pmax = np.array([max(a["premise"]["probabilities"].values()) for _, a in J]); hit = np.array([t == c for t, c in zip(truth, ch)], int)
    P(f"\n### Premise Choice (4-way, ground truth = experiment label): accuracy={hit.mean():.3f} (chance 0.25, majority class={max(Counter(truth).values())/len(truth):.3f}); Jev choice dist={dict(Counter(ch))}")
    cm = defaultdict(Counter)
    for t, c in zip(truth, ch): cm[t][c] += 1
    for t in ("default", "peer", "uncertain", "filler"): P(f"  truth={t}: {dict(cm[t])}")
    rr, ece = reliability(hit, pmax); P("Reliability of max premise probability vs correctness:"); P(fmt_rel(rr, ece))
    res["premise"] = {"acc": float(hit.mean()), "confusion": {t: dict(v) for t, v in cm.items()}, "reliability": rr, "ece": ece}
    return res

if __name__ == "__main__":
    results = {}
    results["elder"] = goal_a("elder", [("survive_1", "keep_1"), ("survive_5", "keep_10"), ("survive_10", "keep_10"), ("stable_10", "keep_10")])
    for r in ("fable", "heartbeat", "qwen"):
        if (HERE / f"jev_raw_{r}.jsonl").exists():
            results[r] = goal_a(r, [("survive_1", "keep_1"), ("survive_5", "keep_10"), ("survive_5_vs_keep_1", "keep_1")] if False else [("survive_1", "keep_1"), ("survive_5", "keep_10")])
    results["goal_b"] = goal_b()
    (HERE / "eval_results.json").write_text(json.dumps(results, indent=1, default=float))
    (HERE / "eval_output.txt").write_text("\n".join(LINES) + "\n")
