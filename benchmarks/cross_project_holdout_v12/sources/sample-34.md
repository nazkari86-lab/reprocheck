# Hybrid LSTM-ANFIS Control System for Magnetic Levitation

A comprehensive research implementation combining Long Short-Term Memory (LSTM) neural networks and Adaptive Neuro-Fuzzy Inference System (ANFIS) for predictive control of magnetic levitation systems.

[![MATLAB](https://img.shields.io/badge/MATLAB-R2020b+-orange.svg)](https://www.mathworks.com/products/matlab.html)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

This project implements an advanced hybrid control system that leverages the complementary strengths of deep learning and fuzzy logic for magnetic levitation control. The system combines:

- **LSTM Neural Networks**: Captures temporal patterns and sequence dependencies in system dynamics
- **ANFIS (Adaptive Neuro-Fuzzy Inference System)**: Provides interpretable fuzzy control with adaptive learning
- **Hybrid Architecture**: Integrates LSTM predictions as inputs to ANFIS for superior control performance

The implementation demonstrates how modern machine learning techniques can be effectively combined with traditional fuzzy control methods for complex dynamic systems.

## Key Features

✅ **Complete End-to-End Pipeline**: From raw data processing to trained hybrid model  
✅ **Dual Model Architecture**: Standalone ANFIS and LSTM models plus hybrid integration  
✅ **Comprehensive Preprocessing**: Data clipping, normalization, outlier detection  
✅ **Extensive Visualization**: 50+ figures across all processing stages  
✅ **Performance Metrics**: MAE, RMSE, R² evaluation for all models  
✅ **Documented Code**: Clear comments and section markers throughout  

## Repository Structure

```
hybrid-lstm-anfis-maglev-control/
├── README.md                       # This file
├── LICENSE                         # MIT License
├── .gitignore                      # Git ignore rules
├── code/                           # MATLAB implementation (7 sections)
│   ├── 01_data_preparation.m       # Data aggregation and chunking
│   ├── 02_data_loading.m           # Exploratory data analysis
│   ├── 03_data_preprocessing.m     # Clipping and validation
│   ├── 04_data_modeling_prep.m     # LSTM/ANFIS data preparation
│   ├── 05_anfis_model.m            # ANFIS model training
│   ├── 06_lstm_model.m             # LSTM model development
│   └── 07_hybrid_integration.m     # Hybrid model integration
├── figures/                        # Visualization outputs (empty)
│   ├── 01_data_preparation/
│   ├── 02_data_loading/
│   ├── 03_preprocessing/
│   ├── 04_modeling_prep/
│   ├── 05_anfis/
│   ├── 06_lstm/
│   └── 07_hybrid/
└── data/                           # Data directory (user-provided)
    └── README.md                   # Data format requirements
```

## Detailed Features by Section

### Section 1: Data Preparation
- **Multi-file aggregation**: Reads multiple `output_*.csv` files
- **Chunking strategy**: Minimum 1000 samples per chunk for robust training
- **Randomization**: Shuffles chunks to prevent temporal bias
- **Visualization**: Time-series plots for all variables per file
- **Output**: Combined `dataset.csv` with randomized training data

**Data Variables**:
- `Error`: Position error signal
- `ErrorRate`: Derivative of error (rate of change)
- `Feedback`: Sensor feedback signal  
- `GeneratedSignal`: System-generated control input
- `ControlSignal`: Actual control signal (target variable)

### Section 2: Data Loading and Exploration
- **Statistical analysis**: Summary statistics, correlations
- **Distribution plots**: Histograms and combined PDFs
- **Correlation analysis**: Heatmap of variable relationships
- **Outlier detection**: Box plots for each variable
- **Trend analysis**: Moving average (window=100) visualization
- **Interaction terms**: Scatter plots of error × error rate vs control signal

### Section 3: Data Preprocessing
- **Missing value handling**: Removes NaN and Inf values
- **Data clipping**: Enforces valid ranges for physical constraints
  - `Error`: [-1, 1]
  - `ErrorRate`: [-10, 10]
  - `ControlSignal`: [-3, 3]
  - `Feedback`: [-3, 0]
  - `GeneratedSignal`: [-3, 0]
- **Before/after comparison**: Side-by-side histograms and box plots
- **Impact analysis**: Percentage of data points clipped per variable
- **Validation**: Post-preprocessing correlation analysis

### Section 4: Data Preparation for Modeling

#### 4.1 LSTM Data Preparation
- **Sequence length**: 10 time steps
- **Input features**: Error, ErrorRate, Feedback, GeneratedSignal (4 dimensions)
- **Target**: ControlSignal
- **Train/test split**: 80% / 20%
- **Format**: Cell arrays for LSTM compatibility
- **Validation**: Pie charts and distribution comparisons

#### 4.2 ANFIS Data Preparation  
- **Input features**: Error, ErrorRate (2 dimensions)
- **Target**: ControlSignal
- **Train/test split**: 80% / 20%
- **Non-normalized data**: Uses raw values for interpretability

### Section 5: ANFIS Model Development

**Architecture**:
- **Type**: Sugeno-type FIS
- **Inputs**: Error (7 MFs), ErrorRate (2 MFs)
- **Total rules**: 14 (7 × 2)
- **MF type**: Generalized Bell (gbellmf)
- **Training method**: Hybrid (backpropagation + LSE)

**Training Configuration**:
- **Epochs**: 50
- **Validation**: Testing data for early stopping
- **Optimization**: Hybrid learning algorithm

**Performance Metrics** (on test data):
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- R-squared (R²) coefficient

**Visualizations**:
- Initial/trained membership functions
- Training & validation error curves
- Actual vs predicted plots
- Residual error analysis
- Error distribution histograms
- Scatter plots with reference lines

### Section 6: LSTM Model Development

**Architecture**:
```
Input Layer: sequenceInputLayer(4)
    ↓
LSTM Layer 1: 64 units (sequence output)
    ↓
Dropout: 0.2 rate
    ↓
LSTM Layer 2: 32 units (last output)
    ↓
Fully Connected: 1 unit
    ↓
Regression Output
```

**Training Configuration**:
- **Optimizer**: Adam
- **Max epochs**: 200
- **Mini-batch size**: 32
- **Initial learning rate**: 0.001
- **Validation frequency**: Every 50 iterations
- **Validation patience**: 10 epochs (early stopping)

**Performance Metrics** (on test data):
- Mean Absolute Error (MAE)
- Root Mean Squared Error (RMSE)
- R-squared (R²) coefficient

**Visualizations**:
- Training progress plots (loss curves)
- Actual vs predicted control signals
- Residual error plots
- Error distribution histograms
- Scatter plots (actual vs predicted)
- Temporal error analysis

### Section 7: Hybrid Integration

**Architecture**:
- **Inputs to Hybrid ANFIS**: Error, ErrorRate, LSTM_Prediction (3 dimensions)
- **Output**: ControlSignal
- **Membership functions**:
  - Error: 5 MFs (NL, NM, Z, PM, PL)
  - ErrorRate: 2 MFs (N, P)
  - LSTM_Prediction: 5 MFs (NL, NM, Z, PM, PL)
- **Total rules**: 50 (5 × 2 × 5)
- **FIS type**: Sugeno with constant consequents

**Membership Function Details**:

*Error MFs (range: -1 to +1)*:
- NL (Negative Large): center=-0.8, width=0.2
- NM (Negative Medium): center=-0.4, width=0.1
- Z (Zero): center=0, width=0.1
- PM (Positive Medium): center=0.4, width=0.1
- PL (Positive Large): center=0.8, width=0.2

*ErrorRate MFs (range: -10 to +10)*:
- N (Negative): center=-10, width=10
- P (Positive): center=10, width=10

*LSTM_Prediction MFs (range: -3 to +3)*:
- NL: center=-2.5, width=1.0
- NM: center=-1.25, width=0.5
- Z: center=0, width=0.5
- PM: center=1.25, width=0.5
- PL: center=2.5, width=1.0

**Training Configuration**:
- **Epochs**: 50
- **Validation data**: Test set for monitoring
- **Optimization**: Hybrid ANFIS learning

**Workflow**:
1. Use trained LSTM to predict control signals for entire dataset
2. Create hybrid dataset: [Error, ErrorRate, LSTM_Prediction, ControlSignal]
3. Train Sugeno FIS with 50 rules
4. Evaluate on test data with comprehensive metrics


## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/shakilapr/hybrid-lstm-anfis-maglev-control.git
cd hybrid-lstm-anfis-maglev-control
```

### 2. Prepare Your Data
Place your magnetic levitation system data files in the `data/` folder:
```
data/
├── output_1.csv
├── output_2.csv
└── output_N.csv
```

Each CSV file should contain the required five columns (see Data Format section below).

### 3. Run the Complete Pipeline in MATLAB

**Option A: Run All Sections Sequentially**
```matlab
% Navigate to repository
cd('path/to/hybrid-lstm-anfis-maglev-control')

% Run complete pipeline
run('code/01_data_preparation.m');
run('code/02_data_loading.m');
run('code/03_data_preprocessing.m');
run('code/04_data_modeling_prep.m');
run('code/05_anfis_model.m');
run('code/06_lstm_model.m');
run('code/07_hybrid_integration.m');
```

**Option B: Run Individual Sections**
```matlab
% Section 1: Data Preparation
run('code/01_data_preparation.m');
% Creates: dataset.csv, figures/01_data_preparation/*.png

% Section 2: Data Exploration  
run('code/02_data_loading.m');
% Creates: figures/02_data_loading/*.png

% Section 3: Preprocessing
run('code/03_data_preprocessing.m');
% Creates: figures/03_preprocessing/*.png

% Section 4: Modeling Preparation
run('code/04_data_modeling_prep.m');
% Creates: lstm_prepared_data.mat, anfis_prepared_data.mat

% Section 5: ANFIS Model
run('code/05_anfis_model.m');
% Creates: anfis_trained.fis, figures/05_anfis/*.png

% Section 6: LSTM Model
run('code/06_lstm_model.m');
% Creates: lstm_net.mat, figures/06_lstm/*.png

% Section 7: Hybrid Integration
run('code/07_hybrid_integration.m');
% Creates: hybrid_anfis_trained.fis, figures/07_hybrid/*.png
```

## Data Format

### Input File Naming Convention
Files must follow the pattern: `output_*.csv` (e.g., `output_1.csv`, `output_2.csv`)

### Required Columns
Each CSV file must contain exactly 5 columns in this order:

| Column | Description | Expected Range | Unit |
|--------|-------------|----------------|------|
| `Error` | Position error signal | [-1, 1] | meters or normalized |
| `ErrorRate` | Rate of change of error | [-10, 10] | m/s or normalized |
| `ControlSignal` | Actual control signal applied | [-3, 3] | volts or normalized |
| `Feedback` | Sensor feedback signal | [-3, 0] | volts or normalized |
| `GeneratedSignal` | System-generated control | [-3, 0] | volts or normalized |

### Example Data Structure
```csv
Error,ErrorRate,ControlSignal,Feedback,GeneratedSignal
0.125,-0.032,1.189,2.456,1.234
0.118,-0.028,1.201,2.478,1.245
0.112,-0.025,1.215,2.501,1.258
...
```

### Data Quality Requirements
- **No missing values**: All entries must be numeric
- **No infinite values**: Remove or replace Inf/-Inf before processing
- **Consistent sampling rate**: Same time step across all files
- **Sufficient samples**: Minimum 1000 rows per file (10,000+ recommended)

## Model Architecture Details

### ANFIS (Standalone Model)
- **Purpose**: Baseline fuzzy control with adaptive learning
- **Inputs**: 2 (Error, ErrorRate)
- **MF Configuration**: 7 × 2 = 14 rules
- **Advantages**: Interpretable, fast inference, works with small data

### LSTM (Standalone Model)
- **Purpose**: Temporal sequence prediction with deep learning
- **Inputs**: 4 features × 10 timesteps = sequence
- **Architecture**: 64→32 LSTM units with 0.2 dropout
- **Advantages**: Captures long-term dependencies, handles complex dynamics

### Hybrid LSTM-ANFIS
- **Purpose**: Combines LSTM temporal prediction with ANFIS fuzzy control
- **Inputs**: 3 (Error, ErrorRate, LSTM_Prediction)
- **MF Configuration**: 5 × 2 × 5 = 50 rules
- **Advantages**: Best of both worlds - accuracy + interpretability

**Why Hybrid is Better**:
1. **LSTM captures temporal patterns** that ANFIS alone cannot learn
2. **ANFIS provides interpretable control rules** based on LSTM predictions
3. **Combined architecture** leverages complementary strengths
4. **Reduced overfitting** through multi-stage learning

## Performance Metrics

All models are evaluated using three standard regression metrics:

### Mean Absolute Error (MAE)
```
MAE = (1/n) * Σ|y_actual - y_predicted|
```
- Measures average magnitude of errors
- Same unit as target variable
- Lower is better

### Root Mean Squared Error (RMSE)
```
RMSE = sqrt((1/n) * Σ(y_actual - y_predicted)²)
```
- Penalizes large errors more heavily
- Same unit as target variable
- Lower is better

### R-squared (R²) Coefficient
```
R² = 1 - (SS_residual / SS_total)
```
- Proportion of variance explained by model
- Range: [0, 1] (1 = perfect prediction)
- Higher is better

**Typical Performance Ranges**:
- **Good**: R² > 0.90, RMSE < 0.3
- **Excellent**: R² > 0.95, RMSE < 0.15

## Usage Examples

### Example 1: Quick Start (Full Pipeline)
```matlab
% 1. Place your data in data/ folder
% 2. Run all sections
for i = 1:7
    run(sprintf('code/%02d_*.m', i));
end
```

### Example 2: Load Pre-trained Models
```matlab
% Load ANFIS model
anfis_model = readfis('anfis_trained.fis');
anfis_output = evalfis(test_inputs, anfis_model);

% Load LSTM model
load('lstm_net.mat', 'net_lstm');
lstm_output = predict(net_lstm, test_sequences);

% Load Hybrid ANFIS
hybrid_model = readfis('hybrid_anfis_trained.fis');
hybrid_output = evalfis(hybrid_inputs, hybrid_model);
```

### Example 3: Custom Evaluation
```matlab
% Evaluate on new data
new_data = readtable('new_test_data.csv');

% ANFIS prediction
anfis_pred = evalfis([new_data.Error, new_data.ErrorRate], anfis_model);

% LSTM prediction (requires sequence preparation)
lstm_pred = predict(net_lstm, prepare_lstm_sequences(new_data));

% Hybrid prediction
hybrid_pred = evalfis([new_data.Error, new_data.ErrorRate, lstm_pred], hybrid_model);

% Compare performance
mae_anfis = mean(abs(new_data.ControlSignal - anfis_pred));
mae_lstm = mean(abs(new_data.ControlSignal - lstm_pred));
mae_hybrid = mean(abs(new_data.ControlSignal - hybrid_pred));
```

## Output Files

### Generated Files (Saved to Root Directory)
- `dataset.csv` - Combined and randomized training data
- `hybrid_dataset.csv` - Dataset with LSTM predictions
- `anfis_prepared_data.mat` - ANFIS training/testing data
- `lstm_prepared_data.mat` - LSTM training/testing data
- `anfis_initial.fis` - Initial ANFIS FIS structure
- `anfis_trained.fis` - Trained ANFIS model
- `lstm_net.mat` - Trained LSTM network
- `hybrid_anfis_initial.fis` - Initial hybrid FIS
- `hybrid_anfis_trained.fis` - Trained hybrid model

### Generated Figures (By Section)

**Section 1** (Data Preparation):
- Data visualization per file
- Chunk size distribution
- Randomization visualization
- Combined dataset plots

**Section 2** (Data Exploration):
- Time-series plots
- Histograms and distributions
- Correlation heatmap
- Box plots (outlier detection)
- Moving average trends

**Section 3** (Preprocessing):
- Before/after clipping comparisons
- Impact analysis tables
- Post-preprocessing correlations

**Section 4** (Modeling Prep):
- Train/test split pie charts
- Target distribution comparisons
- Sample sequence visualizations

**Section 5** (ANFIS):
- Initial/trained MF plots
- Training/validation errors
- Actual vs predicted
- Residual analysis
- Error distributions

**Section 6** (LSTM):
- Training progress curves
- Actual vs predicted
- Residual analysis
- Error distributions
- Temporal error analysis

**Section 7** (Hybrid):
- Hybrid MF visualizations
- Training/validation errors
- Actual vs predicted (train & test)
- Residual errors
- Error distributions
- Scatter plots

### Contact for Collaboration
- **Email**: shakilabeta@gmail.com
- **GitHub**: [@shakilapr](https://github.com/shakilapr)





**Last Updated**: October 2024

---

## Quick Links

- 📧 **Contact**: shakilabeta@gmail.com
- 💻 **GitHub**: [github.com/shakilapr](https://github.com/shakilapr)
- 📄 **License**: [MIT License](LICENSE)
- 📊 **Repository**: [hybrid-lstm-anfis-maglev-control](https://github.com/shakilapr/hybrid-lstm-anfis-maglev-control)

---

**Developed by**: Shakila Praveen Rathnayake  
**Institution**: Mechatronics Engineering Program  
**Course**: DMX7306 Intelligent Control Systems  
**Year**: 2024

---

*For questions, issues, or collaboration opportunities, please open an issue on GitHub or contact via email.*
