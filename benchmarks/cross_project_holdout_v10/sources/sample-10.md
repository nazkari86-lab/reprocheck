# Fraud_detection -**INSAID INTERNSHIP TASK**
**Fraud Detection Model: Random Forest, Decision Tree, and XGBoost Comparison**
## Business Context
This case requires trainees to develop a model for predicting fraudulent transactions for a
financial company and use insights from the model to develop an actionable plan. Data for the
case is available in CSV format having 6362620 rows and 10 columns.
Candidates can use whatever method they wish to develop their machine learning model.
Following usual model development procedures, the model would be estimated on the
calibration data and tested on the validation data. This case requires both statistical analysis and
creativity/judgment. We recommend you spend time on both fine-tuning and interpreting the
results of your machine learning model.

<br>
This repository contains the code and analysis for a **fraud detection system** that compares the performance of **Random Forest**, **Decision Tree**, and **XGBoost** classifiers on a highly imbalanced dataset. The objective is to detect fraudulent transactions effectively while minimizing false positives and false negatives.

## Features

- **Data Preprocessing**:
  - Handling missing values and encoding categorical features.
  - Feature engineering: creation of new features like `TransactionPath`, `Actual_amount_orig`, and `Actual_amount_dest` to enhance model performance.
  - Scaling numeric features to standardize data.
  
- **Exploratory Data Analysis (EDA)**:
  - Visualization of class distribution (Legit vs. Fraud) using bar charts.
  - Heatmaps for analyzing feature correlations and identifying key relationships.
  ![Screenshot (82)](https://github.com/user-attachments/assets/d277c2c8-d82c-4976-8249-13f1c0bf91f6)

- **Model Training**:
  - Training three models: **Random Forest**, **Decision Tree**, and **XGBoost**.
  - Performance comparison using various evaluation metrics like accuracy, precision, recall, F1-score, and ROC curves.

- **Evaluation Metrics**:
  - Confusion matrix and classification report for precision, recall, F1-score, and accuracy.
  - Visualization of **Confusion Matrices** for Random Forest and Decision Tree.
  - ROC-AUC curve to measure the models' ability to distinguish between the classes.
![Screenshot (83)](https://github.com/user-attachments/assets/6b80a4bc-28e4-4080-bebc-6d8970be4bb2)
![Screenshot (84)](https://github.com/user-attachments/assets/ffb40f2c-4a23-4fa0-a07f-53c54082ec05)
![Screenshot (85)](https://github.com/user-attachments/assets/d398c257-8ded-48be-a0aa-fd09482a5b45)

## Dataset

The dataset consists of financial transactions with a significant class imbalance between legitimate and fraudulent transactions (Legit: 99.87%, Fraud: 0.13%). The focus is to detect the small portion of fraudulent transactions accurately while avoiding false negatives.

## Key Findings

- **Random Forest** showed superior precision (96%) compared to **Decision Tree** (70%) and **XGBoost** (97%), making it more reliable for identifying fraudulent transactions.
- The models have similar overall accuracy (~100%), but accuracy alone is misleading for imbalanced datasets.
- **Precision** and **recall** metrics are crucial when detecting fraud, with Random Forest and XGBoost providing better performance than Decision Tree in these metrics.

## Key Factors for Fraud Prediction

1. Whether the request source is secured or not.
2. Legitimacy of the organization requesting money.
3. Transaction history and past behavior of vendors.

## Preventive Measures for Fraud

- Always use verified and trusted applications.
- Ensure you browse on secure websites (use HTTPS).
- Use secure internet connections (consider using a VPN).
- Keep your devices and security software up to date.
- Avoid responding to unsolicited emails, SMS, or calls.
- In case of suspicious activity, contact your bank immediately.

## How to Use

1. Clone the repository:
   ```bash
   git clone https://github.com/Tanishq665/Fraud_detection.git
