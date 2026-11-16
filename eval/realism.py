"""realism.py - the same surface statistics on synthetic and real (AMI) transcripts (Phase 2.5).

All numbers use identical definitions on both corpora, computed from the plain-text transcripts' utterance lines:
  utt_per_meeting     number of utterance lines per meeting
  words_per_utt       mean whitespace-separated words per utterance
  filler_rate         share of utterances containing um / uh / erm / you know / i mean
  backchannel_rate    share of utterances of at most 2 words (mm-hmm, yeah, okay, right ...)
  long_utt_rate       share of utterances of 25 words or more
  restart_rate        share of utterances that contain a repeated adjacent word ('the the', 'we we') = disfluent repetition
  speakers_per_meeting
  decision_marker_share   share of utterances containing decision-like words (decide, agree, go with, let's, we'll, settle, final)
Cut-off rate (utterances ending with '-') is reported for synthetic only: AMI word-level transcription does not mark cut-offs that way, so it is not comparable.
Outputs results/realism.json and prints a table. Synthetic = the 30 new Claude-written sets (pilot sets excluded: they are short and from an earlier session).
"""
import json
import pathlib
import re
import statistics as st

FILL = re.compile(r"\b(um|uh|erm|you know|i mean)\b", re.I)
REPEAT = re.compile(r"\b(\w+)\s+\1\b", re.I)
DEC = re.compile(r"\b(decid\w*|agree\w*|go with|let's|let us|we'll|we will|settle\w*|final\w*)\b", re.I)


def utterances(path):
    L = pathlib.Path(path).read_text(encoding="utf-8").split("\n")
    body = [l for l in L[L.index("") + 1:] if l.strip()]
    return [(l.split(": ", 1)[0], l.split(": ", 1)[1] if ": " in l else l) for l in body]


def stats(files):
    per, W, S = [], [], []
    spk = []
    for f in files:
        u = utterances(f)
        per.append(len(u))
        spk.append(len({s for s, _ in u}))
        for _, t in u:
            W.append(len(t.split()))
            S.append(t)
    n = len(S)
    return dict(meetings=len(per), utt_per_meeting=round(st.mean(per)), utt_min=min(per), utt_max=max(per), words_per_utt=round(st.mean(W), 1),
                filler_rate=round(sum(bool(FILL.search(t)) for t in S) / n, 3), backchannel_rate=round(sum(w <= 2 for w in W) / n, 3),
                long_utt_rate=round(sum(w >= 25 for w in W) / n, 3), restart_rate=round(sum(bool(REPEAT.search(t)) for t in S) / n, 3),
                speakers_per_meeting=round(st.mean(spk), 1), decision_marker_share=round(sum(bool(DEC.search(t)) for t in S) / n, 3),
                cutoff_rate=round(sum(t.rstrip().endswith("-") for t in S) / n, 3))


def main():
    prov = json.loads(pathlib.Path("data/synth/provenance.json").read_text(encoding="utf-8"))
    syn = [f for sid, p in prov.items() if not p["writer"].startswith("claude (earlier") for f in sorted(pathlib.Path("data/synth/transcripts_txt", sid).glob("m*.txt"))]
    sel = json.loads(pathlib.Path("data/ami/selection.json").read_text(encoding="utf-8"))
    chosen = sel["reversal_series"] + sel["control_series"]
    ami_sel = [f for s in chosen for f in sorted(pathlib.Path("data/ami/series", s).glob("*.txt"))]
    ami_all = sorted(pathlib.Path("data/ami/series").glob("*/*.txt"))
    out = {"synthetic_30_new_sets": stats(syn), "ami_selected_5_series": stats(ami_sel), "ami_all_33_series": stats(ami_all)}
    pathlib.Path("results/realism.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    keys = list(next(iter(out.values())))
    print(f"{'':24}" + "".join(f"{k[:22]:>24}" for k in out))
    for k in keys:
        print(f"{k:24}" + "".join(f"{out[c][k]:>24}" for c in out))


if __name__ == "__main__":
    main()
