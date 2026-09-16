# Source-backed evaluation report (source-backed-eval-v1-proposed)
Code revision: 01e8ce7
Corpus: source-backed-eval-v1-proposed sha256:f40ed432e7f0c30a
Cases: 101 total, 81 scored.

## By capability (raw numerators/denominators; no blended %)
- AMB: 1/1 scored pass (4 total incl. unscored)
- CT-AMB: 2/2 scored pass (2 total incl. unscored)
- CT-INV: 6/6 scored pass (6 total incl. unscored)
- CT-LEX: 2/2 scored pass (2 total incl. unscored)
- CT-SEARCH: 4/4 scored pass (4 total incl. unscored)
- CT-SEQ: 1/1 scored pass (1 total incl. unscored)
- CT-TERM: 2/2 scored pass (2 total incl. unscored)
- CT-UNSUP: 12/12 scored pass (12 total incl. unscored)
- CT-VAR: 1/1 scored pass (1 total incl. unscored)
- CT-VIS: 1/1 scored pass (1 total incl. unscored)
- DEF: 1/1 scored pass (3 total incl. unscored)
- EXT: 7/7 scored pass (10 total incl. unscored)
- FIN-NEG: 7/7 scored pass (8 total incl. unscored)
- FIN-POS: 5/5 scored pass (8 total incl. unscored)
- IMP-NEG: 5/5 scored pass (6 total incl. unscored)
- IMP-PL-POS: 2/2 scored pass (2 total incl. unscored)
- IMP-SG-POS: 5/5 scored pass (6 total incl. unscored)
- INF-NEG: 3/3 scored pass (3 total incl. unscored)
- INF-POS: 5/5 scored pass (8 total incl. unscored)
- OBJ: 2/2 scored pass (3 total incl. unscored)
- STEM: 7/7 scored pass (9 total incl. unscored)

## Unscored/out-of-scope watch (20 total, 0 mismatched)

Unadjudicated extra analyses (non-exhaustive cases): 6

## Reproduce
python tools/evaluate_source_backed.py --corpus evaluation/source_backed/v1/corpus.json --out evaluation/source_backed/v1/results
pytest tests/test_source_backed_evaluation.py -q
