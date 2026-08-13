# VEILDRA Formal Experiment Results
**Date:** April 23, 2026
**Environment:** Ubuntu 24.04, VirtualBox, Mininet Simulation
**Researcher:** Kostubh Kumar & Dr. Hemamalini V.

---

## Experiment 1 — Database Hunting Detection (10 trials)

| Trial | Detection Time | Reshape Time | Intent | Returning |
|-------|---------------|--------------|--------|-----------|
| 1 | 1.08ms | 314.25ms | database_hunting | No |
| 2 | 2.06ms | 274.61ms | database_hunting | No |
| 3 | 1.00ms | 283.34ms | database_hunting | No |
| 4 | 0.22ms | 202.52ms | database_hunting | No |
| 5 | 3.36ms | 236.96ms | database_hunting | Yes |
| 6 | 3.69ms | 218.02ms | database_hunting | Yes |
| 7 | 0.95ms | 199.61ms | database_hunting | Yes |
| 8 | 1.30ms | 240.24ms | database_hunting | Yes |
| 9 | 0.41ms | 222.21ms | database_hunting | Yes |
| 10 | 1.65ms | 278.42ms | database_hunting | Yes |

**Avg Detection: 1.67ms | Avg Reshape: 247ms | Accuracy: 10/10**

---

## Experiment 2 — Web Hunting Detection (10 trials)

| Trial | Detection Time | Reshape Time | Intent | Returning |
|-------|---------------|--------------|--------|-----------|
| 1 | 3.13ms | 234.49ms | web_hunting | No |
| 2 | 2.50ms | 244.47ms | web_hunting | No |
| 3 | 7.76ms | 219.46ms | web_hunting | Yes |
| 4 | 3.01ms | 252.85ms | web_hunting | Yes |
| 5 | 5.27ms | 655.18ms | web_hunting | No |
| 6 | 2.83ms | 403.95ms | web_hunting | Yes |
| 7 | 4.64ms | 452.27ms | web_hunting | Yes |
| 8 | 0.76ms | 363.14ms | web_hunting | Yes |
| 9 | 8.52ms | 444.98ms | web_hunting | Yes |
| 10 | 6.12ms | 454.60ms | web_hunting | Yes |

**Avg Detection: 4.45ms | Avg Reshape: 372.74ms | Accuracy: 10/10**

---

## Experiment 3 — Admin Hunting Detection (10 trials)

| Trial | Detection Time | Reshape Time | Intent | Returning |
|-------|---------------|--------------|--------|-----------|
| 1 | 1.11ms | 379.05ms | admin_hunting | No |
| 2 | 13.16ms | 374.64ms | admin_hunting | Yes |
| 3 | 2.99ms | 431.15ms | admin_hunting | No |
| 4 | 2.00ms | 387.89ms | admin_hunting | Yes |
| 5 | 2.92ms | 388.72ms | admin_hunting | Yes |
| 6 | 8.80ms | 440.90ms | admin_hunting | Yes |
| 7 | 2.22ms | 521.11ms | admin_hunting | Yes |
| 8 | 0.51ms | 379.02ms | admin_hunting | Yes |
| 9 | 19.26ms | 431.19ms | admin_hunting | Yes |
| 10 | 3.92ms | 328.13ms | admin_hunting | Yes |

**Avg Detection: 5.69ms | Avg Reshape: 406.18ms | Accuracy: 10/10**

---

## Experiment 4 — False Positive Test

| Traffic Type | Packets | Alert Triggered | Result |
|-------------|---------|----------------|--------|
| ICMP Ping h1 to h2 | 5 | No | PASS |
| ICMP Ping h2 to h1 | 5 | No | PASS |
| ICMP Ping h3 to h1 | 10 | No | PASS |
| ICMP Ping h1 to h3 | 20 | No | PASS |

**False Positive Rate: 0%**

---

## Experiment 5 — Baseline Comparison

| Feature | Static Network | VEILDRA |
|---------|---------------|---------|
| Threat Detection | None | 100% |
| Avg Detection Time | N/A | 3.94ms |
| Network Reshaping | Never | Automatic |
| Avg Reshape Time | N/A | 342ms |
| Attacker Map Valid | Always | Invalidated |
| Intent Classification | None | 100% |
| Returning Attacker | Undetected | 100% |
| False Positives | N/A | 0% |
| Deception Layer | None | Personalized |


---

## Experiment 6 — ML Model Performance (CICIDS2017 Dataset)

| Metric | Value |
|--------|-------|
| Dataset | CICIDS2017 Cleaned and Preprocessed |
| Total Samples | 200,000 |
| Normal Traffic Samples | 112,751 |
| Attack Samples (Port Scanning) | 87,249 |
| Training Samples | 160,000 |
| Test Samples | 40,000 |
| Algorithm | Random Forest (100 estimators) |
| Accuracy | 99.98% |
| Precision (Attack) | 1.00 |
| Recall (Attack) | 1.00 |
| F1 Score (Attack) | 1.00 |
| False Positive Rate | 0.00% |
| Detection Threshold | 0.3 |

---

## Overall Summary

| Metric | Value |
|--------|-------|
| Total Experiments | 30 behavioral + ML validation |
| Behavioral Detection Accuracy | 100% |
| ML Detection Accuracy | 99.98% |
| Overall False Positive Rate | 0% |
| Avg Detection Time | 3.94ms |
| Avg Reshape Time | 342ms |
| Returning Attacker Detection | 100% |
| Intent Classification | 100% |
| Attack Types Tested | 3 |
| ML Dataset Size | 200,000 samples |
