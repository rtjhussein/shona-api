"""One-off annotation strengthening for the repaired evaluation (2026-09-11).

Encodes source-backed semantic expectations (polarity, subject/object/
addressee, number, extension types/order/styles) into scored linguistic cases,
converts round_trip flags to generated-form readings, applies the evidence
audit (constructed full words -> rule_supported), and adds missing explicit
exhaustive booleans. All values derive from cited sources and the documented
response contract, never from implementation output.

After running, rebuild with tools/build_source_backed_corpus.py and record in
CORRECTIONS.md. This script is a migration aid, not part of the gate.
"""

import json
from pathlib import Path

BASE = Path("evaluation/source_backed/v1")


def person(surface, who, number):
    return {"surface": surface, "person": who, "number": number}


def nclass(surface, class_number):
    return {"surface": surface, "class_number": class_number}


def fin_pos(subj, stem, obj=None, exts=()):
    return {
        "subject": subj,
        "tense_aspect": {"value": "present"},
        "polarity": {"value": "positive"},
        "object": obj,
        "verb_stem": {"surface": stem},
        "extensions": list(exts),
    }


def fin_neg(subj, stem, obj=None):
    return {
        "subject": subj,
        "tense_aspect": None,
        "polarity": {"value": "negative"},
        "object": obj,
        "verb_stem": {"surface": stem},
        "extensions": [],
    }


def inf(polarity, stem, obj=None, refl=None, exts=()):
    return {
        "subject": None,
        "tense_aspect": None,
        "polarity": {"value": polarity},
        "object": obj,
        "reflexive": refl,
        "verb_stem": {"surface": stem},
        "extensions": list(exts),
    }


def imp(polarity, number, stem, obj=None, exts=(), mood_surface=None):
    mood = {"value": "imperative"}
    if mood_surface is not None:
        mood["surface"] = mood_surface
    return {
        "subject": None,
        "tense_aspect": None,
        "mood": mood,
        "polarity": {"value": polarity},
        "addressee": {"person": "second", "number": number},
        "object": obj,
        "reflexive": None,
        "verb_stem": {"surface": stem},
        "extensions": list(exts),
    }


NEU = {"type": "neuter"}
APP = {"type": "applicative"}
CAU = {"type": "causative"}
REP = {"type": "repetitive"}
REV = {"type": "reversive", "style": "long"}
REC = {"type": "reciprocal"}
PAS = {"type": "passive"}
ZVI_OBJ = {"surface": "zvi"}
ZVI_REFL = {"value": True}


def R(analysis_type, lemma_key, rule_id, slots):
    return {
        "analysis_type": analysis_type,
        "lemma": {"lemma_key": lemma_key},
        "rule_id": rule_id,
        "slots": slots,
    }


FIN_SLOTS = "fortune.verbal.slots.001"
FIN_NEG = "fortune.verbal.negation.001"
FIN_OBJ = "fortune.concord.object.001"
INF = "fortune.verbal.infinitive.001"
IMP = "fortune.verbal.imperative.001"
IMP_NEG = "fortune.verbal.imperative.negative.001"

# case_id -> (required readings, round-trip marker).
# Marker "self" reuses readings[0]; "rt-ise"/"rt-ise-pl" use the module
# readings below; None clears any round_trip flag.
SPEC = {
    "SRC-001": ([R("verb_form", "taura", FIN_SLOTS, fin_pos(person("ndi", "first", "singular"), "taura"))], "self"),
    "SRC-002": ([R("verb_form", "dzidzisa", FIN_SLOTS, fin_pos(person("u", "second", "singular"), "dzidzisa"))], "self"),
    "SRC-003": ([R("verb_form", "taura", FIN_SLOTS, fin_pos(person("u", "second", "singular"), "taura"))], None),
    "SRC-005": ([R("verb_form", "gona", FIN_SLOTS, fin_pos(person("ti", "first", "plural"), "gona"))], "self"),
    "SRC-006": ([R("verb_form", "da", FIN_SLOTS, fin_pos(person("u", "second", "singular"), "da"))], "self"),
    "SRC-009": ([R("verb_form", "taura", FIN_NEG, fin_neg(person("ndi", "first", "singular"), "tauri"))], "self"),
    "SRC-010": ([R("verb_form", "ziva", FIN_NEG, fin_neg(person("ndi", "first", "singular"), "zive"))], None),
    "SRC-011": ([R("verb_form", "taura", FIN_NEG, fin_neg(person("u", "second", "singular"), "tauri"))], None),
    "SRC-012": ([R("verb_form", "taura", FIN_NEG, fin_neg(nclass("va", "2"), "tauri"))], None),
    "SRC-013": ([R("verb_form", "da", FIN_NEG, fin_neg(person("ndi", "first", "singular"), "di"))], None),
    "SRC-014": ([R("verb_form", "gona", FIN_NEG, fin_neg(person("ndi", "first", "singular"), "goni"))], None),
    "SRC-015": ([R("verb_form", "zadza", FIN_NEG, fin_neg(person("ti", "first", "plural"), "zadzi"))], None),
    "SRC-017": ([R("infinitive", "taura", INF, inf("positive", "taura"))], "self"),
    "SRC-018": ([R("infinitive", "zorora", INF, inf("positive", "zorora"))], None),
    "SRC-019": ([R("infinitive", "ziva", INF, inf("negative", "ziva"))], "self"),
    "SRC-020": ([R("infinitive", "fa", INF, inf("negative", "fa"))], None),
    "SRC-021": ([
        R("infinitive", "ziva", INF, inf("negative", "ziva", obj=ZVI_OBJ)),
        R("infinitive", "ziva", INF, inf("negative", "ziva", refl=ZVI_REFL)),
    ], None),
    "SRC-022": ([R("infinitive", "tora", INF, inf("positive", "tora", obj=ZVI_OBJ))], "self"),
    "SRC-025": ([
        R("infinitive", "ziva", INF, inf("positive", "ziva", obj=ZVI_OBJ)),
        R("infinitive", "ziva", INF, inf("positive", "ziva", refl=ZVI_REFL)),
    ], None),
    "SRC-027": ([R("imperative", "taura", IMP, imp("positive", "singular", "taura", mood_surface=""))], "self"),
    "SRC-028": ([R("imperative", "pinda", IMP, imp("positive", "singular", "pinda", mood_surface=""))], "self"),
    "SRC-029": ([R("imperative", "tenga", IMP, imp("positive", "singular", "tenga", mood_surface=""))], "self"),
    "SRC-030": ([R("imperative", "tengesa", IMP, imp("positive", "plural", "tengesa", mood_surface="i"))], "self"),
    "SRC-031": ([R("imperative", "taura", IMP, imp("positive", "plural", "taura", mood_surface="i"))], "self"),
    "SRC-033": ([R("imperative", "dya", IMP, imp("positive", "singular", "dya", mood_surface=""))], "self"),
    "SRC-034": ([R("imperative", "pa", IMP, imp("positive", "singular", "pe"))], None),
    "SRC-035": ([R("imperative", "dya", IMP_NEG, imp("negative", "singular", "dye"))], "self"),
    "SRC-036": ([R("imperative", "pinda", IMP_NEG, imp("negative", "singular", "pinda"))], None),
    "SRC-037": ([R("imperative", "putsa", IMP_NEG, imp("negative", "singular", "putsa"))], None),
    "SRC-038": ([R("imperative", "isa", IMP_NEG, imp("negative", "singular", "isa", obj=nclass("ri", "5")))], "rt-ise"),
    "SRC-039": ([R("imperative", "isa", IMP_NEG, imp("negative", "plural", "isa"))], "rt-ise-pl"),
    "SRC-041": ([R("verb_form", "ziva", FIN_OBJ, fin_pos(person("ndi", "first", "singular"), "ziva", obj=nclass("mu", "1")))], "self"),
    "SRC-043": ([R("imperative", "dya", IMP, imp("positive", "singular", "dye", obj=nclass("ri", "5")))], None),
    "SRC-045": ([R("infinitive", "tsvaira", INF, inf("positive", "tsvairwa", exts=[PAS]))], None),
    "SRC-046": ([R("infinitive", "ziva", INF, inf("positive", "zivika", exts=[NEU]))], "self"),
    "SRC-047": ([R("infinitive", "tema", INF, inf("positive", "temera", exts=[APP]))], "self"),
    "SRC-048": ([R("infinitive", "muka", INF, inf("positive", "mukisa", exts=[CAU]))], "self"),
    "SRC-050": ([R("infinitive", "tuka", INF, inf("positive", "tukurura", exts=[REP]))], "self"),
    "SRC-051": ([R("infinitive", "pfeka", INF, inf("positive", "pfekenura", exts=[REV]))], "self"),
    "SRC-052": ([R("infinitive", "pamhidza", INF, inf("positive", "pamhidzirana", exts=[APP, REC]))], "self"),
    "SRC-055": ([R("infinitive", "pa", INF, inf("positive", "pa"))], "self"),
    "SRC-056": ([R("infinitive", "dya", INF, inf("positive", "dya"))], "self"),
    "SRC-057": ([R("infinitive", "ti", INF, inf("positive", "ti"))], None),
    "SRC-058": ([R("infinitive", "nzi", INF, inf("positive", "nzi"))], None),
    "SRC-060": ([R("infinitive", "ambura", INF, inf("positive", "ambura"))], "self"),
    "SRC-061": ([R("infinitive", "enda", INF, inf("positive", "enda"))], "self"),
    "SRC-063": ([R("infinitive", "dya", INF, inf("positive", "dyira", exts=[APP]))], "self"),
    "SRC-065": ([R("verb_form", "ziva", FIN_OBJ, fin_pos(person("ndi", "first", "singular"), "ziva", obj=nclass("zvi", "8")))], "self"),
    "SRC-070": ([R("infinitive", "tapa", INF, inf("positive", "tapwa", exts=[PAS]))], None),
}

RT_ISE = R("imperative", "isa", IMP_NEG, imp("negative", "singular", "ise", obj=nclass("ri", "5")))
RT_ISE_PL = R("imperative", "isa", IMP_NEG, imp("negative", "plural", "ise"))

CT_SPEC = {
    "CT-LEX-01": ([
        R("verb_form", "taurisa", FIN_SLOTS, fin_pos(person("ndi", "first", "singular"), "taurisisa", exts=[])),
        R("verb_form", "taura", FIN_SLOTS, fin_pos(person("ndi", "first", "singular"), "taurisisa", exts=[CAU])),
    ], None),
    "CT-LEX-02": ([R("imperative", "taurisa", IMP, imp("positive", "singular", "taurisa", mood_surface=""))], None),
    "CT-AMB-02": ([R("imperative", "taurisa", IMP, imp("positive", "plural", "taurisa", mood_surface="i"))], None),
    "CT-VAR-01": ([R("imperative", "dya", IMP, imp("positive", "plural", "dya"))], None),
    "CT-TERM-01": ([R("verb_form", "ziva", FIN_NEG, fin_neg(person("ndi", "first", "singular"), "zivi"))], "self"),
    "CT-TERM-02": ([R("imperative", "pinda", IMP_NEG, imp("negative", "singular", "pinde"))], "self"),
    "CT-VIS-01": ([R("verb_form", "taura", FIN_SLOTS, fin_pos(person("ndi", "first", "singular"), "taura"))], None),
}

EVIDENCE_AUDIT = {
    "SRC-046": "rule_supported: lemma -ziv-ik- attested (Fortune 2.10.2.3.3); full ku-form constructed by the general ku- rule.",
    "SRC-047": "rule_supported: -tem-er-/-bik-ir- attested; full ku-form constructed.",
    "SRC-048": "rule_supported: -muk-is- attested; full ku-form constructed.",
    "SRC-050": "rule_supported: -tuk-urur-/-oror- attested; full ku-form constructed.",
    "SRC-051": "rule_supported: -chat-anur-/-pfek-enur- family attested; full ku-form constructed.",
    "SRC-052": "rule_supported: -pamhidz-ir-an- attested (Fortune 3.4.2.8, finite terminal); infinitive constructed.",
    "SRC-056": "rule_supported: -dya attested in finite/imperative/nominal use; ku-dya infinitive via general ku- rule.",
    "SRC-063": "rule_supported: -dy-ir- attested (Fortune mu-dy-ir-o); ku-form constructed.",
    "SRC-070": "rule_supported: passive -w-/-iw- free variation stated; kutapwa full form constructed (verbatim witness is kutsvairwa, FSI).",
}


def main():
    parts = {}
    for i in (1, 2, 3, 4):
        parts[i] = json.loads((BASE / f"corpus_part{i}.json").read_text(encoding="utf-8"))
    cases = {}
    for part in parts.values():
        for case in part["cases"]:
            cases[case["case_id"]] = case

    for cid, (readings, rt) in SPEC.items():
        case = cases[cid]
        analysis = case.get("analyze")
        assert analysis and analysis.get("expected_status") == 200, cid
        analysis["required_readings"] = readings
        analysis.setdefault("exhaustive", False)
        if rt == "self":
            case["round_trip"] = {"required_reading": readings[0]}
        elif rt == "rt-ise":
            case["round_trip"] = {"required_reading": RT_ISE}
        elif rt == "rt-ise-pl":
            case["round_trip"] = {"required_reading": RT_ISE_PL}
        else:
            case.pop("round_trip", None)

    for cid, (readings, rt) in CT_SPEC.items():
        case = cases[cid]
        analysis = case.get("analyze")
        assert analysis and analysis.get("expected_status") == 200, cid
        analysis["required_readings"] = readings
        analysis.setdefault("exhaustive", False)
        if rt == "self":
            case["round_trip"] = {"required_reading": readings[0]}

    for cid, note in EVIDENCE_AUDIT.items():
        case = cases[cid]
        case["evidence_class"] = "rule_supported"
        case["interpretation"] = "EVIDENCE AUDIT 2026-09-11: " + note + " " + case.get("interpretation", "")

    cases["SRC-042"]["search"]["required_readings"] = [
        R("infinitive", "dya", INF, inf("positive", "dya", obj=nclass("a", "6")))
    ]
    cases["SRC-025"]["search"]["required_readings"] = [
        R("infinitive", "ziva", INF, inf("positive", "ziva", obj=ZVI_OBJ)),
        R("infinitive", "ziva", INF, inf("positive", "ziva", refl=ZVI_REFL)),
    ]
    cases["CT-SEARCH-01"]["search"]["required_readings"] = [
        R("verb_form", "taura", FIN_SLOTS, fin_pos(person("ndi", "first", "singular"), "taura"))
    ]
    cases["CT-SEARCH-02"]["search"]["required_readings"] = [
        R("infinitive", "ziva", INF, inf("negative", "ziva"))
    ]
    cases["CT-SEARCH-03"]["search"]["prohibited_readings"] = [
        R("verb_form", "taura", FIN_SLOTS, {})
    ]
    cases["CT-AMB-01"]["search"]["expected_lexical_hits"] = [{"normalized_headword": "taurisa"}]

    leftovers = [
        cid for cid, case in cases.items()
        if case.get("round_trip") is True or case.get("round_trip") is False
    ]
    assert not leftovers, f"boolean round_trip flags remain: {leftovers}"

    for i, part in parts.items():
        (BASE / f"corpus_part{i}.json").write_text(json.dumps(part, ensure_ascii=False), encoding="utf-8")
    print(f"annotated {len(SPEC) + len(CT_SPEC)} cases + search blocks + {len(EVIDENCE_AUDIT)} audit notes")


if __name__ == "__main__":
    main()
