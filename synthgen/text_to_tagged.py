"""text_to_tagged.py - hand-author sets as plain text, convert to the importer's tagged JSON.

Format (one file per set):
  set_id: set_01000
  seed: 1000
  arc_type: no_reversal
  topic: the pricing model for the analytics add-on
  option A: description
  option B: description            (also: option A+M)
  beat B1: one concrete sentence
  distractor topic: ...            (only if the assignment has a distractor)
  distractor option: ...
  beat D1: ...
  == m1
  Speaker: what they say @B1       (tags at the end, comma-separated for several: @B1,B2)
  Speaker: more talk
  == m2
  ...
Usage: python text_to_tagged.py pilot/ inbox/
"""
import json
import pathlib
import re
import sys

TAG = re.compile(r"\s@([A-Z]\d+(?:,[A-Z]\d+)*)\s*$")


def parse(path):
    d = dict(options={}, beats={}, distractor=None, meetings=[])
    dis = {}
    for n, raw in enumerate(pathlib.Path(path).read_text().splitlines(), 1):
        line = raw.strip().replace("**", "")
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("== m"):
            d["meetings"].append(dict(utterances=[]))
            continue
        if not d["meetings"]:
            k, _, v = line.partition(":")
            k, v = k.strip(), v.strip()
            if k == "seed":
                d["seed"] = int(v)
            elif k in ("set_id", "arc_type", "topic"):
                d[k] = v
            elif k.startswith("option "):
                d["options"][k[7:].strip()] = v
            elif k == "beat B" or k.startswith("beat "):
                bid = k[5:].strip()
                (dis.setdefault("beats", {}) if bid.startswith("D") else d["beats"])[bid] = v
            elif k == "distractor topic":
                dis["topic"] = v
            elif k == "distractor option":
                dis["option"] = v
            else:
                raise ValueError(f"{path}:{n}: unknown header line {line!r}")
            continue
        sp, sep, text = line.partition(": ")
        if not sep:
            raise ValueError(f"{path}:{n}: expected 'Speaker: text', got {line!r}")
        tags = []
        m = TAG.search(" " + text)
        if m:
            tags = m.group(1).split(",")
            text = TAG.sub("", " " + text).strip()
        d["meetings"][-1]["utterances"].append(dict(speaker=sp.strip(), text=text.strip(), tags=tags))
    if dis:
        d["distractor"] = dis
    return d


if __name__ == "__main__":
    src, dst = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for p in sorted(src.glob("*.txt")):
        d = parse(p)
        (dst / f"{d['set_id']}.json").write_text(json.dumps(d, indent=1))
        print(p.name, "->", [len(m["utterances"]) for m in d["meetings"]], "utterances per meeting")
