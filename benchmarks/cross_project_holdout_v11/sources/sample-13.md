# NVIDIA Stock Price Prediction

This project was completed as part of the AI/ML Engineering Internship at DevelopersHub Corporation.

## Project Overview

This project focuses on predicting NVIDIA stock prices using historical market data. A machine learning regression model is trained to estimate the next-day closing price based on Open, High, Low, Close, and Volume data.

The objective is to understand time-series forecasting using machine learning.

## Dataset

Data is collected from Yahoo Finance using the yfinance library.

Features include:
- Open
- High
- Low
- Close
- Volume

## Target Variable

Next_Close: next day's closing price using time shift.

## Features Used

- Open
- High
- Low
- Close
- Volume
- Lag features
- Moving averages

## Data Preprocessing

- Created target variable using shift
- Generated lag features
- Computed moving averages
- Removed missing values
- Split dataset (80/20, no shuffle)

## Model Used

Random Forest Regressor

Hyperparameters:
- n_estimators = 300
- max_depth = 8
- min_samples_split = 5
- random_state = 42

## Evaluation Metrics

- Mean Absolute Error (MAE): ~7.00
- R² Score: ~0.65

## Conclusion

Machine learning model captures general stock trends but is limited by market randomness. The relatively higher error and moderate R² score can be attributed to the highly volatile and non-linear nature of NVIDIA stock, which experienced significant rapid growth and market-driven fluctuations during the period, making short-term prediction more challenging for traditional regression models. Further improvement can be achieved through better feature engineering and tuning.
