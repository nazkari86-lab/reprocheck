# ReproCheck Evidence Trial v19: дизайн слепого внешнего исследования

Статус: утверждён пользователем для максимального усиления ReproCheck перед
РКНП 2026-08-20.

## 1. Решение

ReproCheck не получает очередной набор parser rules. Следующий релиз строится
вокруг одного исследования:

> Повышает ли детерминированная проверка исходных экспериментальных артефактов
> точность обнаружения неподтверждённых численных утверждений по сравнению с
> анализом одного отчёта на ранее неизвестных ML-проектах?

Проверяемая единица — численное утверждение внутри result block. Для каждого
утверждения система возвращает ровно один статус:

- `supported`: доступные артефакты подтверждают значение в пределах tolerance;
- `contradicted`: доступный источник более высокого уровня даёт несовместимое
  значение;
- `not_verifiable`: данных недостаточно для подтверждения или опровержения.

`not_verifiable` не считается ошибкой автора. ReproCheck проверяет согласованность
переданных доказательств, а не научную истинность, репрезентативность датасета или
добросовестность исследователя.

## 2. Почему выбран этот подход

### Подход A: расширять parser новыми форматами

Это повышает development coverage, но повторяет уже наблюдавшийся цикл:
невиданный формат проваливается, затем post-inspection версия достигает высокого
результата на раскрытом корпусе. Такой результат полезен инженерно, но почти не
усиливает внешнюю валидность.

### Подход B: строить новый unlearning-проект EraseReady

Подход имеет социальную мотивацию, но требует нового репозитория, многократного
обучения моделей и проверки нестабильной гипотезы. Его исходная постановка также
пересекается с DAT, RUM, hardness-aware unlearning и per-example unlearning
evaluation. Для ближайшего РКНП риск незавершённого или неотличимого результата
слишком высок.

### Подход C: слепой evidence-layer trial — выбран

Он использует уже проверенные части ReproCheck, но проверяет их на новых данных с
замороженным evaluator. Проект получает один понятный научный вопрос, естественные
ошибки, отрицательные контроли, статистический анализ и демонстрацию проверяемого
witness. Это закрывает главный текущий пробел без разрастания продукта.

## 3. Границы исследования

### В scope

- англоязычные и русскоязычные открытые ML-репозитории;
- текстовые result blocks в Markdown, TXT, JSON, CSV и text-extractable PDF/DOCX;
- classification, regression, segmentation и detection metrics, уже входящие в
  опубликованный contract ReproCheck;
- supplied metric artifacts и raw predictions, которые можно безопасно
  пересчитать без исполнения кода проекта;
- естественные исправления, supported controls и честные `not_verifiable` cases;
- immutable source URLs, commit hashes, SHA-256 и полный inclusion log.

### Не в scope

- исполнение чужих notebooks или Python-кода;
- OCR сканов;
- универсальная проверка научной воспроизводимости;
- доказательство корректности выбранной метрики или датасета;
- оценка распространённости ошибок во всём GitHub;
- автоматическое обвинение автора в misconduct;
- объединение controlled mutations с естественными ошибками;
- использование раскрытых v6-v15 cases как внешнего теста новой версии;
- объявление незавершённого v18 валидным holdout.

## 4. Гипотезы и исходы

### H1 — основная гипотеза

Raw-artifact recomputation повышает recall естественных противоречий относительно
report-only проверки при false-accusation rate не выше 5%.

### H2 — дополнительная гипотеза

Supplied metric artifacts повышают проверяемое покрытие относительно report-only,
но уступают raw recomputation там, где supplied summary конфликтует с raw data.

### H3 — certificate hypothesis

Canonical minimal witness сохраняет тот же verdict, что и полный evidence graph,
при меньшем числе узлов и serialized bytes, а независимый verifier отклоняет все
заранее зарегистрированные tamper-классы.

H3 не является отдельным accuracy-arm: witness объясняет и переносит уже принятое
artifact-aware решение, но не получает дополнительной информации. Сравнивать его
accuracy с raw-recomputation arm как независимый метод запрещено.

### Primary outcomes

1. contradiction recall при false-accusation rate `<= 0.05`;
2. tri-state macro F1 для `supported`, `contradicted`, `not_verifiable`;
3. exact-result-block accuracy.

### Secondary outcomes

- precision и recall каждого класса;
- проверяемое coverage;
- abstention rate;
- cluster-bootstrap 95% CI по repository owner;
- paired exact McNemar test для H1;
- witness node count, edge count и canonical JSON bytes;
- build/verify runtime;
- tamper rejection rate.

Средние значения не заменяют per-repository интервалы. Документы одного owner не
считаются независимыми наблюдениями.

## 5. Корпус

### 5.1 Pilot frame

Небольшой pilot используется только для проверки yield, доступности файлов и
времени разметки. Все pilot repository owners добавляются в permanent exclusion
list. По pilot нельзя менять evaluator или выбирать удобные metric classes.

Pilot заканчивается до регистрации v19. Его результат не входит в итоговые
confidence intervals.

### 5.2 Main acquisition frame

Main frame формируется без запросов вида `fix metric`, `wrong accuracy` или
`correct results`. Источник — публичные merged pull-request events из заранее
зафиксированного временного окна. После детерминированной сортировки seed выбирает
кандидатов; eligibility проверяется по имени и содержимому changed files, но без
запуска ReproCheck.

Допустимый кандидат должен содержать хотя бы один result-bearing файл и один из
следующих evidence paths:

- supplied metrics artifact;
- raw prediction artifact;
- immutable before/after correction, позволяющий установить естественное
  численное противоречие;
- достаточный report block для честного `not_verifiable` control.

Каждый отказ получает один код из закрытой taxonomy. Нельзя молча заменять
неудобного кандидата следующим.

### 5.3 Минимальный информационный объём

До scoring корпус должен содержать:

- не менее 20 независимых repository owners;
- не менее 150 размеченных численных claims;
- не менее 20 естественных `contradicted` claims;
- не менее 30 `not_verifiable` claims;
- не менее 30 `supported` claims с raw или independently supplied evidence.

Если gate не достигнут в зарегистрированном frame, итог — `insufficient_sample`.
Нельзя расширять окно или менять seed после просмотра evaluator output. Новый frame
требует новой версии протокола и сохраняет неудачный результат.

### 5.4 Разделение страт

Итоговый отчёт всегда показывает отдельно:

- `natural_correction`;
- `natural_supported_control`;
- `natural_not_verifiable`;
- `controlled_mutation` — только capability benchmark;
- `unchanged_negative_control`.

Controlled mutations никогда не участвуют в основной оценке natural recall.

## 6. Blinding и preregistration

До retrieval фиксируются:

- evaluator wheel SHA-256;
- source commit;
- acquisition script SHA-256;
- analysis script SHA-256;
- schema versions;
- source window, seed, caps и ordering;
- inclusion/exclusion taxonomy;
- supported metric ontology;
- hypotheses, endpoints и success gates;
- список всех ранее виденных owners и files.

Разметчики получают source artifacts и инструкции, но не ReproCheck output.
Gold lock содержит SHA-256 полного adjudication payload. Только после проверки
registration и gold lock разрешается один scored evaluator run.

После этого:

- frozen result неизменяем;
- parser fixes получают новый номер версии;
- replay раскрытого корпуса называется development evidence;
- новый zero-shot claim требует нового owner-disjoint holdout.

## 7. Разметка

### 7.1 Gold contract

Для каждого claim фиксируются:

- owner, repository, immutable source commit и file path;
- result-block coordinates;
- verbatim claim span;
- canonical metric name, value, unit, split и model context;
- evidence tier и artifact binding;
- gold status;
- rationale code;
- reviewer confidence;
- adjudication history без удаления первоначальных ответов.

### 7.2 Независимость

Каждый scored block размечается двумя людьми независимо. Расхождения разрешает
третий adjudication pass без ReproCheck output. До начала работы школьный SRC или
организатор определяет, нужны ли формы для участия разметчиков. До такого решения
нельзя объявлять human study завершённым.

Публикуются raw agreement и Cohen's kappa с bootstrap CI. Высокое agreement не
заменяет проверку label correctness; низкое agreement становится отдельным
ограничением.

### 7.3 Неоднозначность

Claim получает `not_verifiable`, если:

- source не определяет нужный split/model context;
- metric artifact не связан с claim;
- raw artifact не содержит необходимых columns;
- unit conversion неоднозначна;
- несколько допустимых evidence sources конфликтуют без declared precedence.

Разметчик не угадывает намерение автора.

## 8. Экспериментальные arms

### Arm A — report only

Доступен только report artifact. Arm извлекает claims и может проверить
внутритекстовые противоречия, но не имеет права подтверждать raw computation.

### Arm B — report plus supplied metrics

Доступны report и structured metric artifacts. Arm проверяет согласованность
заявления с supplied evidence и обязан выявлять конфликт источников.

### Arm C — raw-artifact recomputation

Доступны report и поддерживаемые raw predictions/detections. Метрика независимо
пересчитывается по frozen public contract.

Все arms используют один extractor и различаются только evidence access. Нельзя
настраивать parser отдельно под arm.

### Certificate track

Для каждого verdict Arm C строит полный evidence graph и, когда rule поддержан,
canonical minimal witness. Отдельный verifier получает certificate, witness и
artifact directory, но не доверяет сериализованным verdict или minimality.

## 9. Анализ

Analysis script выполняет только preregistered расчёты:

1. проверяет registration, gold и source hashes;
2. проверяет owner-disjointness и отсутствие известных files;
3. строит confusion matrix каждого arm;
4. считает primary и secondary outcomes;
5. запускает owner-cluster bootstrap с зафиксированным seed;
6. выполняет paired McNemar test для Arm A против Arm C;
7. применяет Holm correction к дополнительным pairwise tests;
8. создаёт machine-readable result JSON и human-readable report;
9. сохраняет все failures и exclusions.

Success для H1 объявляется только если одновременно:

- Arm C имеет больший contradiction recall, чем Arm A;
- нижняя граница paired owner-bootstrap 95% CI для разницы выше нуля;
- false-accusation rate Arm C не превышает 5%;
- corpus прошёл minimum-information gate;
- evaluator, gold и analysis locks прошли проверку.

Если любой пункт не выполнен, H1 получает `not_supported`; используется именно это
обозначение, а не «почти доказано».

## 10. Архитектура trial package

Новый пакет располагается в `benchmarks/evidence_trial_v19/`:

```text
protocol.md
protocol.json
registration.json
exclusions.json
retrieve.py
prepare_review.py
lock_gold.py
score.py
schemas/
raw/
review/
gold/
results/
```

До scoring в git разрешены protocol, registration, schemas, immutable raw
metadata и label-hidden review packets. Private reviewer identities и
непубличные consent records не коммитятся. Публичный gold содержит только данные,
которые разрешено распространять.

CLI orchestration должна иметь отдельные fail-closed стадии:

```text
trial-register
trial-retrieve
trial-verify-registration
trial-prepare-review
trial-lock-gold
trial-score
trial-replay
```

`trial-score` отказывается работать, если найден незакрытый review packet,
изменён evaluator hash, не достигнут sample gate или отсутствует gold lock.

## 11. Работа с v18

Текущий v18 сохраняется как незавершённая retrieval attempt. Его raw responses,
registration и нулевой sample не переписываются и не входят в v19. Документация
должна объяснять, что API сообщил ненулевые `total_count`, но не вернул candidates;
это инфраструктурный null result, а не evidence качества ReproCheck.

Новая acquisition strategy получает новый номер именно для предотвращения
скрытой замены протокола.

## 12. Ошибки и безопасность

- Чужой код и notebooks никогда не исполняются.
- ZIP traversal, symlinks, duplicate members и size bombs отклоняются до audit.
- Network retrieval имеет limits на bytes, files, redirects и elapsed time.
- Partial downloads записываются отдельно и не становятся eligible artifacts.
- SHA-256 mismatch, missing commit или changed upstream bytes дают fail-closed.
- NaN, infinity, duplicate claim IDs и неизвестные units отклоняются.
- Ни один partial score не публикуется как основной результат.
- Ошибка одного repository сохраняется как failure row и не удаляет кандидата из
  denominator без preregistered exclusion code.

## 13. Тестирование

### Unit и property tests

- canonicalization и digest stability;
- tri-state verdict boundaries;
- unit conversion и tolerance edges;
- duplicate/missing context rejection;
- registration и gold-lock tampering;
- owner/file exclusion enforcement;
- permutation invariance для rows и evidence order;
- deterministic sampling и bootstrap.

### Integration tests

- полный synthetic miniature trial без сети;
- interrupted retrieval и deterministic resume;
- label-hidden review packet round trip;
- score refusal до gold lock;
- single-use scored run marker;
- clean-wheel evaluator replay;
- v18 isolation.

### Certificate tests

- node tamper;
- edge tamper;
- numeric-value tamper;
- artifact-byte tamper;
- context/tolerance tamper;
- deleted mandatory relation;
- non-minimal witness substitution;
- certificate/witness swap между cases.

Все зарегистрированные tamper cases должны быть отклонены. Это deterministic
integrity claim, а не статистическая оценка безопасности произвольного атакующего.

### Release gate

- Ruff formatting/check;
- Pyright;
- полный pytest/coverage gate;
- все старые frozen baselines;
- deterministic package build;
- clean-environment wheel smoke;
- v19 registration verification;
- отсутствие private review data в git.

## 14. Демонстрация РКНП

Демонстрация занимает не более трёх минут:

1. открыть невиданный report block с заявленным результатом;
2. показать, что report-only не может его проверить;
3. подключить raw predictions;
4. независимо пересчитать метрику;
5. показать `supported`, `contradicted` или `not_verifiable`;
6. открыть minimal witness;
7. изменить одну цифру и показать отказ verifier;
8. завершить frozen aggregate result, CI и ограничениями.

Демо не зависит от сети и не использует заранее скрытый holdout как театральный
пример. Публичный пример выбирается после завершения scoring из разрешённой части
corpus и помечается как раскрытый.

## 15. Claim register

Разрешённые формулировки зависят от результата:

- `implemented`: система детерминированно связывает поддерживаемые claims с
  предоставленными evidence artifacts;
- `verified locally`: verifier отклоняет зарегистрированные tamper cases;
- `observed on v19`: точные метрики только из immutable scored result;
- `not supported`: гипотеза не прошла хотя бы один success gate;
- `not evaluated`: не было достаточной выборки или независимой разметки.

Запрещённые формулировки:

- «проверяет достоверность научной работы»;
- «находит все ошибки»;
- «доказывает отсутствие data leakage»;
- «универсально улучшает рецензирование»;
- «заменяет научного руководителя или reviewer»;
- «точность 100%» без указания frozen corpus и denominator.

## 16. Definition of done

Исследование завершено только когда:

1. v18 сохранён неизменным как нулевая retrieval attempt.
2. v19 protocol, evaluator, acquisition и analysis зарегистрированы до retrieval.
3. Corpus проходит minimum-information gate либо публикуется честный
   `insufficient_sample`.
4. Две независимые разметки и adjudication завершены без evaluator output.
5. Один frozen scored run создан и криптографически связан с registration/gold.
6. Arms A-C оценены на одинаковых claims без post-hoc ontology changes.
7. Primary outcomes имеют owner-cluster confidence intervals.
8. H1 получает `supported` или `not_supported` строго по зарегистрированным gates.
9. Witness track отклоняет 100% зарегистрированных tamper cases.
10. Natural, controlled и negative-control evidence опубликованы раздельно.
11. Полный release gate и clean-wheel replay проходят.
12. README, scorecard, RKNP-текст и демо повторяют только разрешённые claims.

## 17. Потолок оценки

Сам документ и локальная реализация не дают 10/10. Максимальное усиление требует
следующей последовательности доказательств:

1. green engineering gate;
2. достаточный owner-disjoint frozen corpus;
3. независимая blinded annotation;
4. статистически поддержанная H1 без превышения false-accusation gate;
5. внешний replay другим человеком;
6. ясная защита личного вклада, отрицательных результатов и границ claims.

Без пунктов 3-5 проект остаётся сильной локальной инженерией. С ними ReproCheck
становится воспроизводимым исследованием с реальной внешней проверкой, а не
демонстрацией на уже изученных примерах.
