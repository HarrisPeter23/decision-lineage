# Phase 7 failure log (FREEZE section 21: every failed call, kernel error, timeout, parse failure and ingestion failure, per system)

| when (UTC) | system | job | item | failure | action |
|---|---|---|---|---|---|
| 2026-11-08 | lineage (extraction) | adl-p7-extract v1 | ami_TS3012 mtg_0003, chunk window 1 | Ollama ReadTimeout, 8 tries (600 s each); no links recorded | retried once with identical config and seed: adl-p7-extract-retry1 (whole corpus, since the recap prompt depends on its earlier outputs) |
| 2026-11-08 | lineage (extraction) | adl-p7-extract v1 | test_k1_06 mtg_0002 | Ollama ReadTimeout, 8 tries; no links recorded | same retry kernel |
| 2026-11-08 | lineage (extraction) | adl-p7-extract v1 | ami_TS3004 mtg_0004 | Ollama ReadTimeout, 8 tries; no links recorded | same retry kernel |

adl-p7-extract v1: 183 calls logged as completed, 3 failed (above); worker exit codes [1, 0, 1, 1] (rc 1 = a worker with a failed call); wall 10,338 s run + 165 s set-up; chunk budget = the frozen default 6000 (meta "chunk_budget": 0 means the override is unset).

## Retry rule for the extraction corpora (user decision, 2026-11-08, recorded before adl-p7-extract-retry1 finished)
- For each retried corpus (test_k1_06, ami_TS3012, ami_TS3004), the retry output is used for the WHOLE corpus, so that the recap chain stays consistent. This holds whether or not the earlier meetings match run 1.
- How many earlier meetings (before the failed one) differ from run 1 is reported for information only; it does not change which output is used.
- If a call fails again in the retry, the affected items are scored as failures (no further retries), per FREEZE section 21.

## graphiti, adl-p7-graphiti v1 (TEST pools 1 + 10; 138 episodes; wall 37,481 s of the 39,600 s budget; 3,614 LLM calls, 5 LLM errors)
9 of 138 episodes failed ingestion; 454/454 searches succeeded, none empty.

| corpus | episode | failure |
|---|---|---|
| test_k10_00 | mtg_0009 | APITimeoutError (Ollama request timed out) |
| test_k10_01 | mtg_0020 | APITimeoutError |
| test_k10_01 | mtg_0022 | APITimeoutError |
| test_k10_01 | mtg_0029 | JSONDecodeError: model output truncated/unterminated (parse failure) |
| test_k10_01 | mtg_0031 | JSONDecodeError (parse failure; 3,343 s) |
| test_k1_06 | mtg_0001 | JSONDecodeError (parse failure) |
| test_k1_11 | mtg_0001 | JSONDecodeError (parse failure) |
| test_k1_11 | mtg_0003 | APITimeoutError |
| test_k1_12 | mtg_0003 | APITimeoutError |

Pool 1 (H1): 4 of 69 episodes in 3 of 22 corpora. Pool 10 (descriptive): 5 of 69 episodes in 2 of 3 corpora. Retry: pending the user's decision (see the CHECKPOINT message of 2026-11-08).

## Graphiti retry decision (user, 2026-11-08)
- Pool 1: test_k1_06, test_k1_11 and test_k1_12 are retried once, each whole corpus, with identical config and seed, when a GPU slot frees (kernel adl-p7-graphiti-retry-p1).
- Pool 10: test_k10_00 and test_k10_01 are retried once the same way, after the Nov 14 00:00 UTC quota reset (kernel adl-p7-graphiti-retry-p10).
- The retry output replaces run 1 for the whole corpus. An episode that fails again stays missing and its items are scored as failures; no further retries.

## Extraction retry result, adl-p7-extract-retry1 (whole corpus, identical config and seed; 26 calls; worker rc [0, 1, 1, 0]; 6,160 s)
Per the rule above, the retry output is used for the whole of each corpus (now in `results/phase7/extract/preds/`; run 1 kept in `run1/`).

| corpus | run 1 failed calls | retry failed calls (FINAL, scored as failures) |
|---|---|---|
| test_k1_06 | mtg_0002 (ReadTimeout) | mtg_0002 (JSONDecodeError: model output did not parse) |
| ami_TS3012 | mtg_0003 window 1 (ReadTimeout) | mtg_0003 windows 1 and 2, mtg_0004 (all JSONDecodeError) |
| ami_TS3004 | mtg_0004 (ReadTimeout) | none |

Final extraction failures for my system: 1 meeting call on TEST pool 1 (test_k1_06 mtg_0002: no links), 0 on TEST pool 10, 3 calls on AMI (ami_TS3012). ami_TS3012 ends with more failed calls than in run 1; that is a consequence of the whole-corpus rule, which was fixed before the retry finished.

**Earlier meetings vs run 1 (information only; does not change which output is used):** test_k1_06: 1 earlier meeting, 0 differ. ami_TS3012: 1 earlier meeting, 1 differs (128 vs 187 links). ami_TS3004: 2 earlier meetings, 2 differ (20 vs 22, 145 vs 170 links). So, at temperature 0 and seed 7, Ollama output is not reproducible across runs on the long AMI meetings. The likely cause is concurrent batching, but that is not verified. The short synthetic meeting reproduced exactly.

## Graphiti pool-1 retry, adl-p7-graphiti-retry-p1 v1: kernel error at set-up (2026-11-08)
The Ollama install script returned rc 0 but left no `ollama` binary (FileNotFoundError at `ollama serve`). The kernel ran no episode and made no model call. As with the pre-freeze judge kernel v1 (truncated Ollama install, relaunched unchanged), the identical kernel was pushed again as v2. This is the same single retry, not attempted until now, not an extra re-run of any item. If the user disagrees, the v2 output can be discarded and the run-1 failures kept.

## evowiki_style, adl-p7-evowiki v1 (30 corpora, 158 meetings; wall 7,130 s)
22 failed Build calls in 10 corpora: 14 extract calls and 8 route calls. Each call's exception is caught: a failed extract call loses that window's updates, and a failed route call falls back to exact-name routing. For comparison, DEV (Phase 6) had 1 extract and 3 route failures across 16 builds.

| corpus | meetings | extract failed | route failed |
|---|---|---|---|
| test_k1_01 | 4 | 1 | 0 |
| test_k1_08 | 3 | 1 | 0 |
| test_k1_09 | 4 | 1 | 0 |
| test_k1_20 | 3 | 1 | 0 |
| test_k10_00 | 32 | 1 | 4 |
| test_k10_01 | 31 | 0 | 4 |
| test_k10_02 | 6 | 1 | 0 |
| ami_ES2002 | 4 | 3 | 0 |
| ami_TS3004 | 4 | 2 | 0 |
| ami_TS3012 | 4 | 3 | 0 |

Retry: the wiki is built meeting by meeting (State-Overwrite), so, as for extraction and Graphiti, the retry rebuilds each affected corpus whole with identical config (kernel adl-p7-evowiki-retry1: 10 corpora, 95 meetings; code and config identical to v1, and the corpora byte-identical to v1's bundle). Its output replaces run 1 for each whole corpus; calls that fail again are final. The kernel is built, and pushed when a GPU slot frees (the user may object before then).

## Rule: infrastructure failures before the first model call (user, 2026-11-08)
An infrastructure failure before the first model call (install, download, environment) is not an attempt. The identical kernel may be relaunched, at most 3 launches in total per kernel, and each launch is logged here. Accordingly, adl-p7-graphiti-retry-p1 v2 is the single retry of the 3 pool-1 Graphiti corpora (launch log: v1 2026-11-08 09:22 UTC, set-up failure (no ollama binary), no model call; v2 pushed 2026-11-08 about 10:00 UTC).

## EvoWiki retry split (user, 2026-11-08)
The combined adl-p7-evowiki-retry1 kernel (never pushed) is replaced by two kernels with identical code and config. adl-p7-evowiki-retry-p1 covers pool 1 + AMI (test_k1_01, _08, _09, _20; ami_ES2002, ami_TS3004, ami_TS3012) and is pushed as soon as a slot frees. adl-p7-evowiki-retry-p10 covers test_k10_00, _01, _02 and is pushed after the Nov 14 00:00 UTC reset.
- adl-p7-graphiti-retry-p1 launch 2 (v2, 2026-11-08 09:59 UTC): the same set-up failure, with the Ollama install script returning rc 0 after 21 s and no `ollama` binary; no model call. At the same moment, adl-p7-gen-mine-0 installed Ollama with the same command and ran normally. A CPU-only diagnostic kernel (adl-p7-diag-ollama, no GPU, no model call) replays the Graphiti set-up steps to find the cause before launch 3.

## Generation, adl-p7-gen-mine-0 (my system @ pool 1 / pool 10 / AMI + 3 ablations @ pool 1): 1210/1210 outputs, 0 errors or empty outputs, wall 12,841 s
- Diagnostic adl-p7-diag-ollama (CPU only, 2026-11-08 14:17 UTC): the Graphiti set-up steps and the same install script install Ollama 0.40.15 to /usr/local/bin normally on a CPU machine. The failure is therefore specific to the GPU machines, where the script also fetches the GPU libraries; not yet diagnosed. Launch 3 of adl-p7-graphiti-retry-p1 is held for the user's decision.
- User decision (2026-11-08): a short GPU diagnostic runs first (adl-p7-diag-ollama-gpu, no model call, about 0.1 GPU h); it does not use launch 3. The cause is reported, and any set-up change needs the user's approval.
- User conditions (2026-11-08): if the diagnostic leads to a change in how Ollama is installed, the model digests (qwen3:14b bdbd181c33f2…, all-minilm 1b226e28…) are confirmed identical to the frozen ones before any episode runs, and the change is logged in deviations.md as infrastructure-only. AMI generation for vector_rag and EvoWiki is pushed only if slack stays above 3 h after the pool-1 essentials. Everything else beyond pool 1 waits for the Nov 14 reset.

## EvoWiki retry, adl-p7-evowiki-retry-p1 (7 corpora, 26 meetings; pushed 2026-11-08 14:15 UTC, wall 2,299 s; qwen3:14b digest bdbd181c… confirmed)
Whole-corpus rule applied: the retry wiki.json replaces run 1 for all 7 corpora (run 1 kept in results/phase7/evowiki/run1/, retry logs in retry1/). Calls that failed again are final (no further retry).

| corpus | extract failed (run 1 -> retry) | route failed (run 1 -> retry) | wiki vs run 1 |
|---|---|---|---|
| test_k1_01 | 1 -> 1 | 0 -> 0 | differs |
| test_k1_08 | 1 -> 0 | 0 -> 0 | differs |
| test_k1_09 | 1 -> 0 | 0 -> 0 | differs |
| test_k1_20 | 1 -> 1 | 0 -> 0 | byte-identical (deterministic failure) |
| ami_ES2002 | 3 -> 3 | 0 -> 0 | differs |
| ami_TS3004 | 2 -> 1 | 0 -> 0 | differs |
| ami_TS3012 | 3 -> 3 | 0 -> 1 | differs |

Final for these corpora: pool 1 has 2 failed extract calls (test_k1_01, test_k1_20); AMI has 7 failed extract calls and 1 failed route call. The log does not record exception text. Pool 10 (test_k10_00/_01/_02) waits for adl-p7-evowiki-retry-p10 after the Nov 14 reset.

## Generation, adl-p7-gen-vrag-p1-0 (vector_rag @ pool 1, ctx 12288): 232/232 outputs, 0 errors or empty outputs, wall 3,969 s
- Generation adl-p7-gen-evo-p1-0 (evowiki_style @ pool 1, ctx 12288): 232/232 outputs, 0 errors or empty outputs, wall 2,922 s; qwen3:14b digest bdbd181c… confirmed.
- GPU diagnostic adl-p7-diag-ollama-gpu (Tesla T4, 2026-11-08 16:38 UTC, no model call): the same Graphiti set-up steps in the same order (pip graphiti-core 0.31.2, apt zstd + openjdk, Neo4j 5.26.17 download, password, start), then the same install.sh run with `sh -x`. It installed Ollama 0.40.15 to /usr/local/bin normally (about 20 s). The failure did NOT reproduce. The Graphiti code is identical to run 1, which installed normally. In both failed launches, `curl -fsSL https://ollama.com/install.sh | sh` returned rc 0 after about 11 s (shorter than a normal install), and `ollama` was then missing. The reported rc is that of `sh`, and install.sh itself extracts the binary with `curl ... | tar` without pipefail, so a failed or truncated download of the script or of the Ollama tarball would return rc 0 and leave no binary. Probable cause: a transient download failure masked by the pipes (not proven; exception text is not available). Launch 3 is held for the user's decision on the set-up.
- User decision (2026-11-09): launch 3 uses the hardened install (D-36, infrastructure only). Bundle identical to v2; digests asserted against the frozen ones before any episode.
- adl-p7-graphiti-retry-p1 launch 3 (v3, hardened install, 2026-11-09 03:07 UTC): set-up failure again, no model call. `apt-get install zstd openjdk-17-jre-headless` failed (rc 100, "Unable to connect to archive.ubuntu.com"), so zstd was missing. The Ollama tarball is .tar.zst, so install.sh failed on all 3 attempts (rc 1, now visible because of D-36), and the kernel stopped as designed before any model call. The earlier launches (v1, v2) logged apt rc 0, so their cause stays unproven. That is 3 of 3 allowed launches used. No further launch is made without the user's decision. Logs: results/phase7/graphiti/retry_p1_launch3/.
- User decision (2026-11-09): one exception to the 3-launch cap. Launch 4 (pushed 04:01 UTC) adds an apt retry and a zstd/java check (D-36 addendum); bundle identical to v2.

## Graphiti retry, adl-p7-graphiti-retry-p1 launch 4 (2026-11-09 04:01 UTC; wall 5,244 s; 108 LLM calls, 0 client errors; frozen digests confirmed)
The set-up succeeded (apt rc 0, zstd and java present, Ollama installed). The whole-corpus rule applies: the retry episodes and search files replace run 1 for all 3 corpora (run 1 kept in results/phase7/graphiti/run1/, the retry in retry_p1/). Episodes that failed again are final.

| corpus | meeting | run 1 | retry |
|---|---|---|---|
| test_k1_06 | mtg_0001 | JSONDecodeError | JSONDecodeError (unterminated string; final) |
| test_k1_11 | mtg_0001 | JSONDecodeError | JSONDecodeError (unterminated string; final) |
| test_k1_11 | mtg_0003 | APITimeoutError | JSONDecodeError (unterminated string; final) |
| test_k1_12 | mtg_0003 | APITimeoutError | ok |

Graphiti pool 1, final: 3 of 69 episodes failed, in 2 of 22 corpora (test_k1_06, test_k1_11). The search results differ from run 1 for all 3 corpora. Neo4j "EquivalentSchemaRuleAlreadyExists" messages at start-up are from concurrent `CREATE INDEX IF NOT EXISTS` calls. They are not episode failures, and no episode is affected.
- Graphiti run 1 search_test_k1_21.json was missing locally (a gap from the earlier paged download; run 1 reports 454/454 searches ok). It was re-downloaded from kernel adl-p7-graphiti (10 questions) and placed in graphiti_out/ and run1/. Graphiti pool-1 retrieval: 232 questions. Generation kernel adl-p7-gen-graphiti-p1-0 (ctx 12288) pushed.
- Generation adl-p7-gen-graphiti-p1-0 (graphiti @ pool 1, ctx 12288): 232/232 outputs, 0 errors or empty outputs, wall 3,606 s; digest bdbd181c… confirmed. Pool-1 generation is now complete for every system and ablation. The pool-1 failure log is final.

## D-35 subset fixed (2026-11-10, from the final pool-1 failure log, before any TEST score was computed)
The sets excluded are those where any system had a failed call or episode after the single retry:
- lineage extraction (shared by the 3 ablations): test_k1_06;
- evowiki_style: test_k1_01, test_k1_20;
- graphiti: test_k1_06, test_k1_11;
- vector_rag and every generation run: none.

The excluded sets are set_01018, set_01020, set_01025 and set_01043 (4 of 22). The failure-free subset has **18 sets**: `results/phase7/d35_subset.json`.

Pool-1 failure rates per system (TEST, after retry; for the paper):
- **lineage extraction:** 1 failed call in 22 corpora (test_k1_06 mtg_0002, no links).
- **evowiki_style Build:** 2 failed extract calls (test_k1_01, test_k1_20), 0 route failures.
- **graphiti:** 3 of 69 episodes failed ingestion (test_k1_06 mtg_0001; test_k1_11 mtg_0001, mtg_0003).
- **vector_rag:** 0.
- **Generation:** 0 failed outputs for every system (232/232 each; my system and ablations 1210/1210 over all scopes).
