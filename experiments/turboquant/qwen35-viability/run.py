"""TurboQuant viability on the hybrid Qwen3.8-27B (qwen35: Gated DeltaNet + GQA), 4090.

Run ONLY under a GPU lease (it stops nothing itself; the lease stops door:qwen's server):
  deploy/ayllu-gpu run --holder custodian --purpose "..." --ttl 2h -- \
      python3 -I experiments/turboquant/qwen35-viability/run.py

One server per KV configuration, on 127.0.0.1:8091, from the TurboQuant fork build. Per configuration:
fit (does it start; VRAM), speed (prefill/decode from server timings), long-context recall
(a planted fact at the middle of synthetic filler, at several lengths up to the configured
context), and tool-call behaviour (parsed when tools are offered; leaked as text when none are).
All prompts are synthetic. No community record is read. Results append to results.jsonl.
"""
import json, os, random, subprocess, sys, time, urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.expanduser("~/src/llama-cpp-turboquant/build/bin/llama-server")
MODEL = os.path.expanduser("~/models/Qwen3.8-27B-GGUF/Qwen3.8-27B-Q4_K_M.gguf")
PORT = 8091
BASE = f"http://127.0.0.1:{PORT}"
CONFIGS = [  # (name, kv type, context)
    ("f16-65k", "f16", 65536),          # today's door configuration, on the fork binary
    ("q8_0-131k", "q8_0", 131072),
    ("turbo4-131k", "turbo4", 131072),
    ("turbo3-262k", "turbo3", 262144),
]
LENGTHS = [8000, 30000, 60000, 120000, 240000]   # target prompt tokens; skipped above the context
TOOL_TRIES = 5


def http(path, body=None, timeout=1800):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode() if body is not None else None,
                                 {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def vram_mib():
    out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                         capture_output=True, text=True).stdout.strip()
    return int(out.splitlines()[0]) if out else None


def start(kv, ctx):
    log = open(os.path.join(HERE, f"server-{kv}-{ctx}.log"), "w")
    p = subprocess.Popen([SERVER, "-m", MODEL, "--alias", "qwen-test", "-ngl", "99", "-c", str(ctx), "-np", "1",
                          "-fa", "on", "--jinja", "--reasoning-format", "none", "-ctk", kv, "-ctv", kv,
                          "--host", "127.0.0.1", "--port", str(PORT)], stdout=log, stderr=subprocess.STDOUT)
    for _ in range(300):
        if p.poll() is not None:
            return p, False
        try:
            if http("/health", timeout=5).get("status") == "ok":
                return p, True
        except Exception:
            pass
        time.sleep(2)
    return p, False


def stop(p):
    p.terminate()
    try:
        p.wait(60)
    except subprocess.TimeoutExpired:
        p.kill(); p.wait()
    time.sleep(5)


WORDS = ("river stone market lantern copper meadow harbor quiet thread orchard signal winter "
         "ladder cedar compass basket valley ember journal pebble").split()


def filler(n_words, rng):
    sents = []
    while sum(len(s.split()) for s in sents) < n_words:
        sents.append(" ".join(rng.choice(WORDS) for _ in range(rng.randint(8, 16))).capitalize() + ".")
    return " ".join(sents)


def recall(target_tokens, rng):
    code = str(rng.randint(1000, 9999))
    needle = f"Remember this: the vault code for the seventh door is {code}."
    tok_per_word = len(http("/tokenize", {"content": filler(2000, random.Random(1))})["tokens"]) / 2000
    words = int(target_tokens / tok_per_word)
    half = filler(words // 2, rng)
    text = half + " " + needle + " " + filler(words // 2, rng)
    q = "What is the vault code for the seventh door? Answer with the four digits only."
    t0 = time.time()
    r = http("/v1/chat/completions", {"model": "qwen-test", "max_tokens": 32, "temperature": 0,
                                      "chat_template_kwargs": {"enable_thinking": False},
                                      "messages": [{"role": "user", "content": text + "\n\n" + q}]})
    ans = (r["choices"][0]["message"].get("content") or "")
    tm = r.get("timings", {})
    return {"target_tokens": target_tokens, "prompt_tokens": r.get("usage", {}).get("prompt_tokens"),
            "correct": code in ans, "answer": ans.strip()[-40:], "wall_s": round(time.time() - t0, 1),
            "prefill_tok_s": tm.get("prompt_per_second"), "decode_tok_s": tm.get("predicted_per_second")}


def fn(name, props):
    return {"type": "function", "function": {"name": name, "description": name, "parameters": {
        "type": "object", "properties": {p: {"type": "string"} for p in props}}}}


def toolcalls():
    send, state = fn("send_message", ["to", "text", "reason"]), fn("update_state", ["updates", "reason"])
    sys_ = "You are a resident. Your tools include send_message(to, text, reason) and update_state(updates, reason)."
    user = "Post the word hello to the plaza now (to='plaza'), using send_message."
    out = {}
    for label, tools, choice in [("offered", [send, state], "auto"), ("withdrawn", None, "none")]:
        tally = {"parsed": 0, "leaked": 0, "text": 0}
        for _ in range(TOOL_TRIES):
            body = {"model": "qwen-test", "max_tokens": 300, "temperature": 0.7, "tool_choice": choice,
                    "chat_template_kwargs": {"enable_thinking": False},
                    "messages": [{"role": "system", "content": sys_}, {"role": "user", "content": user}]}
            if tools:
                body["tools"] = tools
            m = http("/v1/chat/completions", body)["choices"][0]["message"]
            c = m.get("content") or ""
            tally["parsed" if m.get("tool_calls") else ("leaked" if "<tool_call>" in c else "text")] += 1
        out[label] = tally
    return out


def main():
    commit = subprocess.run(["git", "-C", os.path.dirname(SERVER) + "/../..", "rev-parse", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    with open(os.path.join(HERE, "results.jsonl"), "a") as f:
        for name, kv, ctx in CONFIGS:
            row = {"at": datetime.now(timezone.utc).isoformat(), "config": name, "kv": kv, "ctx": ctx,
                   "fork_commit": commit, "model": os.path.basename(MODEL)}
            p, ok = start(kv, ctx)
            row["started"] = ok
            if ok:
                row["vram_mib"] = vram_mib()
                rng = random.Random(7)
                row["recall"] = []
                for n in LENGTHS:
                    if n > ctx - 1024:
                        continue
                    try:
                        row["recall"].append(recall(n, rng))
                    except Exception as e:
                        row["recall"].append({"target_tokens": n, "error": f"{type(e).__name__}: {e}"})
                try:
                    row["tools"] = toolcalls()
                except Exception as e:
                    row["tools"] = {"error": f"{type(e).__name__}: {e}"}
            stop(p)
            f.write(json.dumps(row) + "\n"); f.flush()
            print(json.dumps({k: row.get(k) for k in ("config", "started", "vram_mib")}), flush=True)


if __name__ == "__main__":
    sys.exit(main())
