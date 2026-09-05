# Medical RAG Chatbot: Empirical Evaluation Report

**Evaluation Date:** 2026-09-02 12:39:17
**Primary LLM Model:** `mistral-small-latest`
**Embedding Model:** `mistral-embed` (1024-dim)
**Verifier Model:** `mistral-small-latest`
**Vector Store:** Qdrant (cosine similarity, patient-isolated)

---

## Executive Benchmark Summary

| Metric | Measured Score | Target Standard | Status |
| :--- | :---: | :---: | :---: |
| **Grounded-Answer Rate** | **80.0%** | ≥ 90.0% | [WARN] |
| **Unsupported-Claim (Hallucination) Rate** | **0.0%** | < 10.0% | [PASS] |
| **Retrieval Recall@5** | **90.0%** | ≥ 90.0% | [PASS] |
| **Abstention Accuracy** | **80.0%** | ≥ 95.0% | [WARN] |
| **Citation Precision** | **100.0%** | ≥ 95.0% | [PASS] |
| **Patient-Isolation Violations** | **0** | **0 (Zero Tolerance)** | [PASS] |
| **Verifier Audit Agreement** | **100.0%** | ≥ 90.0% | [PASS] |

---

## Benchmark Details & Test Breakdown

- **Total Test Cases Evaluated:** 10
- **Answerable Record Queries:** 5
- **Unanswerable Control Queries:** 5
- **Average Query Latency (RAG + Verifier):** 2.39 seconds

---

## Metric Definitions

1. **Grounded-Answer Rate:** Proportion of answers whose clinical statements are 100% supported by the cited retrieved patient excerpts.
2. **Unsupported-Claim Rate:** Proportion of answers containing fabricated metrics, unverified medications, or general knowledge absent from the context.
3. **Retrieval Recall@5:** Fraction of answerable queries where the ground-truth evidence chunk was successfully returned in the top-5 Qdrant vectors.
4. **Abstention Accuracy:** Ability of the chatbot to return *"Information not found in medical records."* when queries ask about unrecorded clinical facts.
5. **Patient-Isolation Violations:** Number of records retrieved from a different patient ID. (Expected: 0).
