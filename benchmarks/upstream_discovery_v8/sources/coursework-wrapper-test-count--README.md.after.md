# Temple of Gloom - Group Coursework (CSM100)

Our solution to the Temple of Gloom coursework. Jeremy Hunt explores an unknown
cavern to reach the Orb, then escapes with as much gold as he can carry before
the ceiling collapses. The score is the gold collected multiplied by the
exploration bonus, so both phases matter.

## Team
- Marijke
- Ajay
- Michael
- Jordy

## Links
- Trello board: https://trello.com/invite/b/6a30f5910fdb37f934d44899/ATTIbf1db34d20b211867dcd49d584a0f7734262067E/sdp-2026
- SCRUM meeting recordings: https://drive.google.com/drive/folders/1iRBGD-tmfkCqoGuVN1YM2RyL9LH-Eq3c?usp=drive_link

## Verify it works

Run these from the repository root (`coursework-group-csm100`). You need Java 20
installed. Gradle itself is handled by the wrapper (`./gradlew`), which downloads
it for you on first run, so you do not need Gradle installed separately.

Run all tests:

```
./gradlew :temple:test
```

If Gradle says the task is up to date and you want to force the tests to run
again, use:

```
./gradlew :temple:test --rerun-tasks
```

Run the solution on 100 random maps and print an average score:

```
./gradlew :temple:run -PchooseMain=main.TXTmain --args="-n 100"
```

Run a single map with the GUI so you can watch it:

```
./gradlew :temple:run -PchooseMain=main.GUImain --args="-s 42"
```

## What we built

We only write two methods, both in `student/Explorer.java`: `explore()` and
`escape()`. Everything under `game`, `gui` and `main` is provided and we do not
touch it. To keep things readable we split the real work out of `Explorer` into
small classes in the `student` package, so each piece does one job and can be
tested on its own.

## How we arrived at this implementation

Each of us prototyped an approach on our own branch first, then we compared them
and merged the strongest pieces into one solution. The branches are still on the
repository if you want to see the earlier work:

| Branch | Who | Approach explored |
|---|---|---|
| `jordy-implementation` | Jordy | Guided DFS explore, plus a Dijkstra safe-greedy escape (`GoldEscaper`). |
| `ajay_escape1` | Ajay | Two earlier escape heuristics: a smallest-detour approach and a gold-ratio approach. |
| `ajay_escape2` | Ajay + Marijke | Ajay's optimised final escape (Dijkstra plus a depth-limited branch lookahead) on top of Marijke's guided DFS explore. |
| `marijke_escape` | Marijke | Dijkstra safe-greedy escape (`EscapeSolver`) and the first shared test graphs. |
| `origin/michael-exploration` | Michael | Guided DFS explore with a full set of exploration tests. |

For **exploration** we all converged on the same idea, a depth-first search
guided by the distance-to-Orb hint. We looked at BFS and A\* too, but those
assume you can jump to any frontier tile, while the game only lets you move to an
adjacent tile, so guided DFS with backtracking fit the movement rules best.

For **escape** everyone shared the same safety rule (only detour for gold if you
can still reach the exit in time), and Ajay worked through three approaches to
decide which gold to go for:

1. **Detour** (`ajay_escape1`): head for the safe gold tile that adds the fewest
   extra steps compared with going straight to the exit, that is the smallest
   `(steps to the gold + steps from the gold to the exit) - (steps straight to
   the exit)`.
2. **Gold ratio** (`ajay_escape1`): instead of the smallest detour, head for the
   safe gold tile with the best gold per step, `gold / (steps to the gold + steps
   from the gold to the exit)`.
3. **Optimised branch lookahead** (`ajay_escape2`): rather than scoring a single
   gold tile, run a short depth-limited search down each neighbour branch and
   value the whole branch by gold per step. This picks up clusters of gold along
   a direction, not just one tile, and it is the version we kept.

The optimised approach scored best, so we took `ajay_escape2` as the base, kept
Marijke's guided-DFS explore that was already on it, and brought in Michael's
exploration tests and our escape tests. That combined branch is `escape_tests`.

## The algorithms

### Exploration (`ExploreSolver`)

`explore()` has to reach the Orb in as few steps as possible for a good bonus.
We know the grid distance to the Orb from our current tile and each neighbour,
but not the walls, so it is a guided search rather than a blind one.

1. Mark the current tile as visited.
2. If `getDistanceToTarget() == 0` we are on the Orb, so stop.
3. Sort the neighbours by their distance to the Orb, closest first.
4. For each unvisited neighbour: move there, recurse, and if the Orb was found
   return. Otherwise step back and try the next neighbour.

This is depth-first search with a heuristic: always try the direction that looks
closest to the Orb first, while still backtracking out of dead ends.

### Escape (`Dijkstra`, `SelectNextTarget`, `TargetSearch`, `NextStep`)

After picking up the Orb the map is revealed, the walls shift, gold appears, and
every edge now has a weight (a step cost). `escape()` has to reach the exit
before time runs out. Reaching the exit is the priority, because failing scores
zero, and collecting gold is the bonus on top.

1. Pick up any gold on the starting tile.
2. Run `Dijkstra` from the exit once, giving the cheapest cost from every tile to
   the exit. This is what the safety check uses.
3. Loop until we are on the exit. `SelectNextTarget` looks at each neighbour, and
   for the safe ones runs `TargetSearch`, a short depth-limited lookahead that
   estimates how much gold that branch is worth per step. It heads for the best
   branch and takes one step with `NextStep`, collecting any gold on the way.
4. When no safe gold branch is left, walk the shortest path straight to the exit.

The rule that keeps it safe: we only move toward a tile if, after reaching it,
the shortest path from there to the exit still fits in the time left. Since the
brief guarantees enough time for the shortest path at the start, this holds the
whole way, so the escape can never run out of time.

## Code structure (student package)

| Class | Job |
|---|---|
| `Explorer` | Entry point. Delegates `explore()` and `escape()`. |
| `ExploreSolver` | Guided depth first search for the exploration phase. |
| `Dijkstra`, `DijkstraResult`, `NodeDistance` | Shortest paths on the weighted escape graph. |
| `SelectNextTarget`, `TargetSearch`, `TargetSearchResult` | Value each safe branch and pick the best gold per step. |
| `NextStep` | The single adjacent move toward a chosen target. |

## Project layout

```
temple/
  build.gradle.kts
  src/main/java/
    game/            provided: the graph, tiles, game state (do not edit)
    gui/             provided: the Swing display
    main/            provided: TXTmain (headless) and GUImain
    student/         our code
      Explorer.java
      ExploreSolver.java
      Dijkstra.java  DijkstraResult.java  NodeDistance.java
      NextStep.java
      SelectNextTarget.java  TargetSearch.java  TargetSearchResult.java
  src/test/java/
    game/
      GraphHelper.java          shared escape graphs (needs the game package)
    student/
      DijkstraTest.java              \
      NextStepTest.java               |
      SelectNextTargetTest.java       | escape tests
      EscapeIntegrationTest.java      |
      AlwaysEscapesTest.java          |
      MockEscapeState.java           /
      ExploreSolverCorrectnessTest.java   \
      ExploreSolverHeuristicTest.java      |
      ExploreSolverGraphTest.java          |
      ExploreSolverEfficiencyTest.java     | explore tests
      ExploreSolverCycleTest.java          |
      ExplorerWiringTest.java              |
      ExploreGameSmokeTest.java            |
      MockExplorationState.java            |
      ExploreTestGraphs.java              /
```

## Testing

All tests run with JUnit 5 through `./gradlew :temple:test`. There are 39 in total,
15 for exploration and 24 for escape.

### Levels of testing

We test at a few levels, from fast and narrow to slow and realistic:

| Level | What it checks | How |
|---|---|---|
| Unit | The algorithm on small hand-made graphs | JUnit with `MockExplorationState` / `MockEscapeState` |
| Wiring | `Explorer.explore()` calls `ExploreSolver` | JUnit (`ExplorerWiringTest`) |
| Smoke | The real game engine runs without crashing | JUnit calling `GameState.runNewGame` |
| Manual GUI | Watch the explorer move and backtrack | Run `GUImain` and look |
| Benchmark | Score and bonus on real seeds | Run `TXTmain` with `-n` |

We build small graphs by hand and reuse them across tests instead of rebuilding
one each time. The escape tests share named maps in `game/GraphHelper` and drive
them through `MockEscapeState`; the exploration tests use `ExploreTestGraphs` and
`MockExplorationState` the same way.

### Exploration unit tests

| Test class | What it checks |
|---|---|
| `ExploreSolverCorrectnessTest` | The Orb is found on a straight path, a branching map, and when already on it. |
| `ExploreSolverHeuristicTest` | Closer neighbours are tried first, and a misleading dead end is explored then backtracked. |
| `ExploreSolverGraphTest` | The Orb is found on a zig-zag map, and no moves are made when it starts on the Orb. |
| `ExploreSolverEfficiencyTest` | The move count is minimal on maps without misleading branches. |
| `ExploreSolverCycleTest` | Visited tracking stops infinite loops on a map with a cycle. |
| `ExplorerWiringTest` | `Explorer.explore()` delegates to `ExploreSolver`. |
| `ExploreGameSmokeTest` | The real game runs to completion, no crash, on seeds 1, 42 and 123. |

### Escape unit tests

| Test class | What it checks |
|---|---|
| `DijkstraTest` | Cheapest route is by total weight not hops, unreachable tiles are handled, and the path back to the source is rebuilt. |
| `NextStepTest` | The next move is the correct adjacent tile, and it stays put when already on the target. |
| `SelectNextTargetTest` | The richer safe branch is chosen and an unsafe detour is refused. |
| `EscapeIntegrationTest` | The full escape finishes on the exit and collects gold, including gold buried deep and the no-gold case. |
| `AlwaysEscapesTest` | The real game is run over 30 seeded maps and the escape never fails, the one thing we cannot get wrong. |
| `TargetSearchResultTest` | The branch comparator: a higher gold-per-step branch wins, and equal ratios fall through to lower travel cost and then continuability. |
| `TargetSearchTest` | The lookahead finds gold deep in a branch and respects its depth limit, and target selection returns null when nothing is safe and prefers the cheaper branch on an equal-ratio tie. |

### Running specific tests

Run one test class:

```
./gradlew :temple:test --tests "student.ExploreSolverCorrectnessTest"
```

Run one test method:

```
./gradlew :temple:test --tests "student.DijkstraTest.choosesCheaperRouteByWeight"
```

### Benchmark

Score is gold collected times the exploration bonus. These are from our runs on
this implementation:

| Seed | Purpose | Gold | Bonus | Score |
|---|---|---|---|---|
| `42` | Team comparison | 21,243 | 1.2 | 25,491 |
| `-4152836868077314850` | League high-score map | 53,625 | 1.08 | 57,674 |
| 100 random maps (`-n 100`) | Average | | | about 20,000 to 21,000 |

Reproduce them with:

```
./gradlew :temple:run -PchooseMain=main.TXTmain --args="-s 42"
./gradlew :temple:run -PchooseMain=main.TXTmain --args="-s -4152836868077314850"
./gradlew :temple:run -PchooseMain=main.TXTmain --args="-n 100"
```

### Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| `main.TXTmain` not found, or the args look split | The shell split `-PchooseMain=...` or `--args=...` | Quote them, for example `--args="-s 42"`. On PowerShell quote `"-PchooseMain=main.TXTmain"` too. |
| Gradle cannot find a Java 21 toolchain | JDK 21 is not installed | Install a Java 21 JDK, the build is pinned to it. |

## Build

The project uses Gradle with a Java 20 toolchain. `./gradlew :temple:test` and
`./gradlew :temple:run` compile everything for you, so there is nothing else to set
up.
