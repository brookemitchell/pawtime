import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st
import plotly.graph_objects as go

from schedule import AdvancedTimeSlotGenerator, Staff, TimeSlot, Pet, Customer, \
    get_three_best_appointments
from visit_type import VisitType


def generate_dummy_schedule(
        generator: AdvancedTimeSlotGenerator,
        staff_roster: Dict[str, Staff],
        num_appointments: int = 10
) -> Dict[datetime, TimeSlot]:
    """Generate realistic dummy schedule data"""
    schedule = {}
    start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    species_list = ["dog", "cat", "bird", "rabbit"]

    # Create dummy pet for slot generation
    dummy_pet = Pet("dummy", "dog", 0.5, [])

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
            details = generator.get_appointment_details(time, visit_type, dummy_pet)

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
    """Generate dummy data for testing the scheduling system."""

    # Generate staff roster
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

    # Generate existing schedule
    schedule = {}
    current_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    visit_types = list(VisitType)
    species_list = ["dog", "cat", "bird", "rabbit"]

    # Add some random appointments throughout the day
    for _ in range(8):
        time = current_date + timedelta(minutes=random.randint(0, 16) * 30)
        if time not in schedule:
            schedule[time] = TimeSlot(
                time,
                time + timedelta(minutes=30),
                random.choice(visit_types),
                random.choice(list(staff_roster.keys())),
                random.choice(species_list)
            )

    # Generate expiring inventory
    expiring_inventory = {
        VisitType.VACCINATION: 0.8,
        VisitType.SURGERY: 0.3,
        VisitType.DENTAL: 0.5
    }

    return staff_roster, schedule, expiring_inventory


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
                          title="Daily Schedule",
                          labels={"Task": "Staff Member", "Type": "Visit Type"})
        fig.update_layout(height=300)
        return fig
    return None


class ScoreVisualizer:
    def __init__(self):
        self.score_categories = {
            'Staff Availability': 20,
            'Visit Type Alignment': 15,
            'Species Alignment': 15,
            'Health Complexity': 10,
            'Preferred Time': 10,
            'Expiring Inventory': 10,
            'Customer Reliability': 10,
            'Padding Optimization': 10
        }

        self.category_descriptions = {
            'Staff Availability': 'Score based on available qualified staff',
            'Visit Type Alignment': 'Score based on similar appointments nearby',
            'Species Alignment': 'Score based on similar species nearby',
            'Health Complexity': 'Score based on adequate time allocation',
            'Preferred Time': 'Score based on optimal time of day',
            'Expiring Inventory': 'Score based on inventory optimization',
            'Customer Reliability': 'Score based on client history',
            'Padding Optimization': 'Score based on optimal spacing'
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

        # Expiring Inventory (10 points)
        scores['Expiring Inventory'] = 10 * expiring_inventory.get(visit_type, 0)

        # Customer Reliability (10 points)
        peak_hours = 10 <= time.hour <= 15
        if customer.late_history > 0.2 or customer.no_show_history > 0.1:
            scores['Customer Reliability'] = 10 if peak_hours else 5
        else:
            scores['Customer Reliability'] = 5 if peak_hours else 10

        # Padding Optimization (10 points)
        padding_score = 10
        for existing_time, slot in schedule.items():
            time_diff = abs((existing_time - time).total_seconds() / 60)
            if time_diff < appointment_details['padding_before']:
                padding_score -= 2
            if time_diff < appointment_details['padding_after']:
                padding_score -= 2
        scores['Padding Optimization'] = max(0, padding_score)

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
    tab1, tab2 = st.tabs(["Individual Breakdowns", "Comparison"])

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
                    if score >= 0.7 * visualizer.score_categories[category]:
                        st.markdown(f"✅ Strong {category.lower()}")
                    elif score <= 0.3 * visualizer.score_categories[category]:
                        st.markdown(f"⚠️ Weak {category.lower()}")

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


def main():
    st.title("🐾 Veterinary Practice Scheduler")

    # Generate dummy data
    staff_roster, schedule, expiring_inventory = generate_dummy_data()
    generator = AdvancedTimeSlotGenerator()
    schedule = generate_dummy_schedule(generator, staff_roster)

    # Display current schedule
    st.header("Current Daily Schedule")
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
        species = st.selectbox("Pet Species", ["dog", "cat", "bird", "rabbit"])
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

        # When finding appointment times:
        potential_slots = generator.generate_potential_slots(
            schedule,
            staff_roster,
            VisitType(visit_type),
            pet
        )

        # Get top 3 scored slots from potential_slots using the scoring system
        best_times = get_three_best_appointments(
            schedule,
            staff_roster,
            VisitType(visit_type),
            customer,
            pet,
            expiring_inventory,
            potential_slots,
            generator
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
            generator
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
            st.caption(f"Inventory level for {visit_type}: {inventory_level * 100:.0f}%")


if __name__ == "__main__":
    main()