import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from clinic_data_generator import test_data_generation
from forecasting import ServiceDemandForecasting
from insights import ScheduleInsights
from pricing_calculator import PricingCalculator
from research.schedule import Appointment
from schedule import AdvancedTimeSlotGenerator, Staff, TimeSlot, Pet, Customer, \
    get_three_best_appointments, test_advanced_scheduler
from visit_type import VisitType


def generate_dummy_schedule(
        generator: AdvancedTimeSlotGenerator,
        staff_roster: Dict[str, Staff],
        num_appointments: int = 10
) -> Dict[datetime, TimeSlot]:
    """Generate realistic dummy schedule data"""
    schedule = {}
    start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    species_list = ["canine", "feline", "avian", "exotic"]

    # Create dummy pet for slot generation
    dummy_pet = Pet("dummy", "canine", 0.5, [])

    # Generate some appointments
    for _ in range(num_appointments):
        visit_type = random.choice(list(VisitType))
        potential_slots = generator.generate_potential_slots(
            schedule,
            staff_roster,
            visit_type,
            dummy_pet,
            start_date
        )

        if potential_slots:
            time = random.choice(potential_slots)
            details =  generator.get_appointment_details(time, visit_type, dummy_pet)

            # Find available staff
            available_staff = list(generator._check_staff_availability(
                time,
                details['duration'],
                staff_roster,
                schedule,
                visit_type
            ))

            if available_staff:
                schedule[time] = TimeSlot(
                    time,
                    details['end_time'],
                    visit_type,
                    random.choice(available_staff),
                    random.choice(species_list)
                )

    return schedule


def generate_dummy_data():
    """Generate dummy data with a dense schedule."""

    # Generate staff roster with staggered lunch breaks
    staff_roster = {
        "Dr. Smith": Staff(
            "Dr. Smith",
            [VisitType.VACCINATION, VisitType.WELLNESS, VisitType.CONSULT, VisitType.SURGERY],
            datetime.now().replace(hour=12, minute=0)
        ),
        "Dr. Johnson": Staff(
            "Dr. Johnson",
            [VisitType.DENTAL, VisitType.SURGERY, VisitType.SPECIALTY],
            datetime.now().replace(hour=13, minute=0)
        ),
        "Nurse Williams": Staff(
            "Nurse Williams",
            [VisitType.VACCINATION, VisitType.WELLNESS, VisitType.GROOMING],
            datetime.now().replace(hour=11, minute=0)
        )
    }

    # Generate dense schedule
    schedule = {}
    current_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    visit_types = list(VisitType)
    species_list = ["Canine", "Feline", "Avian", "Exotic"]

    # Create time slots every 30 minutes for each staff member
    for hour in range(9, 17):  # 9 AM to 5 PM
        for minute in [0, 30]:  # Every 30 minutes
            time = current_date.replace(hour=hour, minute=minute)

            # Try to schedule each staff member
            for staff_id, staff in staff_roster.items():
                # Skip if during lunch hour
                if time.hour != staff.lunch_start.hour:
                    # 90% chance of booking (high density)
                    if random.random() < 0.9:
                        # Select appropriate visit type for staff
                        available_types = list(staff.capabilities)
                        visit_type = random.choice(available_types)

                        schedule[time] = TimeSlot(
                            time,
                            time + timedelta(minutes=30),
                            visit_type,
                            staff_id,
                            random.choice(species_list)
                        )

    # Generate expiring inventory
    expiring_inventory = {
        VisitType.VACCINATION: 0.8,
        VisitType.SURGERY: 0.3,
        VisitType.DENTAL: 0.5
    }

    # Calculate schedule statistics
    total_possible_slots = len(staff_roster) * 16  # 8 hours * 2 slots/hour
    actual_bookings = len(schedule)
    utilization = (actual_bookings / total_possible_slots) * 100

    summary = {
        'total_slots': total_possible_slots,
        'booked_slots': actual_bookings,
        'utilization': utilization,
        'appointments_by_type': {},
        'appointments_by_staff': {}
    }

    # Calculate appointment distributions
    for slot in schedule.values():
        # Count by type
        visit_type = slot.visit_type.value
        summary['appointments_by_type'][visit_type] = summary['appointments_by_type'].get(visit_type, 0) + 1

        # Count by staff
        staff_id = slot.staff_id
        summary['appointments_by_staff'][staff_id] = summary['appointments_by_staff'].get(staff_id, 0) + 1

    return staff_roster, schedule, expiring_inventory, summary

def create_schedule_gantt(schedule):
    """Create a Gantt chart of the daily schedule."""
    df_schedule = []

    for time, slot in schedule.items():
        df_schedule.append({
            'Task': slot.staff_id,
            'Start': slot.start_time,
            'Finish': slot.end_time,
            'Type': slot.visit_type.value,
            'Species': slot.species
        })

    if df_schedule:
        df = pd.DataFrame(df_schedule)
        fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Type",
                          title="Daily schedule",
                          labels={"Task": "Staff member", "Type": "Visit type"})
        fig.update_layout(height=300)
        return fig
    return None


class ScoreVisualizer:
    def __init__(self):
        self.score_categories = {
            'Staff Availability': 30,
            'Preferred Time': 22,
            'Health Complexity': 12,
            'Customer reliability': 22,
            'Expiring inventory': 14,
            'Species Alignment': 8,
            'Break time': 8,
            'Visit Type Alignment': 5
        }

        self.category_descriptions = {
            'Staff Availability': 'Score based on available qualified staff',
            'Visit Type Alignment': 'Score based on similar appointments nearby',
            'Species Alignment': 'Score based on similar species nearby',
            'Health Complexity': 'Score based on adequate time allocation',
            'Preferred Time': 'Score based on optimal time of day',
            'Expiring inventory': 'Score based on inventory optimization',
            'Customer reliability': 'Score based on client history',
            'Break time': 'Score based on optimal spacing'
        }

    def _get_score_components(
            self,
            time: datetime,
            schedule: Dict,
            staff_roster: Dict,
            visit_type: 'VisitType',
            customer: 'Customer',
            pet: 'Pet',
            expiring_inventory: Dict,
            time_slot_generator: 'AdvancedTimeSlotGenerator'
    ) -> Dict[str, float]:
        """Calculate individual score components for a time slot"""
        appointment_details = time_slot_generator.get_appointment_details(
            time, visit_type, pet
        )

        scores = {}

        # Staff Availability (20 points)
        available_staff = time_slot_generator._check_staff_availability(
            time,
            appointment_details['duration'],
            staff_roster,
            schedule,
            visit_type
        )
        scores['Staff Availability'] = 20 * (len(available_staff) / len(staff_roster))

        # Visit Type Alignment (15 points)
        neighboring_slots = [
            slot for t, slot in schedule.items()
            if abs((t - time).total_seconds()) <= 3600
        ]
        similar_type_count = sum(1 for slot in neighboring_slots if slot.visit_type == visit_type)
        scores['Visit Type Alignment'] = 15 * (similar_type_count / max(1, len(neighboring_slots)))

        # Species Alignment (15 points)
        same_species_count = sum(1 for slot in neighboring_slots if slot.species == pet.species)
        scores['Species Alignment'] = 15 * (same_species_count / max(1, len(neighboring_slots)))

        # Health Complexity (10 points)
        scores['Health Complexity'] = 10 if appointment_details['duration'] >= appointment_details['duration'] else 5

        # Preferred Time (10 points)
        scores['Preferred Time'] = 10 if appointment_details['is_preferred_time'] else 0

        # Expiring inventory (10 points)
        scores['Expiring inventory'] = 10 * expiring_inventory.get(visit_type, 0)

        # Customer reliability (10 points)
        peak_hours = 10 <= time.hour <= 15
        if customer.late_history > 0.2 or customer.no_show_history > 0.1:
            scores['Customer reliability'] = 10 if peak_hours else 5
        else:
            scores['Customer reliability'] = 5 if peak_hours else 10

        # Break time (10 points)
        padding_score = 10
        for existing_time, slot in schedule.items():
            time_diff = abs((existing_time - time).total_seconds() / 60)
            if time_diff < appointment_details['padding_before']:
                padding_score -= 2
            if time_diff < appointment_details['padding_after']:
                padding_score -= 2
        scores['Break time'] = max(0, padding_score)

        return scores

    def create_score_breakdown_chart(
            self,
            scores: Dict[str, float],
            title: str
    ) -> go.Figure:
        """Create a horizontal bar chart showing score breakdown"""
        df = pd.DataFrame([
            {'Category': cat, 'Score': score, 'Maximum': self.score_categories[cat]}
            for cat, score in scores.items()
        ])

        fig = go.Figure()

        # Add bars for maximum possible scores (lighter color)
        fig.add_trace(go.Bar(
            y=df['Category'],
            x=df['Maximum'],
            name='Maximum Possible',
            orientation='h',
            marker_color='lightgray',
            hovertext=[self.category_descriptions[cat] for cat in df['Category']],
            hoverinfo='text'
        ))

        # Add bars for actual scores
        fig.add_trace(go.Bar(
            y=df['Category'],
            x=df['Score'],
            name='Actual Score',
            orientation='h',
            marker_color='#1f77b4',
            hovertext=[f"{score:.1f}/{max_score}" for score, max_score in zip(df['Score'], df['Maximum'])],
            hoverinfo='text'
        ))

        fig.update_layout(
            title=title,
            barmode='overlay',
            height=400,
            margin=dict(l=20, r=20, t=40, b=20),
            xaxis_title='Points',
            yaxis_title='Category',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    def create_comparison_chart(
            self,
            all_scores: List[Tuple[datetime, Dict[str, float]]]
    ) -> go.Figure:
        """Create a radar chart comparing different time slots"""
        fig = go.Figure()

        for i, (time, scores) in enumerate(all_scores):
            fig.add_trace(go.Scatterpolar(
                r=[scores[cat] for cat in self.score_categories.keys()],
                theta=list(self.score_categories.keys()),
                name=f"Option {i + 1}: {time.strftime('%I:%M %p')}",
                fill='toself'
            ))

        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 20]
                )
            ),
            showlegend=True,
            height=500,
            title="Comparison of Time Slot Scores"
        )

        return fig


def display_score_analysis(
        best_times: List[datetime],
        schedule: Dict,
        staff_roster: Dict,
        visit_type: 'VisitType',
        customer: 'Customer',
        pet: 'Pet',
        expiring_inventory: Dict,
        time_slot_generator: 'AdvancedTimeSlotGenerator'
) -> None:
    """Display comprehensive score analysis in Streamlit"""
    visualizer = ScoreVisualizer()

    st.subheader("Appointment Score Analysis")

    # Calculate scores for each time slot
    all_scores = []
    for time in best_times:
        scores = visualizer._get_score_components(
            time,
            schedule,
            staff_roster,
            visit_type,
            customer,
            pet,
            expiring_inventory,
            time_slot_generator
        )
        all_scores.append((time, scores))

    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4 = st.tabs(["Individual Breakdowns", "Comparison", "Insights", "Forecast"])

    with tab1:
        for i, (time, scores) in enumerate(all_scores):
            col1, col2 = st.columns([2, 1])

            with col1:
                fig = visualizer.create_score_breakdown_chart(
                    scores,
                    f"Option {i + 1}: {time.strftime('%I:%M %p')}"
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown(f"**Total Score: {sum(scores.values()):.1f}/100**")
                st.markdown("#### Key Factors:")
                for category, score in scores.items():
                    max_score = visualizer.score_categories[category]
                    if score >= 0.5 * max_score:
                        st.markdown(f"✅ Good {category.lower()}")

    with tab2:
        comparison_fig = visualizer.create_comparison_chart(all_scores)
        st.plotly_chart(comparison_fig, use_container_width=True)

        # Add summary table
        summary_data = []
        for time, scores in all_scores:
            summary_data.append({
                'Time': time.strftime('%I:%M %p'),
                'Total Score': f"{sum(scores.values()):.1f}",
                'Top Factors': ', '.join(
                    [cat for cat, score in scores.items()
                     if score >= 0.7 * visualizer.score_categories[cat]][:2]
                )
            })
        st.table(pd.DataFrame(summary_data))

    with tab3:
        st.markdown("### Insights and Recommendations")

        potential_slots = time_slot_generator.generate_potential_slots(
            schedule,
            staff_roster,
            visit_type,
            pet,
            datetime.now()
        )

        insights = ScheduleInsights(schedule, staff_roster, potential_slots)
        insights.display_insights()
        insights.display_specialization_insights()

    with tab4:
        # forecasting section
        forecasting = ServiceDemandForecasting(schedule)
        forecasting.display_forecast()
        display_revenue_forecast()


def format_forecast_table(forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Format forecast data for display."""
    # Create display DataFrame with specific columns
    display_df = pd.DataFrame({
        'Revenue Forecast': forecast_df['revenue'].map('${:,.2f}'.format),
        'Visits Forecast': forecast_df['visits'].map('{:,.0f}'.format)
    })

    # Format the index (dates) with consistent weekly format
    display_df.index = forecast_df.index.strftime('%Y-%m-%d')
    display_df.index.name = 'Week Starting'

    return display_df


def create_revenue_forecast(appointments: List[Appointment], pricing_calculator: PricingCalculator) -> dict:
    """Create revenue forecast with adjusted scale, more data points, and special events."""
    try:
        # Generate weekly dates for forecasting (doubled to 20 weeks)
        start_date = pd.Timestamp.now().normalize()
        start_date = start_date - pd.Timedelta(days=start_date.weekday())

        dates = pd.date_range(
            start=start_date,
            periods=20,  # Doubled forecast period
            freq='W-MON'
        )

        # Scale factors
        REVENUE_SCALE = 50  # Reduce revenue by factor of 50
        VISITS_SCALE = 50  # Reduce visits by factor of 50

        # Seasonal patterns (multipliers)
        seasonal_patterns = {
            # Monthly seasonality (weeks in month)
            1: 1.08,  # First week: Higher due to payday
            2: 0.98,  # Second week: Slight dip
            3: 1.03,  # Third week: Recovery
            4: 0.95,  # Fourth week: End of month dip
            5: 1.0,  # Fifth week: Normal

            # Day of week adjustments
            'mon': 1.15,  # Monday: High demand
            'tue': 1.08,  # Tuesday: Above average
            'wed': 1.0,  # Wednesday: Average
            'thu': 0.95,  # Thursday: Below average
            'fri': 1.12  # Friday: High for weekend prep
        }

        # Special events and their impacts
        special_events = {
            # Format: 'YYYY-MM-DD': (event_name, revenue_multiplier, visits_multiplier)
            (start_date + pd.Timedelta(weeks=3)).strftime('%Y-%m-%d'):
                ('Pet Vaccination Drive', 1.3, 1.4),
            (start_date + pd.Timedelta(weeks=7)).strftime('%Y-%m-%d'):
                ('Local Pet Show', 1.2, 1.25),
            (start_date + pd.Timedelta(weeks=12)).strftime('%Y-%m-%d'):
                ('Summer Health Check Campaign', 1.25, 1.3),
            (start_date + pd.Timedelta(weeks=16)).strftime('%Y-%m-%d'):
                ('Annual Wellness Week', 1.35, 1.45)
        }

        # Initialize base values with lower scale
        base_revenue = 494372.924639 / REVENUE_SCALE  # Scaled down revenue
        base_visits = 20332 / VISITS_SCALE  # Scaled down visits

        # Randomized growth rates with lower volatility
        np.random.seed(42)  # For reproducibility
        revenue_growth_rates = np.random.normal(0.01, 0.001, len(dates))  # Reduced std to 0.1%
        visit_growth_rates = np.random.normal(0.01, 0.0005, len(dates))  # Reduced std to 0.05%

        # Generate forecast data
        forecast_data = []
        current_revenue = base_revenue
        current_visits = base_visits
        event_annotations = []

        for i, date in enumerate(dates):
            # Get week number in month
            week_in_month = (date.day - 1) // 7 + 1

            # Base seasonal adjustments
            seasonal_multiplier = seasonal_patterns.get(week_in_month, 1.0)
            day_multiplier = seasonal_patterns.get(date.strftime('%a').lower(), 1.0)

            # Reduced random noise (±2% for revenue, ±1% for visits)
            revenue_noise = np.random.uniform(0.98, 1.02)
            visit_noise = np.random.uniform(0.99, 1.01)

            # Check for special events
            date_str = date.strftime('%Y-%m-%d')
            if date_str in special_events:
                event_name, rev_mult, vis_mult = special_events[date_str]
                event_multiplier_revenue = rev_mult
                event_multiplier_visits = vis_mult
                event_annotations.append({
                    'date': date,
                    'event': event_name,
                    'impact_revenue': f"+{((rev_mult - 1) * 100):.0f}%",
                    'impact_visits': f"+{((vis_mult - 1) * 100):.0f}%"
                })
            else:
                event_multiplier_revenue = 1.0
                event_multiplier_visits = 1.0

            # Calculate adjusted values
            adjusted_revenue = (current_revenue *
                                seasonal_multiplier *
                                day_multiplier *
                                revenue_noise *
                                event_multiplier_revenue)

            adjusted_visits = (current_visits *
                               seasonal_multiplier *
                               day_multiplier *
                               visit_noise *
                               event_multiplier_visits)

            forecast_data.append({
                'date': date,
                'revenue': adjusted_revenue,
                'visits': adjusted_visits,
                'seasonal_factor': seasonal_multiplier,
                'day_factor': day_multiplier,
                'has_event': date_str in special_events
            })

            # Apply growth rates for next period
            current_revenue *= (1 + revenue_growth_rates[i])
            current_visits *= (1 + visit_growth_rates[i])

        # Create forecast DataFrame
        forecast_df = pd.DataFrame(forecast_data)
        forecast_df.set_index('date', inplace=True)

        # Calculate confidence intervals with reduced volatility
        volatility_factor = 0.08  # Reduced from 0.15 to 0.08
        forecast_df['revenue_upper'] = forecast_df['revenue'] * (1 + volatility_factor *
                                                                 np.sqrt(np.arange(len(forecast_df)) + 1))
        forecast_df['revenue_lower'] = forecast_df['revenue'] * (1 - volatility_factor *
                                                                 np.sqrt(np.arange(len(forecast_df)) + 1))

        forecast_df['visits_upper'] = (forecast_df['visits'] * (1 + volatility_factor *
                                                                np.sqrt(np.arange(len(forecast_df)) + 1))).round()
        forecast_df['visits_lower'] = (forecast_df['visits'] * (1 - volatility_factor *
                                                                np.sqrt(np.arange(len(forecast_df)) + 1))).round()

        # Generate historical data (8 weeks instead of 4)
        historical_dates = pd.date_range(
            end=start_date - pd.Timedelta(days=1),
            periods=8,  # Doubled historical period
            freq='W-MON'
        )

        historical_data = []
        hist_revenue = base_revenue * 0.95
        hist_visits = base_visits * 0.95

        for date in historical_dates:
            week_in_month = (date.day - 1) // 7 + 1
            seasonal_multiplier = seasonal_patterns.get(week_in_month, 1.0)
            day_multiplier = seasonal_patterns.get(date.strftime('%a').lower(), 1.0)

            revenue_noise = np.random.uniform(0.98, 1.02)
            visit_noise = np.random.uniform(0.99, 1.01)

            historical_data.append({
                'date': date,
                'revenue': hist_revenue * seasonal_multiplier * day_multiplier * revenue_noise,
                'visits': hist_visits * seasonal_multiplier * day_multiplier * visit_noise
            })

            hist_revenue *= 1.01
            hist_visits *= 1.01

        historical_df = pd.DataFrame(historical_data)
        historical_df.set_index('date', inplace=True)

        # Round visits to whole numbers
        forecast_df['visits'] = forecast_df['visits'].round().astype(int)
        historical_df['visits'] = historical_df['visits'].round().astype(int)

        # Add current appointments if available
        if appointments:
            current_week_start = start_date
            current_revenue = sum([
                pricing_calculator.calculate_price(
                    appointment_type=apt.appointment_type,
                    duration=int((apt.end_time - apt.start_time).total_seconds() / 60),
                    pet_type=apt.pet_type,
                    start_time=apt.start_time,
                    is_emergency=apt.status == "Emergency",
                    is_repeat_customer=False
                )['final_price']
                for apt in appointments
                if apt.start_time.date() >= current_week_start.date() and
                   apt.start_time.date() < (current_week_start + pd.Timedelta(days=7)).date()
            ]) / REVENUE_SCALE  # Apply scaling

            current_visits = sum([
                1 for apt in appointments
                if apt.start_time.date() >= current_week_start.date() and
                   apt.start_time.date() < (current_week_start + pd.Timedelta(days=7)).date()
            ]) / VISITS_SCALE  # Apply scaling

            if current_week_start in forecast_df.index:
                forecast_df.loc[current_week_start, 'revenue'] = current_revenue
                forecast_df.loc[current_week_start, 'visits'] = current_visits

        return {
            'forecast_data': forecast_df,
            'historical_data': historical_df,
            'model_type': 'Seasonal Model with Special Events',
            'events': event_annotations,
            'seasonality': seasonal_patterns
        }

    except Exception as e:
        st.error(f"Error in forecast generation: {str(e)}")
        return {
            'forecast_data': pd.DataFrame(),
            'historical_data': pd.DataFrame(),
            'model_type': None,
            'events': [],
            'seasonality': None
        }

def display_revenue_forecast():
    """Display revenue forecast with table and visualizations."""
    st.subheader("📈 Revenue and Visit Forecast")

    # Initialize pricing calculator
    pricing_calculator = PricingCalculator()

    # Get appointments from session state
    appointments = st.session_state.get('appointments', [])

    try:
        # Get forecast data
        forecast_results = create_revenue_forecast(appointments, pricing_calculator)
        forecast_df = forecast_results['forecast_data']
        historical_df = forecast_results['historical_data']
        model_type = forecast_results['model_type']

        if forecast_df.empty:
            st.warning("Unable to generate forecast.")
            return

        # Display model type and date range
        st.info(f"Forecast Model: {model_type}")
        st.caption(
            f"Forecast period: {forecast_df.index[0].strftime('%Y-%m-%d')} to {forecast_df.index[-1].strftime('%Y-%m-%d')}")

        # Create tabs for different views
        forecast_tab1, forecast_tab2 = st.tabs(["📊 Visualizations", "📋 Detailed Forecast"])

        with forecast_tab1:
            # Revenue visualization
            fig_revenue = go.Figure()

            # Historical revenue
            fig_revenue.add_trace(go.Scatter(
                x=historical_df.index,
                y=historical_df['revenue'],
                name='Historical Revenue',
                line=dict(color='blue')
            ))

            # Forecasted revenue
            fig_revenue.add_trace(go.Scatter(
                x=forecast_df.index,
                y=forecast_df['revenue'],
                name='Forecasted Revenue',
                line=dict(color='red', dash='dash')
            ))

            fig_revenue.update_layout(
                title='Weekly Revenue Forecast',
                xaxis_title='Week',
                yaxis_title='Revenue ($)',
                hovermode='x unified'
            )

            st.plotly_chart(fig_revenue, use_container_width=True)

        with forecast_tab2:
            st.subheader("Weekly Forecast Details")

            # Format and display the forecast table
            display_df = format_forecast_table(forecast_df)
            st.table(display_df)

            # Add download button for forecast data
            csv = display_df.to_csv()
            st.download_button(
                label="📥 Download Forecast Data",
                data=csv,
                file_name="forecast_data.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"Error generating forecast display: {str(e)}")
        return
def main():
    st.title("🐾 Purfect timing")

    # Generate dummy data
    staff_roster, schedule, expiring_inventory, summary = test_data_generation()
    time_slot_generator = AdvancedTimeSlotGenerator()

    # Display staff information
    st.sidebar.subheader("Staff on Duty")
    for staff_id, staff in staff_roster.items():
        st.sidebar.write(f"• {staff_id}")

    # Display current schedule
    fig = create_schedule_gantt(schedule)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    # Input form for new appointment
    st.header("Schedule New Appointment")

    col1, col2 = st.columns(2)

    with col1:
        # Visit type selection
        visit_type = st.selectbox(
            "Type of Visit",
            [visit_type.value for visit_type in VisitType]
        )

        # Pet details
        species = st.selectbox("Pet Species", ["Canine", "Feline", "Avian", "Exotic"])
        health_complexity = st.slider(
            "Pet Health Complexity",
            0.0, 1.0, 0.3,
            help="0 = Simple case, 1 = Very complex case"
        )

    with col2:
        # Customer reliability
        late_history = st.slider(
            "Customer Late History",
            0.0, 1.0, 0.1,
            help="Percentage of late arrivals"
        )
        no_show_history = st.slider(
            "Customer No-Show History",
            0.0, 1.0, 0.05,
            help="Percentage of no-shows"
        )

    # Create customer and pet objects
    customer = Customer("new_customer", late_history, no_show_history)
    pet = Pet("new_pet", species, health_complexity, [])

    if st.button("Find Best Appointment Times"):

        # Generate potential slots for new appointment
        potential_slots = test_advanced_scheduler()


        # Use in appointment scheduling
        # Get top 3 scored slots from potential_slots using the scoring system
        # When finding appointments
        best_times = get_three_best_appointments(
            schedule,
            staff_roster,
            VisitType(visit_type),
            customer,
            pet,
            expiring_inventory,
            potential_slots,
            time_slot_generator
        )

        # Display the basic appointment suggestions
        st.header("Suggested Appointment Times")
        for i, time in enumerate(best_times, 1):
            st.markdown(f"**Option {i}**: {time.strftime('%I:%M %p')}")

        # Display the detailed score analysis
        display_score_analysis(
            best_times,
            schedule,
            staff_roster,
            VisitType(visit_type),
            customer,
            pet,
            expiring_inventory,
            time_slot_generator
        )

        # Display staff availability chart
        st.header("Staff Availability Overview")
        staff_data = []
        for staff_id, staff in staff_roster.items():
            available_for_visit = VisitType(visit_type) in staff.capabilities
            staff_data.append({
                'Staff': staff_id,
                'Available': 'Yes' if available_for_visit else 'No',
                'Lunch Break': staff.lunch_start.strftime('%I:%M %p')
            })

        st.table(pd.DataFrame(staff_data))

        # Display inventory status for visit type
        if VisitType(visit_type) in expiring_inventory:
            st.header("Inventory Status")
            inventory_level = expiring_inventory[VisitType(visit_type)]
            st.progress(inventory_level)
            st.caption(f"Expiring vaccinations: {inventory_level * 100:.0f}%")


if __name__ == "__main__":
    main()
