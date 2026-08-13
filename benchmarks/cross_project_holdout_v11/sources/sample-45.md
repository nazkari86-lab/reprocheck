# **BoroughAccidentInsights**

## **Overview**
**BoroughAccidentInsights** is a machine learning project aimed at predicting the number of injuries in traffic accidents based on a variety of features, such as boroughs, vehicle types, contributing factors, and crash times. The project leverages a Random Forest model to analyze both structured and unstructured data, including textual contributing factors processed with NLP (TF-IDF). The insights from this project help identify key factors contributing to traffic accidents across boroughs, providing a data-driven approach to improving road safety.

## **Key Features**
- **Predictive Model**: Accurately predicts the number of injuries in traffic accidents using Random Forest regression.
- **Feature Engineering**: Includes time-based features (e.g., crash hour, rush hour), manually encoded categorical variables (borough, vehicle type), and NLP-based features from contributing factors.
- **NLP Integration**: Uses TF-IDF to process textual data on contributing factors to enhance model predictions.
- **Exploratory Data Analysis (EDA)**: Visualizations and insights into crash distributions, peak accident times, contributing factors, and vehicle types.

## **Technologies Used**
- **Python**: For data processing and model development.
- **scikit-learn**: For machine learning models and evaluation metrics.
- **Pandas and NumPy**: For data manipulation and preprocessing.
- **Matplotlib and Seaborn**: For generating insightful visualizations.
- **TF-IDF**: Used for processing textual contributing factors.

## **Project Structure**
- `data/`: Contains the dataset used in this project.
- `notebooks/`: Jupyter notebooks documenting the analysis and model development process.
- `src/`: Python scripts for data preprocessing, feature engineering, and model building.
- `README.md`: Project overview and documentation.
  
## **How to Run the Project**
1. **Clone the repository**:
   `git clone https://github.com/yourusername/BoroughAccidentInsights.git`
   `cd BoroughAccidentInsights`
2. **Install Dependencies**:
   `pip install -r requirements.txt`
3. **RUn the Notebook**


## **Results**

- The model achieved a **Mean Absolute Error (MAE)** of `1.82e-05` and a **Mean Squared Error (MSE)** of `1.02e-04`, demonstrating strong predictive performance.

## **Future Work**

- Optimize hyperparameters further to reduce overfitting and improve generalization.
- Expand the dataset with additional features, such as weather conditions and traffic data.
- Explore other machine learning models (e.g., XGBoost, Gradient Boosting) for potential performance improvements.


## **License**

This project is licensed under the MIT License - see the `LICENSE` file for details.
