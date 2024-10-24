from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import streamlit as st


class ServiceDemandForecasting:
    def __init__(self, schedule: Dict[datetime, 'TimeSlot']):
        self.schedule = schedule
        self.historical_patterns = self._analyze_historical_patterns()

    def _analyze_historical_patterns(self) -> Dict:
        """Analyze historical appointment patterns"""
        patterns = {
            'hourly_demand': defaultdict(lambda: defaultdict(int)),
            'service_popularity': defaultdict(int),
            'typical_duration': defaultdict(list),
            'concurrent_services': defaultdict(list)
        }

        for time, slot in self.schedule.items():
            hour = time.hour
            service = slot.visit_type.value
            duration = (slot.end_time - slot.start_time).total_seconds() / 3600  # in hours

            patterns['hourly_demand'][hour][service] += 1
            patterns['service_popularity'][service] += 1
            patterns['typical_duration'][service].append(duration)

            # Track concurrent services
            concurrent_services = [
                other_slot.visit_type.value
                for other_time, other_slot in self.schedule.items()
                if abs((other_time - time).total_seconds()) < 1800  # within 30 minutes
                   and other_slot.visit_type.value != service
            ]
            patterns['concurrent_services'][service].extend(concurrent_services)

        return patterns

    def forecast_demand(self, horizon_days: int = 7) -> Dict:
        """Generate demand forecast for specified horizon"""
        forecast = {
            'daily_demand': {},
            'service_growth': {},
            'peak_hours': {},
            'recommended_capacity': {}
        }

        # Calculate baseline metrics
        total_appointments = sum(self.historical_patterns['service_popularity'].values())
        hours_analyzed = len(set(hour for hour in self.historical_patterns['hourly_demand'].keys()))

        for service, count in self.historical_patterns['service_popularity'].items():
            # Calculate daily rate and variation
            daily_rate = count / (hours_analyzed / 8)  # Assuming 8-hour days

            # Generate daily demand forecast with confidence intervals
            forecast['daily_demand'][service] = self._generate_daily_forecast(
                daily_rate,
                horizon_days
            )

            # Calculate service growth trend
            hourly_counts = [
                self.historical_patterns['hourly_demand'][hour][service]
                for hour in range(9, 17)
            ]
            growth_rate = self._calculate_growth_rate(hourly_counts)
            forecast['service_growth'][service] = growth_rate

            # Identify peak hours
            peak_hours = self._identify_peak_hours(service)
            forecast['peak_hours'][service] = peak_hours

            # Calculate recommended capacity
            forecast['recommended_capacity'][service] = self._calculate_recommended_capacity(
                service,
                daily_rate,
                growth_rate
            )

        return forecast

    def _generate_daily_forecast(
            self,
            daily_rate: float,
            horizon_days: int
    ) -> Dict[str, List[float]]:
        """Generate daily demand forecast with confidence intervals"""
        # Use normal distribution for prediction intervals
        std_dev = np.sqrt(daily_rate)  # Assuming Poisson-like variation

        forecast = {
            'mean': [],
            'lower': [],
            'upper': []
        }

        for day in range(horizon_days):
            # Add slight trend and weekly seasonality
            trend_factor = 1 + (day * 0.01)  # 1% daily growth
            seasonality = 1 + (0.2 * np.sin(2 * np.pi * (day % 7) / 7))  # 20% weekly variation

            mean_demand = daily_rate * trend_factor * seasonality

            # Calculate confidence intervals
            lower = max(0, mean_demand - 1.96 * std_dev)
            upper = mean_demand + 1.96 * std_dev

            forecast['mean'].append(mean_demand)
            forecast['lower'].append(lower)
            forecast['upper'].append(upper)

        return forecast

    def _calculate_growth_rate(self, counts: List[int]) -> float:
        """Calculate service growth rate from historical data"""
        if not counts or len(counts) < 2:
            return 0

        # Simple linear regression for growth trend
        x = np.arange(len(counts))
        y = np.array(counts)

        slope, _ = np.polyfit(x, y, 1)
        return slope / np.mean(counts) if np.mean(counts) > 0 else 0

    def _identify_peak_hours(self, service: str) -> List[int]:
        """Identify peak hours for a service"""
        hourly_counts = {
            hour: self.historical_patterns['hourly_demand'][hour][service]
            for hour in range(9, 17)
        }

        if not hourly_counts:
            return []

        mean_count = np.mean(list(hourly_counts.values()))
        std_count = np.std(list(hourly_counts.values()))

        return [
            hour for hour, count in hourly_counts.items()
            if count > mean_count + std_count
        ]

    def _calculate_recommended_capacity(
            self,
            service: str,
            daily_rate: float,
            growth_rate: float
    ) -> Dict[str, float]:
        """Calculate recommended service capacity"""
        # Base capacity from daily rate
        base_capacity = daily_rate * 1.2  # 20% buffer

        # Adjust for growth
        growth_factor = max(1, 1 + (growth_rate * 30))  # 30-day growth projection

        # Consider typical duration
        avg_duration = np.mean(self.historical_patterns['typical_duration'][service])
        capacity_hours = base_capacity * avg_duration * growth_factor

        return {
            'appointments_per_day': round(base_capacity * growth_factor, 1),
            'hours_per_day': round(capacity_hours, 1),
            'recommended_staff': max(1, round(capacity_hours / 6))  # Assuming 6 productive hours per staff
        }

    def display_forecast(self):
        """Display comprehensive forecast visualizations"""
        st.subheader("📈 Service Demand Forecast")

        # Generate forecast
        forecast = self.forecast_demand()

        # Display forecast overview
        col1, col2 = st.columns(2)

        with col1:
            st.write("#### Projected Daily Demand")
            demand_data = []
            for service, demand in forecast['daily_demand'].items():
                for day in range(len(demand['mean'])):
                    demand_data.append({
                        'Day': day + 1,
                        'Service': service,
                        'Demand': demand['mean'][day],
                        'Lower CI': demand['lower'][day],
                        'Upper CI': demand['upper'][day]
                    })

            demand_df = pd.DataFrame(demand_data)
            fig = go.Figure()

            for service in forecast['daily_demand'].keys():
                service_data = demand_df[demand_df['Service'] == service]

                # Add mean line
                fig.add_trace(go.Scatter(
                    x=service_data['Day'],
                    y=service_data['Demand'],
                    name=f"{service} (mean)",
                    mode='lines',
                    line=dict(width=2)
                ))

                # Add confidence interval
                fig.add_trace(go.Scatter(
                    x=service_data['Day'],
                    y=service_data['Upper CI'],
                    name=f"{service} (upper)",
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False
                ))
                fig.add_trace(go.Scatter(
                    x=service_data['Day'],
                    y=service_data['Lower CI'],
                    name=f"{service} (lower)",
                    mode='lines',
                    line=dict(width=0),
                    fill='tonexty',
                    showlegend=False
                ))

            fig.update_layout(
                title="7-Day Demand Forecast",
                xaxis_title="Days Ahead",
                yaxis_title="Expected Appointments",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.write("#### Service Growth Trends")
            growth_data = [
                {'Service': service, 'Growth Rate': rate * 100}
                for service, rate in forecast['service_growth'].items()
            ]
            growth_df = pd.DataFrame(growth_data)

            fig = px.bar(
                growth_df,
                x='Service',
                y='Growth Rate',
                title="Service Growth Rates (%)",
                color='Growth Rate',
                color_continuous_scale='RdYlBu'
            )
            st.plotly_chart(fig, use_container_width=True)

        # Display capacity recommendations
        st.write("#### Capacity Recommendations")
        capacity_data = []
        for service, capacity in forecast['recommended_capacity'].items():
            capacity_data.append({
                'Service': service,
                'Daily Appointments': capacity['appointments_per_day'],
                'Hours Required': capacity['hours_per_day'],
                'Staff Required': capacity['recommended_staff']
            })

        capacity_df = pd.DataFrame(capacity_data)
        st.table(capacity_df)

        # Display peak hour analysis
        st.write("#### Peak Hours Analysis")
        peak_data = []
        for service, peaks in forecast['peak_hours'].items():
            peak_times = [f"{hour:02d}:00" for hour in sorted(peaks)]
            peak_data.append({
                'Service': service,
                'Peak Hours': ", ".join(peak_times) if peak_times else "No clear peaks",
                'Number of Peak Hours': len(peaks)
            })

        peak_df = pd.DataFrame(peak_data)
        st.table(peak_df)


