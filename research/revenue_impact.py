import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.api import VAR

# Generate a time series data
dates = pd.date_range(start='2020-01-01', periods=100, freq='W')
np.random.seed(42)
revenue = np.random.normal(loc=5000, scale=1000, size=len(dates)).cumsum()  # Simulated revenue over time

# Create DataFrame
ts_data = pd.DataFrame({'date': dates, 'revenue': revenue})
ts_data.set_index('date', inplace=True)

# ARIMA model - Only Revenue based
arima_model = ARIMA(ts_data['revenue'], order=(1, 1, 1)) # Train the model on historical revenue data
arima_result = arima_model.fit()
arima_forecast = arima_result.forecast(steps=10) # forecast of next 10 weeks

# SARIMA model - Only revenue based
sarima_model = SARIMAX(ts_data['revenue'], order=(1, 1, 1), seasonal_order=(1, 1, 1, 12)) # Train the model on historical revenue data
sarima_result = sarima_model.fit()
sarima_forecast = sarima_result.forecast(steps=10) # forecast of next 10 weeks

# If total visits data is available, can forecast both - revenue and visits with VAR
visits = np.random.normal(loc=200, scale=50, size=len(dates)).cumsum()
ts_data['visits'] = visits

# VAR model - Revenue and Visits based forecasting as visits and revenue are assumed to be strongly correlated
var_model = VAR(ts_data) # Train the model on historical revenue and vists data
var_result = var_model.fit(maxlags=15, ic='aic')
var_forecast = var_result.forecast(ts_data.values[-var_result.k_ar:], steps=10) # forecast of next 10 weeks
var_forecast_df = pd.DataFrame(var_forecast, index=pd.date_range(start=ts_data.index[-1]
                                                                       + pd.Timedelta(weeks=1), periods=10, freq='W'), columns=ts_data.columns)


# The revenue forecast for the next 10 weeks is stored in arima_forecast
# The revenue forecast for the next 10 weeks is stored in sarima_forecast
# The revenue forecast for the next 10 weeks is stored in var_forecast_df['revenue']
# The visits forecast for the next 10 weeks is stored in var_forecast_df['visits']

comparison_df = pd.DataFrame({
    'ARIMA_Revenue_Forecast': arima_forecast,
    'SARIMA_Revenue_Forecast': sarima_forecast,
    'VAR_Revenue_Forecast': var_forecast_df['revenue'],
    'VAR Visits_Forecast': var_forecast_df['visits']
}, index=pd.date_range(start=ts_data.index[-1] + pd.Timedelta(weeks=1), periods=10, freq='W'))

print(comparison_df.to_string())
