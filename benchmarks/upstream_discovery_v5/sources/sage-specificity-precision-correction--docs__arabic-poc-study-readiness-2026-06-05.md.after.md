# Arabic POC Study Readiness Brief

**Date:** 2026-06-05  
**Prepared for:** Study Owner, Clinical Lead, DPO  
**Purpose:** Decision gate before Arabic-speaking users interact with SageAI POC

---

## What Is Ready

The Arabic therapeutic experience is complete and verified:

- All 24 skills deliver Khaleeji Gulf Arabic responses with natively-authored Arabic examples and substantive cultural overrides (family hierarchy, Islamic framing, Gulf wellness context).
- The translation pipeline (Arabic input → English processing → Khaleeji output) is live.
- 20 Arabic knowledge articles in Gulf dialect are in the retrieval corpus.
- Cultural output validation, code-switching detection, and register calibration are active on every turn, including high-stakes escalation turns (fix verified 2026-06-05).
- Crisis path for English: S1 lexicon + S3 semantic OR-fusion. Measured recall: **37.1%** (86/232 CRADLE cases). Specificity: **95.7%** (178/186). Precision: **91.5%** (86/94). KPI is ≥95% recall — gap is **57.9 points**. (Corrected 2026-06-15: the 95.7% figure was previously mislabeled "precision"; it is specificity. True precision is 91.5%, given the frozen 2026-06-05 numerators — see tests/test_cradle_bench.py header.)

---

## What Is Not Ready: Crisis Detection in Arabic

Arabic and Arabizi crisis detection relies on **keyword matching only (S1 tier)**.

| Tier | English | Arabic / Arabizi |
|------|---------|-----------------|
| S1 Lexicon (keywords) | ✓ Live | ✓ Live — **load-bearing, sole tier** |
| S3 Semantic (BGE-M3) | ✓ Live — genuine backstop | ✗ Sub-threshold (0.70–0.74 vs threshold 0.8059) — not a fallback |
| S2 Classifier (MARBERT) | ✗ Not built | ✗ Not built |

**Arabic crisis recall is unmeasured.** No Arabic CRADLE equivalent exists. The 57.9-point English recall gap is driven by indirect and method-adjacent language that keywords cannot enumerate. The same structural gap exists in Arabic and is likely larger — Arabic crisis expression is more indirect by convention, and there is no regex tier (English has SK-EN-005; Arabic/Arabizi have none).

This is documented in code (`test_arabic_tier_guard.py`, `test_cradle_bench.py`) and is not a matter of interpretation.

---

## The Decision Required

**Who are the Arabic POC testers?**

This single question is the gate. Everything else is either already resolved or follows from this answer.

### Path A — Screened internal users (staff, researchers, colleagues)

Proceed. The therapeutic experience is high-quality and ready to test. Testers should be briefed that crisis detection in Arabic is keyword-only and that they should not bring real personal distress into sessions.

Minimum conditions:
- Briefing document for all testers stating the crisis detection limitation explicitly
- A visible, one-tap Arabic crisis resource in the UI (e.g., Ministry of Health line 800 46342) present in every session — not only on crisis trigger
- An escalation path if a tester does disclose real distress: named human contact, response commitment within N hours

### Path B — Real users, including those who may bring genuine distress

**Do not proceed without the following, in writing:**

1. **Clinical lead sign-off** on operating with keyword-only, unmeasured Arabic crisis recall in a population where distress expression is indirect. The sign-off must acknowledge the measured English recall gap (37.1%) and the fact that Arabic is currently unmeasured.

2. **DPO sign-off** under PDPL Article 4 — processing sensitive health data from Arabic-speaking users in a system with an unquantified crisis detection gap constitutes a material risk that requires documented acceptance.

3. **In-product Arabic crisis resource** — always visible, one tap, not conditional on crisis detection firing. This is the minimum safety net when the AI net has an unmeasured floor.

4. **Documented escalation path** with a named human, not a process. The crisis resource is not sufficient alone; there must be a person who receives an escalation and a commitment on response time.

MARBERT (Exp 4.2, v7 §5.1) is the architecture-specified solution for the recall gap. It is not a prerequisite for Path A. It is effectively a prerequisite for Path B at scale.

---

## What Happens Next

This document does not recommend for or against proceeding. It states what is true, what is unmeasured, and what each path requires.

The study owner and clinical lead determine which path applies. The DPO determines whether Path B requires a formal DPIA supplement before data collection begins.

No further code work is needed to unblock Path A. Path B requires MARBERT or an equivalent measure before general Arabic availability — this is a multi-week engineering item, separate from this brief.

---

**Reviewed by (engineering):** _________________ Date: 2026-06-05

**Clinical Lead sign-off:** _________________ Date: _________

**DPO sign-off:** _________________ Date: _________

**Study Owner decision (Path A / Path B):** _________________ Date: _________
