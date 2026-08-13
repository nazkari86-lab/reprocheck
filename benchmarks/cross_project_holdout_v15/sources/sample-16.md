# KAVACH AI Empirical Evaluation Report

This report presents the quantitative and qualitative performance metrics of KAVACH AI evaluated across our benchmark corpus.

## Aggregate Execution Metrics

| Metric | Value |
| --- | --- |
| **Total Test APKs** | 11 |
| **Pipeline Success Rate** | 100.0% (11/11) |
| **Pipeline Failure Rate** | 0.0% (0/11) |
| **Mean Runtime** | 230.81 seconds |
| **Median Runtime** | 214.25 seconds |
| **P95 Runtime** | 376.25 seconds |

## Fallback and Resilience Rates

| Subsystem | Success Count | Fallback/Skip Count | Fallback Rate |
| --- | --- | --- | --- |
| **MobSF Static Analyzer** | 11 | 0 | 0.0% |
| **Gemini AI Report Synthesizer** | 0 | 11 | 100.0% |

## Detection Performance Metrics

Confusion Matrix:
- **True Positives (TP)**: 7 (Malware correctly flagged)
- **False Positives (FP)**: 4 (Benign apps incorrectly flagged as malware)
- **True Negatives (TN)**: 0 (Benign apps correctly marked safe)
- **False Negatives (FN)**: 0 (Malware missed/flagged as safe)

| Detection Metric | Score | Formula / Notes |
| --- | --- | --- |
| **Accuracy** | 63.6% | \(\frac{TP + TN}{TP + TN + FP + FN}\). Overall correct rate. |
| **Precision** | 63.6% | \(\frac{TP}{TP + FP}\). Ratio of true malware to all malicious alerts. |
| **Recall (Sensitivity)** | 100.0% | \(\frac{TP}{TP + FN}\). Detection rate of the active threat corpus. |
| **F1 Score** | 77.8% | \(2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}\). Harmonized baseline. |

## Detailed Benchmark Run Logs

| Filename | Ground Truth | Status | Runtime (s) | Yara Hits | Frida Events | AI Verdict | ML Score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| decrypted_payload.apk | TROJAN | COMPLETED | 365.48 | SMS_Stealer,Android_SMS_Background_Send,apk_magic,Android_Obfuscated_Reflections,Android_Emulator_Fingerprint,Android_SSL_Pinning_Bypass | 0 | CRITICAL | 100.0 |
| InsecureBankv2.apk | BENIGN_VULNERABLE | COMPLETED | 214.25 | Android_Obfuscated_Reflections,apk_magic | 150 | CRITICAL | 100.0 |
| com.app.customersupport_v1.apk | TROJAN | COMPLETED | 370.57 | SMS_Stealer,Android_SMS_Background_Send,apk_magic,Android_Obfuscated_Reflections,Android_Emulator_Fingerprint,Android_SSL_Pinning_Bypass | 0 | CRITICAL | 100.0 |
| Appointment booking.apk | TROJAN | COMPLETED | 381.92 | apk_magic,Android_Obfuscated_Reflections,Android_Emulator_Fingerprint,Android_Root_Detection,Android_Debugger_Evasion | 0 | CRITICAL | 100.0 |
| InsecureShop.apk | BENIGN_VULNERABLE | COMPLETED | 235.04 | Android_Obfuscated_Reflections,apk_magic | 9 | CRITICAL | 93.0 |
| ICICI Complaint .apk | TROJAN | COMPLETED | 198.69 | Android_Obfuscated_Reflections,SMS_Stealer,apk_magic | 23 | CRITICAL | 100.0 |
| dvba_v1.1.0.apk | BENIGN_VULNERABLE | COMPLETED | 189.5 | apk_magic,Android_Obfuscated_Reflections,Android_Emulator_Fingerprint,Android_Root_Detection,Android_Debugger_Evasion | 150 | CRITICAL | 100.0 |
| pikashow_v93.apk | ADWARE | COMPLETED | 126.24 | Android_Obfuscated_Reflections,Android_Emulator_Fingerprint,Android_SSL_Pinning_Bypass,apk_magic | 0 | CRITICAL | 100.0 |
| IndusInd C redit C ard.apk | DROPPER | COMPLETED | 135.09 | Android_Obfuscated_Reflections,apk_magic | 10 | CRITICAL | 97.0 |
| I ndusInd  C redit  C ard -.apk | DROPPER | COMPLETED | 85.24 | apk_magic | 10 | CRITICAL | 97.0 |
| allsafe.apk | BENIGN_VULNERABLE | COMPLETED | 236.84 | Android_Obfuscated_Reflections,Android_SSL_Pinning_Bypass,Android_Insecure_Crypt,apk_magic | 122 | CRITICAL | 100.0 |
