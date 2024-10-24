import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from xgboost import XGBRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# Sample data
data = {
    'appointment_time': [9, 10, 11, 14, 15, 16],  # Hour of the day
    'duration': [30, 45, 60, 30, 60, 45],  # Duration in minutes
    'pet_type': [1, 0, 1, 0, 1, 0],  # 1 for dog, 0 for cat
    'wait_time': [5, 15, 10, 20, 5, 30]  # Wait time in minutes, outcome basecd on appointment_time, duration, and pet_type
}

df = pd.DataFrame(data)

X = df[['appointment_time', 'duration', 'pet_type']]

# Generate additional logical features from available data
X['appointment_duration'] = X['appointment_time'] * X['duration']
X['appointment_time_sin'] = np.sin(2 * np.pi * X['appointment_time'] / 24)
X['appointment_time_cos'] = np.cos(2 * np.pi * X['appointment_time'] / 24)

y = df['wait_time']

# Split the data into training and testing sets - 80% for training, 20% for testing
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=True)

# poly = PolynomialFeatures(degree=2, include_bias=False)
# X_train = poly.fit_transform(X_train)
# X_test = poly.transform(X_test)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# List of models to evaluate
models = {
    'Linear Regression': LinearRegression(),
    'Support Vector Regression': SVR(kernel='rbf'),
    'Random Forest Regressor': RandomForestRegressor(n_estimators=100),
    'Gradient Boosting Regressor': GradientBoostingRegressor(n_estimators=100),
    'XGBoost': XGBRegressor(n_estimators=100),
    'Neural Network': MLPRegressor(hidden_layer_sizes=(100,), max_iter=1000)
}

results = {}

for name, model in models.items():
    model.fit(X_train, y_train)  # Train the model
    y_pred = model.predict(X_test)  # Predict

    # Calculate performance metrics and predicted result
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    results[name] = {
        'Mean Absolute Error': mae,
        'R-squared': r2,
        'Predictions': y_pred
    }

for model_name, metrics in results.items():
    print(f"{model_name}:")
    print(f"  Mean Absolute Error: {metrics['Mean Absolute Error']:.2f}")
    print(f"  R-squared: {metrics['R-squared']:.2f}")
    print()
    results_df = pd.DataFrame({
        'Actual': y_test,
        'Predicted': metrics['Predictions']
    })
    print("  Actual vs Predicted:")
    print(results_df)
    print()
