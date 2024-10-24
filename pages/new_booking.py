import random
from datetime import datetime, timedelta
from typing import Dict

import pandas as pd
import plotly.express as px
import streamlit as st

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
            potential_slots  # Pass potential slots to scoring system
        )

        # Display results
        st.header("Suggested Appointment Times")
        for i, time in enumerate(best_times, 1):
            # Create a card-like display for each suggestion
            with st.container():
                st.markdown(f"""
                **Option {i}**
                * Time: {time.strftime('%I:%M %p')}
                * Available Staff: {', '.join([s.id for s in staff_roster.values() if VisitType(visit_type) in s.capabilities])}
                """)

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