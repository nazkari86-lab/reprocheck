# Case Study: Predicting Match-3 Player Churn using Machine Learning
**Author**: Meltem Baş
**Role**: Product Specialist Candidate

## The Objective
In Free-to-Play mobile games (like *Royal Match* or *Toon Blast*), managing the game economy—specifically the flow of virtual currency ("sinks" and "sources")—is critical for maximizing player Lifetime Value (LTV). My goal for this repository was to prove a hypothesis: *Can we use Machine Learning to figure out exactly which gameplay roadblocks cause players to abandon a Match-3 game?*

## Methodology
Because I needed granular player data to test my hypothesis, I built a custom **Monte Carlo simulator** using Python. 

1. **The Simulation**: I simulated 5,000 distinct players playing through 50 Match-3 levels. The progression relies on stochastic win rates modeling actual gameplay. A player starts with 3,500 coins and 5 lives. Winning a level yields 100 coins; losing a level consumes a life, and running out of lives requires 900 coins to continue.
2. **Behavioral Tracking**: The script tracked contextual events for each player:
   - `fails_early`: Failures on levels 1-10.
   - `fails_mid`: Failures on levels 11-30.
   - `fails_late`: Failures on levels 31-50.
   - `continues_used`: How many times the player exhausted their life pool and bought a continue.
3. **The Data Pipeline**: This dataset was exported straight into `player_data.csv`, algorithmically mimicking a real-world SQL pull from a game telemetry database (such as Snowflake or BigQuery).

## The Machine Learning Model
I ingested the `player_data.csv` using `pandas` and implemented a **Random Forest Classifier** from `scikit-learn` (utilizing an 80/20 train/test split). 

The model achieved **96.4% Accuracy** predicting the churn class.

### Feature Importances: The "Why"
As a Product Manager, model accuracy isn't enough; we need to know the *why* behind the player behavior. Exposing the internal feature nodes of the Random Forest model revealed the following weightings for churn prediction:

- **Failing Late Levels (31-50)**: 36.87% Importance
- **Failing Mid Levels (11-30)**: 31.70% Importance
- **Using Continues (Coin Drain)**: 27.30% Importance
- **Failing Early Levels (1-10)**: 4.13% Importance

## The Strategic Product Decision
If a data analyst simply reported "Players are churning," a naive design approach would be to make the entire game easier. However, the Machine Learning data tells a deeply specific, targeted story:

Failing early levels (1-10) is practically irrelevant (4.13% importance). Players either expect onboarding friction or have a high tolerance for early-game failures because their coin balances are still high. However, hitting the difficulty wall at levels 31-50 is the absolute paramount reason players quit permanently (36.8% importance paired with a 27.3% importance on coin drainage).

**Actionable Steps for the Live Game:**
1. **Do not touch early game difficulty**. It acts as a healthy filter without severely damaging retention.
2. **Implement dynamic coin sources** specifically targeted at players entering Level 30+. By introducing a "Level 30 login bonus" or "Rewarded Video Ads" tailored exclusively to mid-game players, we can pad their coin wallets before they hit the Level 31+ difficulty wall.
3. **Conduct A/B Testing**: Run an experiment lowering the win rate difficulty curve of levels 31-50 by 15% to test if the "fun factor" and Day-7 Retention metrics increase.
