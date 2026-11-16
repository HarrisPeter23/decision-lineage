"""faithfulness.py - ALCE-style citation checks for generated explanations (pre-declared, reports/phase5.md section 0b).

NLI_MODEL = cross-encoder/nli-deberta-v3-small (revision fa2804872c3b), CPU. Entailed iff P(entailment) >= 0.5 (fixed).
For each sentence with citations C (retrieved items):
  supported      = entails(premise(C), sentence)                                    -> citation recall
  relevant(c)    = entails(premise([c]), s) or (supported and not entails(premise(C - {c}), s))   -> citation precision
  hallucinated   = no single retrieved item entails s and premise(all retrieved) does not entail s
  lexical_ok     = |tokens(s) & tokens(cited)| / |tokens(s)| >= 0.25
Premise text of an item: "Speaker (role, meeting k): text". Long premises are truncated by the model's tokenizer (512 tokens); this is stated, not hidden.
The checker is pluggable (`nli` callable: list of (premise, hypothesis) -> list of P(entail)) so tests can use a toy one.
"""
import functools

from .graph import tokens

NLI = "cross-encoder/nli-deberta-v3-small"
NLI_REV = "fa2804872c3b"
AT = 0.5


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(NLI, revision=NLI_REV, device="cpu")


class NLIChecker:
    def __init__(self, nli=None):
        self.fn = nli
        self.cache = {}
        self.ent = None

    def probs(self, pairs):
        todo = [p for p in dict.fromkeys(pairs) if p not in self.cache]
        if todo:
            if self.fn:
                out = self.fn(todo)
            else:
                m = _model()
                if self.ent is None:
                    lab = {v.lower(): k for k, v in m.model.config.id2label.items()}
                    self.ent = lab["entailment"]
                    # self-check: a model with a missing tokenizer maps every token to [UNK] and returns the same scores for every pair (seen 2026-11-04)
                    chk = m.predict([("The van costs 4,100 a month.", "The van costs 4,100 a month."), ("The van costs 4,100 a month.", "The van costs 9,000 a month.")],
                                    apply_softmax=True)
                    assert chk[0][self.ent] > 0.9 and chk[1][self.ent] < 0.1, f"NLI self-check failed: {chk}"
                out = [float(r[self.ent]) for r in m.predict(todo, apply_softmax=True, batch_size=16, show_progress_bar=False)]
            for p, v in zip(todo, out):
                self.cache[p] = float(v)
        return [self.cache[p] for p in pairs]


def premise(items, ordn=None):
    """Source text of each item: its transcript utterances (`source_text`, set by baselines whose items are paraphrases) or, by default, its text
    (my system's and vector_rag's items ARE utterances). Phase 6 amendment A1: faithfulness is always checked against the meeting, never a paraphrase."""
    return " ".join(f"{it['speaker']} ({it['role'] or 'excerpt'}, meeting {ordn.get(it['meeting'], '?') if ordn else it['meeting']}): {it.get('source_text', it['text'])}"
                    for it in items)


def check_answer(sentences, retrieved, checker, ordn=None):
    """sentences: [{text, cites=[items]}]; retrieved: all items the generator saw. Returns per-sentence dicts."""
    out = []
    for s in sentences:
        h, C = s["text"], s["cites"]
        pairs = []
        if C:
            pairs.append((premise(C, ordn), h))
            pairs += [(premise([c], ordn), h) for c in C]
            if len(C) > 1:
                pairs += [(premise([x for x in C if x is not c], ordn), h) for c in C]
        pairs += [(premise([it], ordn), h) for it in retrieved]
        if retrieved:
            pairs.append((premise(retrieved, ordn), h))
        pr = dict(zip(pairs, checker.probs(pairs)))
        sup = bool(C) and pr[(premise(C, ordn), h)] >= AT
        rel = []
        for c in C:
            alone = pr[(premise([c], ordn), h)] >= AT
            needed = sup and (len(C) == 1 or pr[(premise([x for x in C if x is not c], ordn), h)] < AT)
            rel.append(alone or needed)
        any_single = any(pr[(premise([it], ordn), h)] >= AT for it in retrieved)
        all_ = bool(retrieved) and pr[(premise(retrieved, ordn), h)] >= AT
        st = set(tokens(h))
        ct = set(tokens(" ".join(c["text"] for c in C)))
        out.append(dict(text=h, n_cites=len(C), supported=sup, p_support=round(pr[(premise(C, ordn), h)], 4) if C else 0.0, relevant=rel,
                        hallucinated=not any_single and not all_, lexical_ok=bool(st) and len(st & ct) / len(st) >= 0.25))
    return out
