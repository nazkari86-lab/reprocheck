# Accuracy benchmark

Scores whether a basket answer is **correct**, which no other test in this repo
does. The existing suite asserts the absence of bugs already found. That is the
blind spot that let a roll-count pattern with 196 catalog false positives pass its
author's own verification: the check confirmed what it assumed.

> **The label set is MACHINE-PROPOSED and pending human review.** Until a
> Hebrew-speaking human has read `src/scripts/accuracy/labels/staples.ts`, treat
> the output as a **consistency** measure (did behaviour change?) and not as an
> **accuracy** measure (is behaviour right?). Do not quote it externally.

## Run it

```bash
# full run, writes a baseline
pnpm --filter @super-mcp/api accuracy -- --out=baseline.json

# one or two baskets while iterating
pnpm --filter @super-mcp/api accuracy -- --only=topup,produce --concurrency=1

# compare a change against a baseline; exits 1 on regression
pnpm --filter @super-mcp/api accuracy -- --baseline=baseline.json --tolerance=0.02
```

Needs `DATABASE_URL` and `BASKET_CONTINUATION_SECRET` in `.env`. It calls the
basket service directly rather than over HTTP, so no server is required. A full
10-basket run is minutes; individual baskets ranged 2.4s to 41s, the slow ones
being cold buffer cache.

## The five metrics

| metric | meaning | gated on regression |
| --- | --- | --- |
| `resolutionAccuracy` | lines resolving to the right KIND of product | yes |
| `localAvailability` | checked lines whose SKU is stocked widely enough nearby | no |
| `coverage` | requested lines priced at the recommended store | yes |
| `conditionalExposure` | priced lines needing a club card or a coupon | no |
| `imputedShare` | share of the headline total that is estimated, not observed | no |

The last two are not gated because they describe the catalog and the promotion
landscape as much as the code. Failing a build on them would punish a data refresh.
`localAvailability` is not gated for a sharper reason, below.

### Correctness and availability are two scores, not one

`resolutionAccuracy` answers "is this the right kind of thing?" and reads only the
token, class, preparation and forbidden-pattern criteria in `accept`.
`localAvailability` answers "do the storefronts near this shopper actually carry
it?" and reads `minNearbyStoreShare`, which sits on the label **beside** `accept`
rather than inside it.

They were one number until 2026-08-09, and it inverted the score: a widely stocked
WRONG product beat a thinly stocked right one. The harness accepted
`עוף טוב פסטרמה דבש דק דק 110ג` (110g of honey deli pastrami) for `עוף`, and
`עגבניות שרי צהוב פרמיום ארוז` for 1 kg of `עגבניות`. Fixing the resolver so both
returned the plain staple moved `resolutionAccuracy` **down**, 97.0% to 95.0%, all
of it in `vegetable_fresh`, with the stated reason `stocked at 1/7 serving storefronts
(14%), need 20%`. Coverage rose and `imputedShare` halved across the same two runs,
so the answer got better while the headline metric got worse.

Two consequences worth keeping in mind when reading a run:

- `localAvailability` is measured on every checkable line, **accepted or not**, so
  the two numbers never move for each other's reasons. Its denominator is
  `availabilityCheckedLines`, not `requestedLines`: only 23 of the 61 labels state a
  threshold, and a line is only checked when the product was resolved and the
  storefront scope is known. Two runs compare on this metric only when that count
  matches.
- It is reported, never gated. The denominator is the 7 or 8 storefronts that
  deliver to the address, so one storefront dropping a SKU swings a whole line, and
  the thresholds were calibrated against 143 physical branches. Treat a shortfall as
  a hint until they are re-derived on storefront counts.

### A line the system did not resolve counts as wrong

`resolutionAccuracy` judges the label only once there is a resolution to judge.
Any `resolutionStatus` other than `resolved` fails the line outright, with the
status as the stated reason, and the line stays in the denominator.

That gate is not decoration. When the resolver omits a line it echoes the
shopper's query back as the item's `name` (`omitOutcome` sets
`name: query ?? item.name`), and the echo then satisfies the label written for the
product: `תפוחי אדמה` carries the `תפוח` that `potato` requires, and
`ביצים תבנית 12` carries both the `ביצ` and the `12` that `eggs-tray-12` requires.
The class gate cannot object either, because a line with no product id has no facts
and a missing fact is never a failure. So 4 of the 100 lines scored as correct
resolutions for a resolution that never happened: `potato` in `weekly-large` and
`produce`, `eggs-tray-12` in `weekly-small` and `controls`. `coverage` had them all
along, since all four are the unpriced lines, but the headline read 99.0% where the
honest figure is 95.0%.

Failed, not excluded from the denominator. The denominator already keeps the lines
of a basket that threw, because a benchmark must never reward the system for being
unable to answer, and one declined line is the same thing at a smaller scale. That
is the opposite of how an unaskable availability line is treated, and deliberately
so: there the *label* states no threshold, so the question cannot be put at all,
while here it was put, to a catalogue that plainly carries potatoes and 12-egg
trays.

`needs_confirmation` fails too, under its own reason so the report can tell a
declined line from a dead end. Declining is the better failure, since the resolver
returns it rather than guess a product it is not sure of, but better than wrong is
not right. It does not arise here in practice: the harness runs
`resolutionMode: "fast"`, and the fast policy only ever emits `resolved` or
`unresolved`.

### `coverage` scores one store, so adding stores moves it

`coverage` grades the storefront the ranking picked, which makes it a measure of
the *choice* as much as of the catalogue. Adding options can lower it: pulling
the 25 Wolt venues into the local catalogue moved coverage from 96.0% to 93.0%
in one run, because a cheaper storefront with a thinner shelf started winning
baskets that a broader one used to take. Nothing resolved worse;
`resolutionAccuracy` held at 88.0% across exactly that change. The choice is not
even stable between two runs minutes apart: see the baseline note below.

The physical surface had the same property through a different mechanism, and it
is worth keeping as the cautionary case. There the ranking preferred *near*
stores, so a store that mislocated itself scored better: Rami Levy Ramat HaHayal
had a polluted address (`דבורה הנביאה 127&#x0D;`), failed to geocode, fell back
to the Tel Aviv centroid 0.6 km from the benchmark origin when it is really 7 km
away, and geocoding it correctly *dropped* coverage from 95.0% to 92.0%.

So before treating a `coverage` fall as a regression, ask what changed about the
store set. A **fall** here can mean the numbers stopped flattering themselves.
`resolutionAccuracy` does not depend on which store won and is the cleaner
signal for resolution changes.

## Baseline, measured on the delivery surface

Measured 2026-08-09 against `optimize_delivery`, the surface that is mounted.
Herzliya and nearby locations, 10 baskets, 100 scored lines, 57 storefronts in
the catalogue of which 7 to 8 deliver to the benchmark address (14 for the Tel
Aviv basket).

```
resolutionAccuracy   95.0%   95 of 100 requested lines
localAvailability    90.6%   48 of 53 checked lines
coverage             95.0%
conditionalExposure   2.1%
imputedShare          1.1%
```

### Current, 2026-08-11

Re-measured after the resolution and pricing work of 2026-08-10/11, on the same 100-line
denominator and the same 53 availability-checked lines, so these ARE comparable to the
figures above. Three consecutive runs agreed exactly, including one before and one after
a change to promotion pricing.

```
resolutionAccuracy   99.0%   99 of 100 requested lines
localAvailability    86.8%   46 of 53 checked lines
coverage             98.0%
conditionalExposure   1.0%
imputedShare          2.0%
```

Correctness failures went 5 to 1: the four `potato` / `eggs-tray-12` omissions are gone.
`localAvailability` fell 90.6% to 86.8%, which is the metric this file already warns is
not gated and tracks the storefront set rather than the code. The 2026-08-09 runs scoped
7 to 8 serving storefronts; these scoped 11 to 15, and a share metric with a larger
denominator falls without anything resolving worse.

Nine runs across that day agreed on `coverage`, `localAvailability` and
`imputedShare` exactly. `resolutionAccuracy` moved twice, both times because the
metric itself changed and never between two runs of the same code (see below).

`conditionalExposure` is the one that moves on its own. It read 1.1% in three of
the first four runs: the `controls` basket's winning storefront flipped from Rami
Levy to Shufersal between two runs minutes apart, taking one line from an
unconditional price to a club price. Nothing resolved differently and `coverage`
did not move. The last five runs, two before the unresolved-line fix and three
after, all read 2.1% with `controls` won by Shufersal, so the flip is real but not
frequent. A tight `--tolerance` is safe for the gated metrics, and
`conditionalExposure` follows the store choice, which is the same caveat `coverage`
carries above.

### `resolutionAccuracy` is not comparable across 2026-08-09

It changed meaning twice that day, and it lands on the number it started from.
**95.0% before and 95.0% after are not the same measurement**, and they do not
share a single failing line.

1. **Availability split out.** The same run scored 95.0% before and 99.0% after,
   on identical resolutions. Availability used to be able to fail a line, and 4 of
   the 5 failures in that run were availability shortfalls on products that were
   correct: `tomatoes` in three baskets and `eggs-l` in one. They now score in
   `localAvailability`.
2. **Unresolved lines stopped scoring as correct.** 99.0% down to 95.0%, again on
   identical resolutions: the 4 lines gained in step 1 were replaced, one for one
   by count and not at all by identity, with the 4 omitted lines that had been
   passing on their echoed query. See the section above.

Nothing else moved across either change: `coverage` 95.0%, `requestedLines` 100,
`localAvailability` 90.6% of 53, `imputedShare` 1.1% in every run.

Older figures in this file predate both changes and are wrong in both directions
at once: availability could still fail a correct line, which pushed them down, and
an omitted line still passed on its echoed query, which pushed them up. The line to
date, all on the delivery surface unless noted:

| when | resolutionAccuracy | note |
|---|---|---|
| 2026-07-25 | 76.0% | physical branches, 143 in scope |
| 2026-08-07 | 91.0% | delivery surface, first run |
| 2026-08-08 | 97.0% | three resolver rounds (milk, soda, yogurt) |
| 2026-08-08 | 95.0% | availability upgrade fixed, and the metric *fell* |
| 2026-08-09 | 99.0% | availability split out into `localAvailability` |
| 2026-08-09 | 95.0% | unresolved lines stopped being credited for the echoed query |

The 76% to 91% step in particular is mostly the availability test getting weaker,
not resolution getting better: `minNearbyStoreShare` is a share of the stores in
scope and that denominator fell from 143 nearby branches to 7 or 8 serving
storefronts, so the same 0.25 went from "carried by 36 of 143" to "carried by 2 of
8". Availability produced 21 of 24 failures then. That whole confusion is what the
split removes.

### The 5 correctness failures

| lines | label | query | what it picked |
|---|---|---|---|
| 2 | `potato` | `תפוחי אדמה` | nothing; `weekly-large` and `produce` both omitted the line |
| 2 | `eggs-tray-12` | `ביצים תבנית 12` | nothing; `weekly-small` and `controls` both omitted the line |
| 1 | `oil-cooking` | `שמן` | שמן **זית** כתית מעולה 2 קלאסי 750 יד מרדכי |

The first four are the same two queries in two baskets each, and they are the
whole of the gap between the old 99.0% and the honest 95.0%. Both are ordinary
staples the catalogue carries, so an omission is a real miss and not a refusal to
guess: bare `תפוחי אדמה` and an explicit `ביצים תבנית 12` are exactly the two
shapes of query the harness exists to check, one generic and one specific. They
are also all four unpriced at the recommended storefront, which is why `coverage`
sat at 95.0% while the headline read 99.0%.

`oil-cooking` is the one wrong *product*: a bare `שמן` should be cooking oil.
`class_l3` is NULL for all 680 `oil_vinegar` products, so there is no class signal
to separate olive oil from canola, and olive oil vastly outnumbers canola in what
the storefronts price. Weakest categories are `eggs` 4/6, `oil_vinegar` 2/3 and
`vegetable_fresh` 10/12; every other category scores 100%.

### The 5 availability shortfalls

| lines | label | resolved to | stocked |
|---|---|---|---|
| 3 | `tomatoes` | עגבניות | 1/7, 2/14, 1/8, need 20% |
| 1 | `eggs-l` | ביצים L גדול 18 יחיד | 1/8, need 25% |
| 1 | `dish-soap` | סבון כלים 24% לפירות ללא בישום וצבע 750מ | 0/7, need 20% |

All three labels resolved to the RIGHT product, which is the point of scoring them
apart from correctness. Loose produce and fresh meat fragment into per-store SKUs,
so a low share there is structural rather than a bad answer, and both `tomatoes`
and `eggs-l` were flagged for human review before the split. `dish-soap` at 0 of 7
is the strongest case in the set and the one worth chasing: the recommended
storefront had to impute a price for it, which is the whole of this run's
`imputedShare`.

### A label that could never pass

`cucumbers` required the token `מלפפון` and the resolver returned a product named
`מלפפונים`. Hebrew final letters make that unmatchable: the singular ends in a
final nun (U+05DF) and the plural carries a medial one (U+05E0), so neither string
is a substring of the other and no shared prefix covers both. It failed three
lines per run against a query that was itself plural. Now `requireAnyToken`,
accepting either form, which is worth 3 points of the 91%.

Thirteen other labels use a `requireTokens` entry ending in a final letter
(`לחם`, `שמן`, `עוף`, `מים`, `יין`, `לימון`, ...). None of them is currently
failing, and every one of those tokens matches at least 30 catalogue names, so
they are live rather than broken. It is still the first thing to check when a
label fails against a product whose name obviously contains the word.

The `controls` basket, which uses only explicit requests (`קוטג׳ תנובה 5%`,
`אורז בסמטי`, `קוקה קולה זירו`, `ביצים תבנית 12`), scores **10/11**: its one miss
is `ביצים תבנית 12`, omitted rather than resolved. Until the unresolved-line fix it
read 11/11, and that clean sweep was the evidence for "the system handles a
specific query well and struggles with a bare generic one". The claim is now
weaker than it looked. The plain-versus-composite gap that `preparation`
(migration 025) exists to close is still real, but a specific query can also fall
off the end of the resolver entirely, and this basket is where that shows.

## How labels work

A label never names a product id, because the catalog is reingested and ids churn.
It pins the properties a correct answer must have:

```ts
{
  id: "rice",
  query: "אורז",
  category: "grains_rice",
  accept: {                                // correctness only, scores resolutionAccuracy
    requireTokens: ["אורז"],              // all must appear
    requireAnyToken: ["פסטה", "ספגטי"],   // at least one must appear
    forbidTokens: ["דפי", "מקלוני"],      // none may appear
    anyOfClassL2: ["grains_rice"],
    anyOfPreparation: ["plain"],
  },
  minNearbyStoreShare: 0.25,               // availability, scores localAvailability
}
```

`minNearbyStoreShare` is deliberately outside `accept`, so it cannot fail a line in
`resolutionAccuracy` and the type system rejects any attempt to put it back. It is a
share, not an absolute count, because the denominator moves: it was 143 branches
within 10km of Herzliya against 898 nationally, and since the ingest narrowed to
storefronts it is the 7 or 8 that deliver to the benchmark address. The first
iteration of this harness used absolute counts calibrated on national numbers and
false-failed correct answers.

A missing fact is never a failure. An unclassified product (`preparation` is NULL
for the whole catalog until the classifier runs) scores as acceptable, otherwise the
benchmark would punish the exact gap it exists to measure. Availability treats the
same gap differently: an unaskable line (no threshold, unresolved product, no store
scope) is left OUT of `localAvailability` rather than counted as a pass, so the
metric stays sensitive with only 53 of 100 lines in its denominator. A product
priced by none of the serving storefronts is a measured 0, not a missing fact.

A missing *resolution* is a failure, though, and none of the criteria above is even
consulted on one. The label is judged only when `resolutionStatus` is `resolved`,
because an omitted line arrives carrying the shopper's query as its name and would
otherwise pass its own label on the echo. That check lives in `evaluateAccept`,
ahead of every token test, and takes a required argument rather than an optional one
so a caller cannot forget to supply it.

## What a reviewer should check first

1. **Availability thresholds per category.** They no longer move the headline
   score, so this is now a question about `localAvailability` alone. Loose produce
   and fresh meat fragment into per-store SKUs, so a low share is structural rather
   than a bad answer: `tomatoes` scores 0/3 at 1 or 2 storefronts out of 7 to 14,
   and the produce labels that carry no threshold at all resolve to products at 1 to
   3 storefronts routinely (`cucumbers`, `banana`, `carrot`). Either lower the bar
   for `vegetable_fresh` and `fruit_fresh` or drop it there, and say which.
   Only 23 of the 61 labels state a threshold, so the ones that do are also an
   accident of who wrote them first.
2. **`oil-cooking` is the last failing line, and the label is RIGHT.** This entry read
   "the label is wrong, not the system" until 2026-08-11, on the grounds that
   `שמן קנולה עץ הזית סוגת` is canola oil from a brand called Etz HaZait. That case is
   already handled: the criterion is `forbidPatterns: ["(?<!עץ ה)זית"]`, and the negative
   lookbehind exempts the brand — verified, the pattern does not match that name. The
   product actually failing is `שמן זית כתית מעולה ... זיתא`, genuinely extra virgin OLIVE
   oil, so the label correctly rejects it and the RESOLVER is what is wrong: a bare `שמן`
   should be cooking oil. Do not "fix" the label to reach 100%; that hides a real miss.
   The cause is the one stated above — `class_l3` is NULL for all 680 `oil_vinegar`
   products, so nothing separates olive from canola and olive dominates what storefronts
   price. Closing it means classifying that category, not editing this file.
3. **Everything marked `confidence: "low"`**: `cottage` (should a bare קוטג׳ mean
   5%?), `dates` (does תמר לח satisfy תמרים, given the moist-form guard rejects it?).
4. **Then `confidence: "medium"`**, roughly a third of the set.

## Adding labels

Append to `STAPLE_LABELS` in `src/scripts/accuracy/labels/staples.ts`, then add the
id to a basket in `BENCHMARK_BASKETS`. `tests/accuracy/scorer.test.ts` enforces
unique ids, that every basket references a known label, that every label states at
least one positive criterion and has notes, and that no label forbids a token it
also requires. Those tests need no database.

Derive new queries from the catalog rather than intuition. In this data "most
stocked in the class" is emphatically not "the plain staple": the top-stocked item
in `grains_rice` is an instant noodle cup, in `bread` a crispbread, in `milk`
chocolate milk, and in `paper_goods` facial tissues.
