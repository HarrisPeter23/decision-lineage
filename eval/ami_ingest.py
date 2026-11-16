"""ami_ingest.py - turn the AMI manual annotations (CC BY 4.0, ami_public_manual_1.6.2.zip) into plain-text transcripts in the benchmark format.

For each complete scenario series (4 meetings, letters a-d, same four participants):
  data/ami/series/<series>/<meeting>.txt     'Meeting: ES2002a / Date / Participants / blank / Role: utterance' (utterance = one transcriber segment, speakers merged by start time)
  data/ami/series/<series>/decisions.json    the DECISIONS / PROBLEMS / ACTIONS sentences of the abstractive summary, per meeting
  data/ami/series_index.json                 series list with roles, durations, utterance counts
Speakers are the role codes (PM, ME, UI, ID); the participant id behind each role is checked to be constant inside a series.
Raw archives stay in data/ami/raw (git-ignored). Attribution: AMI Meeting Corpus, CC BY 4.0.

  python eval/ami_ingest.py
"""
import collections
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ZIP = pathlib.Path("data/ami/raw/ami_public_manual_1.6.2.zip")
OUT = pathlib.Path("data/ami/series")
NS = "{http://nite.sourceforge.net/}"
ROLE_NAME = dict(PM="Project Manager", ME="Marketing Expert", UI="User Interface Designer", ID="Industrial Designer")


def xml(z, name):
    raw = z.read(name)
    return ET.fromstring(raw)


def words_of(z, meeting, agent):
    root = xml(z, f"words/{meeting}.{agent}.words.xml")
    W = {}
    order = []
    for e in root:
        if e.tag == "w":
            i = int(re.search(r"words(\d+)$", e.get("{http://nite.sourceforge.net/}id")).group(1))
            W[i] = (e.text or "", e.get("punc") == "true", float(e.get("starttime", 0)))
            order.append(i)
    return W


def segments(z, meeting, agent):
    W = words_of(z, meeting, agent)
    root = xml(z, f"segments/{meeting}.{agent}.segments.xml")
    out = []
    for s in root:
        if s.tag != "segment":
            continue
        start = float(s.get("transcriber_start", 0))
        toks = []
        for c in s:
            href = c.get("href", "")
            m = re.search(r"words(\d+)\)(?:\.\.id\(.*?words(\d+)\))?", href)
            if not m:
                continue
            a = int(m.group(1)); b = int(m.group(2) or a)
            for i in range(a, b + 1):
                if i in W:
                    toks.append(W[i])
        text = ""
        for t, punc, _ in toks:
            text += t if (punc or not text) else " " + t
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((start, text))
    return out


def decisions(z, meeting):
    n = f"abstractive/{meeting}.abssumm.xml"
    if n not in z.namelist():
        return None
    root = xml(z, n)
    d = collections.defaultdict(list)
    for block in root:
        tag = block.tag
        for s in block:
            if s.tag == "sentence" and (s.text or "").strip():
                d[tag].append(" ".join(s.text.split()))
    return dict(d)


def main():
    z = zipfile.ZipFile(ZIP)
    meet = xml(z, "corpusResources/meetings.xml")
    info = {}
    for m in meet:
        obs = m.get("observation")
        if m.get("type") == "scenario" and re.match(r"^(ES|IS|TS)\d{4}[a-d]$", obs or ""):
            info[obs] = dict(date=m.get("dateOnly"), duration=m.get("duration"), agents={s.get("nxt_agent"): (s.get("role"), s.get("global_name")) for s in m if s.tag == "speaker"})
    series = collections.defaultdict(dict)
    for obs in info:
        series[obs[:-1]][obs[-1]] = obs
    complete = {s: v for s, v in series.items() if sorted(v) == list("abcd")}
    index = {}
    for s, v in sorted(complete.items()):
        # the same participant must hold the same role in all four meetings
        roles = {obs: {a: info[obs]["agents"][a] for a in info[obs]["agents"]} for obs in v.values()}
        who = {}
        for obs, ag in roles.items():
            for a, (role, gname) in ag.items():
                who.setdefault(role, set()).add(gname)
        stable = all(len(g) == 1 for g in who.values())
        ok_files = all(f"abstractive/{o}.abssumm.xml" in z.namelist() and all(f"segments/{o}.{a}.segments.xml" in z.namelist() for a in info[o]["agents"]) for o in v.values())
        rec = dict(series=s, stable_roles=stable, files_ok=ok_files, meetings={})
        if stable and ok_files:
            (OUT / s).mkdir(parents=True, exist_ok=True)
            decs = {}
            for letter, obs in sorted(v.items()):
                utts = []
                for a, (role, g) in info[obs]["agents"].items():
                    utts += [(t, role, tx) for t, tx in segments(z, obs, a)]
                utts.sort(key=lambda x: (x[0], x[1]))
                head = [f"Meeting: {obs}", f"Date: {info[obs]['date']}", "Participants: " + ", ".join(sorted(r for r, _ in info[obs]["agents"].values())), ""]
                (OUT / s / f"{obs}.txt").write_text("\n".join(head + [f"{r}: {tx}" for _, r, tx in utts]) + "\n", encoding="utf-8", newline="\n")
                decs[obs] = decisions(z, obs)
                rec["meetings"][obs] = dict(utterances=len(utts), words=sum(len(tx.split()) for _, _, tx in utts), date=info[obs]["date"], duration_s=info[obs]["duration"],
                                            n_decisions=len((decs[obs] or {}).get("decisions", [])))
            (OUT / s / "decisions.json").write_text(json.dumps(decs, indent=1), encoding="utf-8")
        index[s] = rec
    pathlib.Path("data/ami/series_index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    ok = [s for s, r in index.items() if r["meetings"]]
    print("complete 4-meeting scenario series:", len(complete), "| usable (stable roles, files present):", len(ok))
    print("not usable:", {s: ("roles changed" if not r["stable_roles"] else "files missing") for s, r in index.items() if not r["meetings"]})
    u = [m["utterances"] for r in index.values() for m in r["meetings"].values()]
    print("meetings", len(u), "utterances per meeting mean/min/max", round(sum(u) / len(u)), min(u), max(u))


if __name__ == "__main__":
    main()
