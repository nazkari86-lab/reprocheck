# ReproCheck 0.17: спецификация научного усиления

Статус: утверждено для локальной реализации 2026-08-12.

## Цель

Усилить ReproCheck как проверяемое исследование, не выдавая подготовленную
инфраструктуру за независимую внешнюю валидацию.

## Текущая граница доказательств

- Основной evidence-layer эксперимент является авторским controlled study.
- Переход к первичным артефактам поддержан на замороженной матрице.
- Отдельное преимущество полного graph layer статистически не установлено.
- Завершенных независимых внешних рецензентов и human-study участников нет.

## Новый алгоритмический результат

Для finding `claim_metric_mismatch` система строит **source-grounded minimal
contradiction witness**. Witness обязан содержать:

1. finding с объявленным кодом;
2. claim, который поднимает finding;
3. metric observation, противоречащий claim;
4. report artifact, содержащий claim;
5. source artifact, из которого получена metric observation;
6. все четыре типизированные связи между этими объектами.

Если один artifact одновременно выполняет обе source-роли, он учитывается один
раз. Среди всех допустимых подмножеств выбирается подмножество с минимальным
числом узлов; равенство разрешается канонической сортировкой. Полный перебор
подмножеств ограничен релевантным typed neighborhood, а результат включает
число проверенных подмножеств и найденную нижнюю границу.

Слово `minimal` относится только к этой публичной verifier-семантике. Оно не
означает минимальный научный эксперимент, минимальный исходный архив или
глобально кратчайшее доказательство в произвольной provenance-модели.

## Проверяемость

Отдельная команда verifier должна независимо проверить:

- checksum исходного audit certificate;
- checksum witness;
- внутренние node/edge digests;
- наличие всех обязательных typed relations;
- численное противоречие с учетом tolerance;
- соответствие artifact descriptors исходному certificate;
- заявленную кардинальную минимальность повторным поиском.

Изменение любого значения, digest, relation или source binding обязано приводить
к отказу.

## Controlled benchmark

Сравниваются три представления одного finding:

1. полный evidence graph;
2. прямой neighborhood finding;
3. exact minimal witness.

Primary outcomes: число узлов и serialized bytes. Secondary outcomes: время
verification и tamper rejection. Benchmark показывает компактность и
проверяемость на объявленных случаях, но не реальную экономию времени reviewer.

## Внешняя валидация

Локально должны быть готовы два разных протокола:

- dual blind annotation для проверки надежности labels;
- новый preregistered holdout с evaluator freeze до раскрытия source contents.

Результаты остаются `not executed`, пока реальные независимые люди не подпишут
и не заморозят ответы. AI-ответы не считаются внешними рецензиями.

## Human study

Локально готовится randomized crossover protocol, packet builder и scorer.
Эксперимент нельзя запускать до необходимых школьных/SRC/IRB разрешений и
информированного согласия участников. До этого запрещено заявлять экономию
времени или снижение reviewer error.

## Network boundary

`reprocheck serve` остается loopback-only по умолчанию. Любой non-loopback host
требует явного `--allow-network` и предупреждает, что приложение не реализует
authentication, TLS или multi-user isolation.

## Definition of done

- Все новые verifier paths fail closed и покрыты tamper tests.
- Controlled benchmark воспроизводим одной командой и имеет frozen baseline.
- External holdout и human-study пакеты проверяют собственные locks и не могут
  быть ошибочно представлены как завершенные.
- Документация различает capability, controlled evidence и external evidence.
- Полный `make gate` проходит без изменения старых frozen результатов.
