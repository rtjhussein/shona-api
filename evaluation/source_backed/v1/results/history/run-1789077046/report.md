# Source-backed evaluation report (source-backed-eval-v1)
Code revision: 01e8ce79449cd9a7873694c2144c4b799d98dab9 (dirty worktree)
Evaluator: tools/evaluate_source_backed.py sha256:6d12381c76ec5a9d
Corpus: source-backed-eval-v1 sha256:7c9020fd5c40c9a7a654b37a8919f4c9aaa533c0671e7bce2c1c4522c0ddd30b
Cases: 101 total, 90 evaluated, 11 not evaluated (evidence-only), 159 endpoint calls.

## Metrics (raw numerators/denominators; incompatible measures are not blended)
### linguistic
- correct generation among scored supported requests: 30/30
- required-analysis recall (analyze required + round-trip + search morphology): 83/84
- explicitly prohibited readings produced: 0
- unadjudicated extra analyses: 5
- refusals of declared supported requests: 0 of 50 scored cases
- correct deferred/invalid-request handling: 1/1
- generation-to-analysis agreement: 30/30
- analysis-to-search agreement: 2/2
### contract
- correct generation among scored supported requests: 2/2
- required-analysis recall (analyze required + round-trip + search morphology): 10/12
- explicitly prohibited readings produced: 0
- unadjudicated extra analyses: 4
- refusals of declared supported requests: 0 of 31 scored cases
- correct deferred/invalid-request handling: 19/19
- generation-to-analysis agreement: 2/2
- analysis-to-search agreement: 3/3

Unresolved evidence: 2 (SRC-059, SRC-062)
Not evaluated (evidence-only, no flows): 11 (SRC-023, SRC-026, SRC-032, SRC-040, SRC-044, SRC-049, SRC-054, SRC-059, SRC-062, SRC-068, SRC-069)

## Failures by capability (triage classes are candidates for adjudication)
- AMB: 1/1 scored pass (4 total)
- CT-AMB: 2/2 scored pass (2 total)
- CT-INV: 6/6 scored pass (6 total)
- CT-LEX: 1/2 scored pass (2 total)
  - FAIL CT-LEX-01 [linguistic_rule_defect_or_lexical_data_gap]: analyze_required:{"analysis_type": "verb_form", "lemma": {"lemma_key": "taurisa"}, "rule_id": "fortune.verb: required reading not recovered among 2: verb_form/fortune.verbal.slots.001 lemma=-taurisa, verb_form/fortune.verbal.slots.001 lemma=-taura; analyze_required:{"analysis_type": "verb_form", "lemma": {"lemma_key": 
- CT-SEARCH: 4/4 scored pass (4 total)
- CT-SEQ: 1/1 scored pass (1 total)
- CT-TERM: 2/2 scored pass (2 total)
- CT-UNSUP: 12/12 scored pass (12 total)
- CT-VAR: 1/1 scored pass (1 total)
- CT-VIS: 1/1 scored pass (1 total)
- DEF: 1/1 scored pass (3 total)
  - EVIDENCE-ONLY SRC-068
  - EVIDENCE-ONLY SRC-069
- EXT: 7/7 scored pass (10 total)
  - EVIDENCE-ONLY SRC-049
  - EVIDENCE-ONLY SRC-054
- FIN-NEG: 7/7 scored pass (8 total)
- FIN-POS: 5/5 scored pass (8 total)
- IMP-NEG: 5/5 scored pass (6 total)
  - EVIDENCE-ONLY SRC-040
- IMP-PL-POS: 2/2 scored pass (2 total)
- IMP-SG-POS: 4/5 scored pass (6 total)
  - FAIL SRC-034 [linguistic_rule_defect_or_lexical_data_gap]: analyze_required:{"analysis_type": "imperative", "lemma": {"lemma_key": "pa"}, "rule_id": "fortune.verbal.i: required reading not recovered among 1: imperative/fortune.verbal.imperative.001 lemma=-pa
  - EVIDENCE-ONLY SRC-032
- INF-NEG: 3/3 scored pass (3 total)
- INF-POS: 5/5 scored pass (8 total)
  - EVIDENCE-ONLY SRC-023
  - EVIDENCE-ONLY SRC-026
- OBJ: 2/2 scored pass (3 total)
  - EVIDENCE-ONLY SRC-044
- STEM: 7/7 scored pass (9 total)
  - EVIDENCE-ONLY SRC-059
  - EVIDENCE-ONLY SRC-062

## Reproduce
python tools/build_source_backed_corpus.py --check-only
python tools/evaluate_source_backed.py --corpus evaluation/source_backed/v1/corpus.json --out evaluation/source_backed/v1/results
pytest tests/test_source_backed_evaluation.py -q
