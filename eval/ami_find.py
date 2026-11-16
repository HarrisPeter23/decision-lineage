"""ami_find.py - read-only helper for drafting AMI gold chains: search a series' transcripts and print windows with utterance indexes.
  python eval/ami_find.py ES2002 "kinetic|batter" [--window 3] [--meetings b,c] [--max 40]
  python eval/ami_find.py ES2002 --show ES2002c 120 160          # print lines 120-160 of one meeting
Index = zero-based position among the utterance lines (as in the benchmark)."""
import pathlib
import re
import sys

SER = pathlib.Path("data/ami/series")


def lines(series, obs):
    L = (SER / series / f"{obs}.txt").read_text(encoding="utf-8").split("\n")
    return [l for l in L[L.index("") + 1:] if l.strip()]


def main():
    a = sys.argv[1:]
    series = a[0]
    if "--show" in a:
        i = a.index("--show")
        obs, s, e = a[i + 1], int(a[i + 2]), int(a[i + 3])
        L = lines(series, obs)
        for k in range(max(0, s), min(len(L), e + 1)):
            print(f"[{k}] {L[k][:300]}")
        return
    pat = re.compile(a[1], re.I)
    win = int(a[a.index("--window") + 1]) if "--window" in a else 0
    mx = int(a[a.index("--max") + 1]) if "--max" in a else 40
    which = a[a.index("--meetings") + 1].split(",") if "--meetings" in a else list("abcd")
    for m in which:
        obs = series + m
        L = lines(series, obs)
        hits = [i for i, l in enumerate(L) if pat.search(l)]
        print(f"===== {obs}: {len(L)} utterances, {len(hits)} hits")
        shown = set()
        for i in hits[:mx]:
            for k in range(max(0, i - win), min(len(L), i + win + 1)):
                if k not in shown:
                    shown.add(k)
                    print(f"{'*' if k == i else ' '}[{k}] {L[k][:240]}")
            if win:
                print("   ...")


if __name__ == "__main__":
    main()
