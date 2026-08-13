# DA5401 A7: Multi-Class Model Selection using ROC and Precision-Recall Curves  
**Course:** Data Analytics (DA5401)  
**Student**: Abesech Inbasekar  
**Roll Number**: ME21B003

---

###  Repository Structure  
├── Assignment_7_ME21B003.ipynb # Main Colab Notebook  
├── README.md # This file

---

## Overview
This repository implements a complete model-selection and evaluation pipeline on the **Statlog (Landsat Satellite)** dataset.  
The objective is to compare multiple classifiers using **Accuracy**, **Weighted F1**, **ROC-AUC**, and **Precision-Recall (PRC-AP)** metrics, and to interpret their behavior under both well-performing and poor configurations.

---

## Part A: Data Preparation and Baseline

### Objective
Load and preprocess the Landsat dataset, standardize all features, and create a balanced train–test split for subsequent experiments.

### Steps
1. **Data Loading:** Combined the `sat.trn` and `sat.tst` files (each with 36 features + 1 label).  
2. **Standardization:** Applied z-score scaling to normalize features.  
3. **Train–Test Split:** 80-20 split with stratified sampling to maintain class proportions.

### Dataset Summary
| Metric | Value |
|:--|:--|
| Total samples | 6,435 |
| Features | 36 |
| Classes | 6 (1–5, 7) |
| Train samples | 5,148 |
| Test samples | 1,287 |

---

## Part B: Baseline Model Training and Evaluation

### Models
1. **K-Nearest Neighbors (KNN)**  
2. **Support Vector Machine (SVC)**  
3. **Logistic Regression**  
4. **Decision Tree Classifier**  
5. **Gaussian Naïve Bayes**  
6. **Dummy Classifier** (Prior strategy)

### Results
| Model | Accuracy | Weighted F1 | Observation |
|:--|:--:|:--:|:--|
| **KNN** | **0.911** | **0.909** | Best overall baseline; excellent separability |
| **SVM** | 0.893 | 0.891 | Consistent, smooth margin separation |
| Logistic Regression | 0.849 | 0.842 | Robust linear model |
| Decision Tree | 0.847 | 0.848 | Moderate, prone to overfitting |
| Gaussian NB | 0.783 | 0.790 | Weak due to independence assumption |
| Dummy (Prior) | 0.239 | 0.092 | Baseline reference |

**Observation:**  
KNN and SVM outperform other classical models. Naïve Bayes and Dummy confirm the baseline lower bound.

---

## Part B: ROC Analysis for Model Selection

### One-vs-Rest (OvR) Multi-Class ROC
Each class is treated as *positive* vs. the rest (*negative*).  
ROC curves are averaged (macro-average) to compare models on separability.

| Model | Macro-Averaged AUC |
|:--|:--:|
| **KNN** | **0.980** |
| **SVM** | **0.980** |
| Logistic Regression | 0.972 |
| Gaussian NB | 0.948 |
| Decision Tree | 0.895 |
| Dummy (Prior) | 0.500 |

**Interpretation:**  
AUC ≈ 1.0 implies near-perfect class ranking. KNN and SVM provide highest separability, while Dummy corresponds to random guessing.

---

## Part C: Precision–Recall Analysis

### Motivation
Precision–Recall Curves (PRC) are more informative than ROC when dealing with class imbalance, emphasizing positive-class precision at varying recall levels.

| Model | Mean Average Precision (AP) |
|:--|:--:|
| **KNN** | **0.921** |
| **SVM** | 0.900 |
| Logistic Regression | 0.864 |
| Gaussian NB | 0.786 |
| Decision Tree | 0.725 |
| Dummy (Prior) | 0.167 |

**Interpretation:**  
KNN maintains the best precision–recall balance.  
Dummy’s steep PRC drop demonstrates how weak models rapidly lose precision as recall increases.

---

## Part D: Synthesis and Recommendation

### Cross-Metric Comparison

| Model | Weighted F1 | ROC-AUC | PRC-AP |
|:--|:--:|:--:|:--:|
| **KNN** | **0.909** | **0.980** | **0.921** |
| **SVM** | 0.891 | 0.980 | 0.900 |
| Logistic Regression | 0.842 | 0.972 | 0.864 |
| Gaussian NB | 0.790 | 0.948 | 0.786 |
| Decision Tree | 0.848 | 0.895 | 0.725 |
| Dummy (Prior) | 0.092 | 0.500 | 0.167 |

### Trade-offs
- **ROC-AUC** captures ranking quality, independent of thresholds.  
- **PRC-AP** is sensitive to false positives and reveals precision degradation in imbalanced settings.  
- **F1-Score** evaluates a single operating point.  

### Recommendation
**KNN** emerges as the best overall baseline model — offering high accuracy, AUC, and PRC-AP with minimal tuning.  
It balances precision and recall effectively, making it a strong candidate for multiclass remote-sensing classification.

---

##  Brownie Points – Part 1: Ensemble Models

| Model | Accuracy | Weighted F1 | ROC-AUC | PRC-AP |
|:--|:--:|:--:|:--:|:--:|
| **XGBoost** | **0.9200** | **0.9178** | **0.989** | **0.949** |
| **Random Forest** | 0.9106 | 0.9071 | 0.987 | 0.939 |

**Interpretation:**
- **XGBoost** outperforms all baselines by sequentially correcting residual errors through gradient boosting, achieving near-perfect separability (AUC ≈ 0.99).  
- **Random Forest** provides similar results via variance reduction and is easier to interpret.  
- Both ensembles generalize well and outperform traditional classifiers, confirming the power of ensemble learning.

---

## Brownie Points – Part 2: Experimental & Poor-Performing Models

| Model | ROC-AUC | Description |
|:--|:--:|:--|
| **QDA** | **0.968** | Strong generative classifier; covariance modeling effective. |
| **Perceptron** | **0.884** | Linear model; decent ranking but low accuracy. |
| **LDA (weak features)** | **0.834** | Reduced features weaken separability. |
| **Dummy (constant)** | **0.500** | Random baseline. |
| **Inverted Logistic Regression** | **0.028** | Anti-learning: reversed probabilities rank incorrect classes highest. |

**Conceptual Insight:**  
AUC reveals *ranking quality*, not direct accuracy.  
- High AUC (>0.9): strong separability (QDA).  
- Mid AUC (~0.8): partial discrimination (Perceptron, LDA).  
- AUC = 0.5: random.  
- AUC < 0.5: model systematically wrong (Inverted Logistic Regression).

---

##  Final Insights

- **Best Models:** XGBoost and Random Forest outperform all baselines, achieving ROC-AUC ≈ 0.99.  
- **Most Interpretable:** Random Forest (feature importances easily extracted).  
- **Best Simplicity–Performance Trade-off:** KNN (no training, consistent across metrics).  
- **Key Lesson:** ROC and PRC analyses reveal not just accuracy, but deeper insights into **ranking**, **calibration**, and **error behavior**.  

> Ensemble methods, combined with multi-metric evaluation (Accuracy, F1, ROC-AUC, PRC-AP), provide a comprehensive understanding of model reliability — crucial for robust real-world deployment.

---

##  References
- Statlog (Landsat Satellite) Dataset – UCI Machine Learning Repository  
- Scikit-learn Documentation – Metrics and Model Evaluation  
- Chen & Guestrin (2016), *XGBoost: A Scalable Tree Boosting System*, KDD

---

###  How to Run

1. Clone the repository  
   ```bash
   git clone https://github.com/<Abesech-Inbasekar>/DA5401_Assignment-6.git

## Dependencies

```bash
python>=3.10
numpy
pandas
matplotlib
scikit-learn
scipy




