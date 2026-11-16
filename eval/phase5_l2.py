"""phase5_l2.py - grid for linker revision L2 (pre-declared in reports/phase5.md section 2): team_at x link_at, objective = mean DEV headline retrieval
completeness at pool 1 and pool 10 for the final config. Ties: smaller team_at, then link_at 0.4.
  HF_HUB_OFFLINE=1 python eval/phase5_l2.py -> results/phase5/l2_grid.json
"""
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "eval"), str(ROOT / "synthgen")]
from argdecisionlineage.linking import Embedder               # noqa: E402
from phase5_retrieval import HEADLINE, boot, run_pool         # noqa: E402

TEAM = [0.0, 0.2, 0.3, 0.5]
LINK = [0.4, 0.5, 0.6]


def main():
    dev = json.loads((ROOT / "data/synth/split.json").read_text(encoding="utf-8"))["dev"]
    gold = {s: json.loads((ROOT / "data/synth/gold" / f"{s}.json").read_text(encoding="utf-8")) for s in dev}
    index = json.loads((ROOT / "data/synth/pools/dev/index.json").read_text(encoding="utf-8"))
    emb = Embedder()
    grid = []
    for ta, la in itertools.product(TEAM, LINK):
        lp = dict(team_at=ta, link_at=la)
        res = {}
        for size, src in (("1", "single_pass_recap_roles_top4"), ("10", "single_pass_recap_roles_top4_pooled")):
            rows = []
            for p in [p for p in index if p.startswith(f"dev_k{size}_")]:
                rows += run_pool(ROOT / "data/synth/pools/dev" / p, src, emb, gold, link_params=lp)
            res[size] = boot(rows, dev, lambda r: r["type"] in HEADLINE)
        grid.append(dict(team_at=ta, link_at=la, k1=res["1"], k10=res["10"], objective=round((res["1"][0] + res["10"][0]) / 2, 4)))
        print(grid[-1])
    best = max(grid, key=lambda r: (r["objective"], -r["team_at"], r["link_at"] == 0.4))
    print("selected:", best)
    (ROOT / "results/phase5/l2_grid.json").write_text(json.dumps(dict(selected=best, grid=grid), indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
