# ReproCheck: защита и демонстрация

## Структура семиминутной защиты

### 0:00-0:40 — проблема

«В статье написано: accuracy 94%. Но откуда reviewer знает, что это число
соответствует predictions, что train и test не пересекаются и что приложенный
файл не был заменен? Обычно эти проверки выполняются отдельно и вручную.»

### 0:40-1:20 — идея

«ReproCheck строит проверяемую цепочку: claim в отчете -> supplied metric ->
пересчет из predictions -> split/notebook checks -> artifact hashes -> evidence
graph -> certificate. Он проверяет согласованность предоставленных evidence, а
не истинность научной гипотезы.»

### 1:20-2:05 — гипотеза

«Основная гипотеза: первичные вычислительные артефакты позволят обнаружить
больше заранее определенных несогласованностей, чем текст и заявленные метрики,
без роста false alarms на clean controls.»

Показать четыре evidence levels. Не перечислять все форматы файлов и метрики.

### 2:05-3:15 — главный эксперимент

Показать одну таблицу:

```text
report only       1/12 defects, 0/7 false alarms
+ metrics         3/12 defects, 0/7 false alarms
+ artifacts       9/12 defects, 0/7 false alarms
+ verified graph 12/12 defects, 0/7 false alarms
```

«Главный подтвержденный переход — 3/12 -> 9/12: шесть улучшений, ноль регрессий,
exact McNemar p=0.03125. Graph добавил три integrity cases, но p=0.25, поэтому я
не заявляю статистически доказанное общее превосходство graph layer.»

### 3:15-4:05 — научная честность

«Первая frozen версия на новом формате получила recall 1.79%. Я сохранил этот
результат. После исправления стало 100%, но это development evidence. Затем я
заморозил новые holdouts: 94.89% и 87.80% recall. Это показывает не идеальность
parser, а дисциплину разделения zero-shot проверки и последующей доработки.»

### 4:05-4:50 — новизна и аналоги

«Static leakage analyzers, ReproZip, provenance models и artifact review уже
существуют. Мой вклад не в изобретении каждого компонента. Это единая typed
claim-to-evidence модель, детерминированный audit state и проверяемая цепочка от
байтов артефакта к численному claim.»

Показать только строку ReproCheck и 3 ближайшие группы аналогов. Полная таблица
должна находиться в приложении.

### 4:50-5:35 — практическая граница

«Reviewer может локально получить список supported, contradicted, verified и
not-verifiable claims. Загруженный notebook не исполняется. Это предварительный
аудит, а не замена экспертной оценки и не доказательство истинности статьи.»

### 5:35-6:20 — ограничения

«Текущие ограничения: bounded metric and notebook coverage, отсутствие
семантической гарантии, внутреннее происхождение большинства labels и ноль
завершенных external reviews. Для последнего уже создан blind protocol, но я не
выдаю готовую инфраструктуру за проведенный эксперимент.»

### 6:20-7:00 — вывод

«Эксперимент поддержал основную гипотезу на объявленной матрице: первичные
артефакты сделали наблюдаемыми дополнительные классы несогласованностей без
ложных срабатываний на семи controls. ReproCheck превращает проверку числа из
неформального доверия в ограниченную, повторяемую и проверяемую процедуру.»

## Offline demo за 90 секунд

До защиты открыть терминал в корне репозитория и выполнить `make install`.
Весь сценарий можно заранее проверить одной командой `make rknp-demo`.

Для максимально наглядного live-показа запустить `reprocheck serve`, открыть
<http://127.0.0.1:8000> и нажать «Показать живой пример». После аудита:

1. Показать один подтверждённый claim и одно расхождение.
2. Открыть «Карту доказательств».
3. Нажать `research_report.md`: подсветится путь от отчёта через predictions и
   пересчитанные метрики к конкретным выводам.
4. Нажать claim: справа показать строку отчёта, заявленное и наблюдаемое
   значение, уровень evidence и SHA-256 узла.
5. Нажать `train_split.csv`: показать связь файла с найденным split overlap.

Анимация визуализирует уже построенный проверяемый graph и не является
доказательством сама по себе. Все показанные карточки создаются из ответа
backend, а встроенный пример также проходит настоящий `run_audit`.

Для демонстрации именно своего проекта выбрать папку или один ZIP и запустить
аудит. Сначала показать Evidence Passport: это не субъективный балл, а точные
отношения «сколько выводов имеют evidence / сколько независимо пересчитано»,
проверенные слои и детерминированные следующие действия. Затем интерфейс покажет
роли, которые backend прочитал из
`reprocheck.json` или определил по именам, а после завершения сохранит пять
измеренных длительностей в блоке «Фактический ход backend». Это реальные границы
`run_audit`, а не анимационный таймер. Ручные поля можно использовать как
override, если роль файла определена неверно. Если manifest содержит несколько
экспериментов, web-интерфейс явно проверяет первый и показывает его `id`; полный
пакет экспериментов запускается командой `reprocheck check`.

ZIP распаковывается только после проверки traversal-путей, symlink, шифрования,
дубликатов и лимитов размера. Загруженный код при этом не исполняется.

### 1. Чистый эксперимент

```bash
reprocheck audit \
  --report benchmarks/external/sklearn-tabular/iris_report.md \
  --metrics benchmarks/external/sklearn-tabular/official_metrics.json \
  --metrics-selector iris \
  --predictions benchmarks/external/sklearn-tabular/iris_predictions.csv \
  --train benchmarks/external/sklearn-tabular/iris_train.csv \
  --test benchmarks/external/sklearn-tabular/iris_test.csv \
  --label-column target \
  --identity-columns sample_id \
  --average macro \
  --output outputs/rknp-clean.json
```

Ожидаемый результат: `status=passed`, `findings=0`.

### 2. Понятный corrupted example

```bash
reprocheck demo --output-dir outputs/rknp-corrupted
```

Ожидаемый результат: `status=needs_review`, три findings. Открыть
`outputs/rknp-corrupted/demo-audit.html` и показать claim mismatch и leakage.

### 3. Повреждение evidence

```bash
reprocheck verify \
  --certificate outputs/rknp-clean.json \
  --artifact-dir benchmarks/external/sklearn-tabular
```

Показать успешную проверку. Для демонстрации tamper не менять frozen benchmark:
работать только с копией certificate/artifact в отдельной временной папке.

### 4. Главная таблица одним вызовом

```bash
reprocheck ablation --output outputs/rknp-ablation.json
```

Расширенный набор integrity/corruption/representation/scalability заранее
проверяется командой `make expanded-experiments`. На основной защите показывать
только один результат из него: три семантические подмены проходят после полного
пересчета unsigned hashes, а доверенная Ed25519 signature обнаруживает 9/9.
Это демонстрирует понимание границы криптографической модели.

Если live demo нестабилен, использовать заранее сохраненный HTML/скриншот, но
не выдавать его за запуск в реальном времени.

## Что разместить на стенде

1. Проблема и один пример `94% в тексте != 91% из predictions`.
2. Схема `claim -> evidence -> verification`.
3. Таблица абляции 1/12 -> 3/12 -> 9/12 -> 12/12.
4. График или карточка frozen failure 1.79% и новых zero-shot results.
5. Короткая таблица аналогов и точная novelty statement.
6. Ограничения и `external reviewers completed: 0`.
7. QR-код на immutable GitHub release, commit и reproduction commands.

## Опасные вопросы жюри

**Где новизна?** Не в leakage или hashing отдельно. Новизна — audit-specific
typed claim-to-evidence architecture и экспериментальная оценка уровней evidence.

**Почему это не ReproZip?** ReproZip сильнее в захвате окружения для повторного
исполнения. ReproCheck не исполняет код и проверяет связи между claim,
предоставленными результатами, split и certificate.

**Static leakage существовал?** Да: Yang et al., NBLyzer, LeakageDetector.
ReproCheck не заявляет первенство; его notebook rules уже и входят в более
широкий audit protocol.

**Baseline тоже получил 40/40?** Да. На исходном корпусе сильный
format-aware baseline связан вничью с parser. Поэтому parser не является
центральным contribution.

**Почему v0.5 получила 1.79%?** Появился новый формат таблиц. Failure был
заморожен; исправленный результат помечен development и не выдан за zero-shot.

**Graph действительно лучше?** Он обнаружил три дополнительные integrity
атаки в контролируемой матрице, но общий эффект не статистически значим:
`p=0.25`. Capability показана, general superiority — нет.

**Кто создал ground truth?** Большая часть internal. Это ограничение. Two-person
blind protocol готов, но внешняя проверка еще не завершена.

**ReproCheck доказывает правильность статьи?** Нет. Только вычислительную
согласованность предоставленных evidence в объявленном scope.

**Почему не исполняется notebook?** Безопасность и детерминизм. Это осознанный
scope tradeoff, а не полная замена reproduction environment.

**Что конкретно сделали вы?** Отвечать только правдиво и отдельно перечислять
личный дизайн, код, эксперименты, помощь руководителя и AI-assisted части.

## Минимум знаний перед защитой

Ученик должен без текста объяснить:

- precision, recall, specificity и balanced accuracy;
- Wilson interval и почему observed 100% не означает универсальные 100%;
- парный McNemar test и почему `p=0.25` недостаточно;
- точное определение minimal witness и область, внутри которой доказана минимальность;
- почему one-hop neighborhood может быть меньше witness, но не является source-grounded доказательством;
- почему controlled benchmark 58.3%/67.7% не доказывает экономию времени человека;
- zero-shot, development set, preregistration и post-hoc change;
- SHA-256, canonical digest, Ed25519 и различие между ними;
- AST/data flow, exact/group/lexical leakage;
- почему certificate не равен scientific truth;
- каждый блок главной схемы и происхождение каждой цифры на стенде.
