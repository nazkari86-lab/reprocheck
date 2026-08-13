# Kiértékelési eredmények

Ez a dokumentum a `make export-results` futásakor a `results/raw/` és `results/summary/` állományokból generálódik. A táblázatokban szereplő számok a létrehozott CSV fájlokból származnak.

## Kísérleti környezet

- Lokális Docker Compose környezet egy Kafka brokerrel.
- A minőségellenőrzés és az anomáliadetektálás PySpark Structured Streaming feladatként fut.
- A live drift detektor River ADWIN-t használ Kafka fogyasztó/termelő ciklussal.
- Az anomáliakísérlet determinisztikus, kísérleti Isolation Forest modellt használ, nem a produkciós `models/isolation_forest.joblib` fájlt.

## Futtatott forgatókönyvek

| scenario | records_or_events | primary_metric | primary_value |
| --- | --- | --- | --- |
| clean_baseline | 60 | quality_alerts | 0 |
| quality_degradation | 17 | quality_alerts | 8 |
| anomaly_detection | 60 | f1_score | 1.000000 |
| drift_sudden | 240 | detection_delay | 28 |
| drift_gradual | 260 | detection_delay | 16 |
| drift_recurring | 320 | detection_delay | 16 |
| small_load_performance | 300 | throughput_records_per_second | 35.223493 |

## Használt mérőszámok

- Adatminőség: riasztások száma hibatípusonként, tiszta rekordok száma.
- Anomáliadetektálás: true positive, false positive, false negative, precision, recall és F1.
- Drift: valós vagy közelítő driftpont, első detektálási pont, detektálási késleltetés és korai riasztások száma.
- Teljesítmény: előállított és elfogyasztott rekordok, futásidő, átviteli sebesség, átlagos, p95 és p99 késleltetés.

## Eredménytáblázatok

### Adatminőség

| scenario | issue_type | alert_count | clean_records |
| --- | --- | --- | --- |
| clean_baseline | none | 0 | 60 |
| quality_degradation | invalid_timestamp | 1 | 1 |
| quality_degradation | late_event | 1 | 1 |
| quality_degradation | malformed_record | 1 | 1 |
| quality_degradation | missing_pressure | 1 | 1 |
| quality_degradation | missing_sensor_id | 1 | 1 |
| quality_degradation | missing_temperature | 1 | 1 |
| quality_degradation | pressure_outlier | 1 | 1 |
| quality_degradation | temperature_outlier | 1 | 1 |

CSV: [quality_metrics.csv](../results/summary/quality_metrics.csv)

### Anomáliadetektálás

| scenario | true_positives | false_positives | false_negatives | precision | recall | f1_score | alerts | expected_anomalies |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| anomaly_detection | 10 | 0 | 0 | 1.000000 | 1.000000 | 1.000000 | 10 | 10 |

CSV: [anomaly_metrics.csv](../results/summary/anomaly_metrics.csv)

### Drift detektálás

| scenario | true_drift_point | approximate_drift_start | first_detection_point | detection_delay | alert_count | false_or_early_alerts |
| --- | --- | --- | --- | --- | --- | --- |
| drift_sudden | 100 | 100 | 128 | 28 | 1 | 0 |
| drift_gradual | 260 | 80 | 96 | 16 | 6 | 0 |
| drift_recurring | 80 | 80 | 96 | 16 | 2 | 0 |

CSV: [drift_metrics.csv](../results/summary/drift_metrics.csv)

### Teljesítmény

| scenario | records_produced | records_consumed | total_runtime_seconds | throughput_records_per_second | average_latency_seconds | p95_latency_seconds | p99_latency_seconds |
| --- | --- | --- | --- | --- | --- | --- | --- |
| small_load | 300 | 300 | 8.517043 | 35.223493 | 8.517750 | 8.517750 | 8.517750 |

CSV: [performance_metrics.csv](../results/summary/performance_metrics.csv)

## Ábrák

- [quality_issue_counts.png](../results/figures/quality_issue_counts.png)
- [anomaly_detection_summary.png](../results/figures/anomaly_detection_summary.png)
- [drift_sudden_timeline.png](../results/figures/drift_sudden_timeline.png)
- [drift_gradual_timeline.png](../results/figures/drift_gradual_timeline.png)
- [drift_recurring_timeline.png](../results/figures/drift_recurring_timeline.png)
- [throughput_summary.png](../results/figures/throughput_summary.png)
- [latency_summary.png](../results/figures/latency_summary.png)

## Rövid értékelés

- A tiszta baseline futás az aktuális pipeline alapzaját méri; a minőségi, anomália- és drift riasztások a Kafka kimenetekből kerülnek összesítésre.
- Az adatminőségi degradációs forgatókönyv kontrollált hibákat küld a nyers témába, ezért a hibatípusonkénti riasztásszámok közvetlenül összevethetők az injektált hibákkal.
- Az anomáliakísérlet oldalsó elvárt címkefájlt használ, így a produkciós Kafka üzenetséma változtatása nélkül számolhatók a klasszifikációs mérőszámok.
- A drift forgatókönyvek az ADWIN riasztási pontjait hasonlítják a hirtelen, fokozatos és visszatérő eloszlásváltozásokhoz.
- A teljesítményteszt kis terhelésű reprodukciós mérés; nem tekinthető produkciós benchmarknak.

## Ismert korlátok

- A Kafka környezet egy brokerrel és replikáció nélkül fut.
- A duplicate rekordok elnyomása működik a minőségellenőrzésben, de külön `duplicate_record` riasztás továbbra sincs implementálva.
- A drift detektor riasztást publikál, de automatikus újratanítást vagy modelladaptációt nem végez.
- A késleltetésmérés host oldali időbélyegekből számolt közelítés, nem elosztott tracing.
