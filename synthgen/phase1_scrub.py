"""phase1_scrub.py - pre-gold edits to meeting text, each logged to reports/label_issues.md (rule 11: no real brands; length cap).

Only untagged lines are touched. Run once; it is idempotent (a replacement that no longer matches is skipped).
"""
import pathlib

M = pathlib.Path("../data/synth_work/meetings")
LOG = pathlib.Path("../reports/label_issues.md")

REPLACE = [
    ("set_01014/m1.txt", "gmail people though", "free-mail people though"),
    ("set_01014/m1.txt", "Gmail people aren't buying", "Free-mail people aren't buying"),
    ("set_01014/m1.txt", "And the gmail question", "And the free-mail question"),
    ("set_01014/m2.txt", "they're mailinator addresses", "they're throwaway addresses"),
    ("set_01014/m2.txt", "typing in the Amex to look", "typing in a corporate card to look"),
    ("set_01014/m2.txt", "That's Stripe's dunning emails", "That's the payment processor's dunning emails"),
    ("set_01014/m3.txt", "hand out the Amex so", "hand out the company card so"),
    ("set_01014/m3.txt", "without 128 mailinator addresses", "without 128 throwaway addresses"),
    ("set_01014/m3.txt", "they were mailinator addresses", "they were throwaway addresses"),
    ("set_01016/m1.txt", "the wrong Marriott, right", "the wrong Hartwell, right"),
    ("set_01016/m1.txt", "To the wrong Marriott.", "To the wrong Hartwell."),
    ("set_01019/m1.txt", "from the Slack thread", "from the chat thread"),
    ("set_01019/m3.txt", "count the Slack thread", "count the chat thread"),
]
# (file, first line, last line) 1-based inclusive: untagged tangents removed to meet the 120-utterance cap
TRIM = [("set_01025/m3.txt", [(97, 101), (49, 51), (9, 11)])]


def log(msg):
    LOG.parent.mkdir(exist_ok=True)
    if not LOG.exists():
        LOG.write_text("# Label and text issues (pre-freeze edits)\n\n", encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


for f, a, b in REPLACE:
    p = M / f
    t = p.read_text(encoding="utf-8")
    if a in t:
        assert "@" not in next(l for l in t.splitlines() if a in l), f"tagged line {f}"
        p.write_text(t.replace(a, b), encoding="utf-8", newline="\n")
        log(f"- {f}: real brand removed (rule 11). before: `{a}` after: `{b}`")
for f, spans in TRIM:
    p = M / f
    L = p.read_text(encoding="utf-8").splitlines()
    if len(L) <= 120:
        continue
    removed = []
    for s, e in sorted(spans, reverse=True):
        chunk = L[s - 1:e]
        assert not any("@" in l for l in chunk)
        removed += chunk
        del L[s - 1:e]
    p.write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")
    log(f"- {f}: {len(removed)} untagged tangent lines removed to meet the 120-utterance cap (now {len(L)}).")
print("scrub done")
