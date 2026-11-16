"""verification.py - per-link verification status from the LLM panel (Phase 1.3). Writes data/synth/verification.json and a summary.

Rule: both judges yes -> verification 'llm_consensus', which means CONTENT AND SPEAKER ONLY (verification_scope = content_speaker_only); roles are verified only by role-blind agreement and the human spot-check. Any partial/no -> an agent re-read and decided (recorded in AGENT_DECISIONS); such links stay
verification 'none' (not consensus) with the decision and reason attached. The only permitted pre-freeze gold edit (both judges 'no', agent agrees) did not arise.
Hand-checked links (agent, not human) are flagged separately. human_spotcheck is added only if the user returns the CSV.
"""
import collections, json, pathlib, sys
sys.path.insert(0, "eval")
import agreement as ag

AGENT = {  # reviewed by the agent after reading the surrounding lines
    ("set_01021", "B5"): ("keep", "granite stricter than the text warrants; both parts of the gist are in lines 28-29"),
    ("set_01022", "B6"): ("keep", "span narrower than the gist: the three-webinar plus retargeting arithmetic is not in the tagged lines"),
    ("set_01027", "B11"): ("keep", "content matches; granite stricter than the text warrants"),
    ("set_01029", "B4"): ("keep", "span narrower than the gist: 31 second calls and 5 complaints are in neighbouring lines"),
    ("set_01034", "B4"): ("keep", "tagged lines 7 and 11 carry the attendance and the absent accounts; the 40 percent and rival show are in line 9"),
    ("set_01036", "B4"): ("keep", "span narrower than the gist: one success and the 40-minute exposure are in neighbouring lines"),
    ("set_01036", "B5"): ("keep", "granite stricter than the text warrants"),
    ("set_01037", "B7"): ("keep", "span narrower than the gist: the 9,000 saving and no-minimum clause are in neighbouring lines"),
    ("set_01043", "B8"): ("keep", "span narrower than the gist: the 22 percent late submissions are in a neighbouring line"),
}

G = ag.load_jsonl("results/panel/gemini_synth.jsonl"); R = ag.load_jsonl("results/panel/granite_synth.jsonl"); H = ag.load_hand("results/panel/handcheck_agent.json")
out, cnt = {}, collections.Counter()
IN_DATASET = {p.stem for p in pathlib.Path("data/synth/gold").glob("*.json")}
for k in sorted(G):
    if k[0] not in IN_DATASET:      # verdicts for rejected sets (e.g. the dropped control set) are kept in results/panel but not in the dataset
        continue
    g, r, h = G[k], R.get(k), H.get(k)
    if g == "yes" and r == "yes" and h in (None, "yes"):
        v = dict(verification="llm_consensus", verification_scope="content_speaker_only")
    else:
        d = AGENT.get(k)
        assert d, f"unreviewed flagged link {k}"
        v = dict(verification="none", agent_decision=d[0], reason=d[1])
    v.update(gemini=g, granite=r, agent_handcheck=h)
    out[f"{k[0]}/{k[1]}"] = v
    cnt[v["verification"]] += 1
pathlib.Path("data/synth/verification.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print(dict(cnt), "links", len(out))
