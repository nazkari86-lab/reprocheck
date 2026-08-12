# ReproCheck multi-rule minimal witness: дизайн 0.18

Статус: предложено пользователем и зафиксировано перед реализацией 2026-08-12.

## Цель

Расширить канонический minimal witness с одного finding
`claim_metric_mismatch` до трех научно различимых семейств:

1. несоответствие заявленной и наблюдаемой метрики;
2. конфликт двух источников метрики (`metric_evidence_conflict`);
3. точное пересечение train/test (`exact_split_overlap`).

Результат должен оставаться компактным, детерминированным, source-grounded и
независимо перепроверяемым по исходному audit certificate и его артефактам.

## Не входит в scope

- универсальный язык запросов к provenance-графам;
- witness для normalized/group/near-duplicate leakage;
- утверждение, что minimal provenance witness как класс изобретен ReproCheck;
- утверждение об экономии времени человека без завершенного human study;
- раскрытие или использование зарегистрированного внешнего holdout 0.17;
- объединение естественных дефектов и авторских мутаций в одну оценку accuracy.

## Рассмотренные подходы

### 1. Три независимых builder/verifier

Прост в первой реализации, но дублирует checksum, canonicalization,
minimality, error handling и tamper-проверки. Высокий риск расхождения правил.

### 2. Универсальный graph-pattern DSL

Гибок, но добавляет второй язык, parser и собственную семантику. Для трех
правил это преждевременная сложность, которую трудно объяснить на РКНП.

### 3. Реестр строгих rule-adapter'ов — выбран

Общий pipeline отвечает за загрузку, привязку, canonicalization, digest и
повторный поиск. Каждый adapter отвечает только за допустимые typed grounding,
семантический predicate и обязательные артефакты. Это сохраняет индивидуально
доказуемую минимальность и не дублирует инфраструктуру.

## Архитектура

### Общий pipeline

`build_witness_file` принимает certificate, finding index и optional
`artifact_dir`. Он:

1. проверяет certificate и, если правило artifact-dependent, его артефакты;
2. выбирает adapter строго по finding code;
3. перечисляет все допустимые typed grounding;
4. проверяет семантический predicate каждого grounding;
5. выбирает минимум по `(node_count, edge_count, canonical node ids)`;
6. сериализует witness v2 и вычисляет digest.

`verify_witness_file` не доверяет заявленной минимальности. Он повторно
проверяет certificate/artifacts, node/edge digests, rule semantics и заново
строит канонический witness через тот же публичный rule contract. Сравнение
выполняется по всему payload.

### API rule-adapter

Внутренний immutable descriptor содержит:

- `finding_code`;
- `verifier_rule` с версией;
- `requires_artifacts`;
- функцию полного перечисления grounding;
- функцию вычисления canonical `rule_inputs`;
- функцию семантической проверки witness;
- человекочитаемую границу minimality.

Неизвестный finding code отклоняется. Автоматического fallback на
"ближайшее" правило нет.

## Контракты трех правил

### Claim metric mismatch

Правило сохраняет существующую семантику и v1-результат:

- finding;
- claim;
- contradicting metric observation;
- report artifact;
- metric source artifact;
- связи `raises`, `contradicts`, `contains` и `reports|recomputes`.

Минимум текущего простого случая: 5 узлов и 4 ребра. Численное расхождение
обязано превышать tolerance.

### Metric evidence conflict

Witness содержит:

- finding;
- ровно две metric observation одного имени и совместимого context;
- по одному source artifact для каждой observation;
- две связи `metric -> finding: flags`;
- две связи `artifact -> metric: reports|recomputes`.

Значения обеих observation должны совпадать со структурированными `values` и
`sources` finding с учетом порядка-независимого сопоставления. Разность должна
превышать audit tolerance. Канонический tie-break предпочитает пару с
лексикографически меньшими node ids после равенства размера.

Ожидаемый минимум обычного случая: 5 узлов и 4 ребра.

### Exact split overlap

Graph-only witness здесь недостаточен: наличие двух `flags` не доказывает
пересечение. Поэтому правило artifact-dependent и содержит:

- finding;
- train artifact;
- test artifact;
- две связи `artifact -> finding: flags`;
- canonical rule inputs: identity columns, число строк test, число точных
  пересечений и отсортированные SHA-256 отпечатки пересекающихся identity keys.

Builder и verifier независимо читают CSV, применяют те же declared identity
columns из audit parameters и воспроизводят exact overlap. Пустые identity
columns, отсутствующие столбцы, неоднозначные train/test artifact bindings,
несовпадение counts или hash-set приводят к отказу.

Минимум обычного случая: 3 узла и 2 ребра. Он minimal только в рамках правила,
где row-level доказательство хранится в canonical `rule_inputs`, а сами CSV
криптографически привязаны artifact descriptors.

## Версии и совместимость

- Новые witness используют schema `reprocheck.witness.v2`.
- Verifier продолжает принимать существующий v1 mismatch witness.
- CLI `witness` получает `--artifact-dir`; для artifact-dependent правила он
  обязателен, для остальных рекомендуется и проверяет реальные файлы.
- CLI `verify-witness` сохраняет текущий интерфейс.
- Старые certificate и evidence graph не переписываются.

## Benchmark

### Controlled multi-rule benchmark

Минимум 12 детерминированных случаев: четыре на каждое правило, включая
несколько допустимых grounding, совмещенные artifact-роли, дополнительные
несвязанные findings и tie-break. Для каждого случая сравниваются full graph,
one-hop neighborhood и exact witness, а также четыре независимые tamper-мутации.

### Source-derived benchmark

Минимум 30 audit cases строятся из уже замороженных реальных experiment
artifacts. Результат стратифицируется:

- `natural`: finding существовал без изменения source artifacts;
- `controlled_mutation`: дефект внесен детерминированно в копию реального
  артефакта;
- `negative_control`: исходный clean case.

Primary outcomes: witness build success для ожидаемого finding, independent
verification success, tamper rejection и отсутствие witness у negative
controls. Compactness публикуется отдельно по каждому rule. Если естественных
findings недостаточно, это показывается как corpus limitation; controlled
mutations не переименовываются в natural evidence.

Зарегистрированный unseen holdout 0.17 не открывается и не используется.

## Ошибки и безопасность

- Никакой partial witness не записывается при ошибке.
- CSV читается как данные, код/ноутбуки не исполняются.
- Используются существующие лимиты artifact size; benchmark имеет явный cap на
  число строк и общее время.
- Path traversal и несоответствие checksum отклоняются certificate verifier.
- NaN, infinity, duplicate node/edge ids и неизвестные relations отклоняются.
- Любая смена node, edge, rule input, certificate или artifact должна ломать
  verification.

## Тестирование

- unit tests каждого adapter и всех fail-closed ветвей;
- brute-force comparison на малых искусственных графах;
- permutation tests для порядка sources/values и CSV rows;
- tamper tests отдельно для node, edge, rule input, artifact и minimality;
- v1 compatibility tests;
- CLI tests для обязательного `--artifact-dir`;
- frozen baseline для controlled и source-derived benchmark;
- полный `make gate`, deterministic build и clean-wheel smoke-test.

## Документация и демонстрация

`make rknp-demo` должен последовательно показать все три witness, проверить их
и вывести компактную таблицу: rule, nodes, edges, source binding, verifier
result. RKNP-текст обязан говорить "три строго заданных verifier rules", а не
"универсальное объяснение любого дефекта".

## Definition of done

1. Все три правила строят канонический witness и независимо проверяются.
2. V1 mismatch witness не ломается.
3. Controlled benchmark покрывает минимум 12 случаев и 100% объявленных tamper
   cases отклоняются.
4. Source-derived benchmark содержит минимум 30 стратифицированных audit cases;
   natural и mutation evidence не смешиваются.
5. `make rknp-demo`, полный gate и clean-wheel smoke-test проходят.
6. Frozen holdout 0.17 и private human-study gold остаются неизменными.
7. Новые научные заявления соответствуют фактически полученным результатам.
