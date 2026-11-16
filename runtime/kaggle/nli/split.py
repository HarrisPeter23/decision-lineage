"""Splits the ordered NLI pairs into GPU kernels small enough to upload (large single uploads failed on 2026-11-06), and merges their outputs.
  python runtime/kaggle/nli/split.py build <ordered.jsonl> <prefix> <n_chunks>     -> runtime/kaggle/nli/kernels/<prefix>-<i>/
  python runtime/kaggle/nli/split.py merge <ordered.jsonl> <prefix> <n_chunks> <out_cache.jsonl>   (needs results/phase6/nli/out/<prefix>-<i>/nli_e.json)
The kernel source is the same as runtime/kaggle/nli/build.py (same model, revision, self-check)."""
import base64, gzip, json, pathlib, sys

TEMPLATE = pathlib.Path("runtime/kaggle/nli/build.py").read_text(encoding="utf-8").split("src = '''", 1)[1].split("'''.replace", 1)[0]


def load(f):
    return [json.loads(l) for l in pathlib.Path(f).read_text(encoding="utf-8").splitlines() if l.strip()]


def build(ordered, prefix, n):
    P = load(ordered)
    k = -(-len(P) // n)
    for i in range(n):
        part = P[i * k:(i + 1) * k]
        blob = base64.b64encode(gzip.compress(json.dumps(part).encode(), 9)).decode()
        out = pathlib.Path("runtime/kaggle/nli/kernels") / f"{prefix}-{i}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "nli.py").write_text(TEMPLATE.replace("@@B@@", blob), encoding="utf8", newline="\n")
        (out / "kernel-metadata.json").write_text(json.dumps(dict(id=f"KAGGLE_USER/{prefix}-{i}", title=f"{prefix}-{i}", code_file="nli.py", language="python",
            kernel_type="script", is_private=True, enable_gpu=True, enable_internet=True, dataset_sources=[], competition_sources=[], kernel_sources=[])))
        print(out, len(part), "pairs", round((out / "nli.py").stat().st_size / 1e6, 2), "MB")


def merge(ordered, prefix, n, dst):
    P = load(ordered)
    E = []
    for i in range(n):
        E += json.loads((pathlib.Path("results/phase6/nli/out") / f"{prefix}-{i}" / "nli_e.json").read_text())
    assert len(E) == len(P), (len(E), len(P))
    pathlib.Path(dst).write_text("\n".join(json.dumps(dict(p=d["p"], h=d["h"], e=e)) for d, e in zip(P, E)) + "\n", encoding="utf-8")
    print("merged", len(P), "->", dst)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "build":
        build(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else:
        merge(sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5])
