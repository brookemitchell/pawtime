import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
from datetime import datetime, timedelta
import random
from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from enum import Enum
import numpy as np


# Data structures
@dataclass
class Veterinarian:
    id: str
    name: str
    specialties: Set[str]
    color: str  # For visualization


class AppointmentType(Enum):
    CHECKUP = "Checkup"
    VACCINATION = "Vaccination"
    SURGERY = "Surgery"
    EMERGENCY = "Emergency"
    GROOMING = "Grooming"
    DENTAL = "Dental"


@dataclass
class Appointment:
    start_time: datetime
    end_time: datetime
    pet_name: str
    pet_type: str
    appointment_type: AppointmentType
    vet: Veterinarian
    owner_name: str
    status: str = "Confirmed"


# Initialize demo data
def initialize_vets():
    return [
        Veterinarian(
            id="V1",
            name="Dr. Smith",
            specialties={"general", "surgery"},
            color="rgb(33, 150, 243)"  # Blue
        ),
        Veterinarian(
            id="V2",
            name="Dr. Johnson",
            specialties={"exotic", "birds"},
            color="rgb(76, 175, 80)"  # Green
        ),
        Veterinarian(
            id="V3",
            name="Dr. Patel",
            specialties={"general", "dental"},
            color="rgb(156, 39, 176)"  # Purple
        )
    ]


def generate_sample_appointments(selected_date: datetime, vets: List[Veterinarian]) -> List[Appointment]:
    appointments = []
    pet_types = ["Dog", "Cat", "Bird", "Rabbit", "Hamster"]
    pet_names = ["Max", "Luna", "Charlie", "Bella", "Rocky", "Lucy", "Bailey", "Daisy"]
    owner_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

    # Generate 15-20 appointments for the day
    num_appointments = random.randint(15, 20)

    for _ in range(num_appointments):
        # Generate random appointment time between 9 AM and 5 PM
        hour = random.randint(9, 16)
        minute = random.choice([0, 15, 30, 45])
        duration = random.choice([30, 45, 60])  # minutes

        start_time = selected_date.replace(hour=hour, minute=minute)
        end_time = start_time + timedelta(minutes=duration)

        appointments.append(Appointment(
            start_time=start_time,
            end_time=end_time,
            pet_name=random.choice(pet_names),
            pet_type=random.choice(pet_types),
            appointment_type=random.choice(list(AppointmentType)),
            vet=random.choice(vets),
            owner_name=random.choice(owner_names),
            status=random.choice(["Confirmed", "Check-in", "In Progress", "Completed"])
        ))

    return sorted(appointments, key=lambda x: x.start_time)


def create_gantt_chart(appointments: List[Appointment], vets: List[Veterinarian]):
    # Prepare data for Plotly
    df_dict = {
        'Task': [],  # Vet name
        'Start': [],  # Start time
        'Finish': [],  # End time
        'Resource': [],  # Appointment type
        'Description': [],  # Additional info
    }

    colors = []  # Separate list for colors

    for appt in appointments:
        df_dict['Task'].append(appt.vet.name)
        df_dict['Start'].append(appt.start_time)
        df_dict['Finish'].append(appt.end_time)
        df_dict['Resource'].append(appt.appointment_type.value)
        df_dict['Description'].append(
            f"Pet: {appt.pet_name} ({appt.pet_type})<br>"
            f"Owner: {appt.owner_name}<br>"
            f"Status: {appt.status}"
        )
        colors.append(appt.vet.color)

    df = pd.DataFrame(df_dict)

    # Create the Gantt chart
    fig = ff.create_gantt(
        df,
        colors=colors,  # Pass the colors list directly
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        height=400,
        title='Daily Clinic Schedule'
    )

    # Update layout for better visibility
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Veterinarian",
        font=dict(size=12),
        hoverlabel=dict(bgcolor="white"),
        showlegend=True
    )

    # Customize hover text
    for trace in fig.data:
        trace.hovertemplate = (
            "<b>%{text}</b><br>"
            "Start: %{x}<br>"
            "End: %{base}<br>"
            "<extra></extra>"  # This removes the secondary box
        )

    return fig


def main():
    st.set_page_config(page_title="Vet Clinic Schedule", layout="wide")

    st.title("🐾 Veterinary Clinic Daily Schedule")

    # Initialize vets
    vets = initialize_vets()

    # Date selector
    col1, col2 = st.columns([2, 3])

    with col1:
        selected_date = st.date_input(
            "Select Date",
            datetime.now()
        )

        # Convert to datetime for processing
        selected_datetime = datetime.combine(selected_date, datetime.min.time())

        # Generate appointments for selected date
        appointments = generate_sample_appointments(selected_datetime, vets)

        # Display summary statistics
        st.subheader("📊 Daily Summary")
        total_appointments = len(appointments)
        st.metric("Total Appointments", total_appointments)

        # Appointments by type
        st.subheader("📋 Appointments by Type")
        type_counts = {}
        for appt in appointments:
            type_counts[appt.appointment_type.value] = type_counts.get(appt.appointment_type.value, 0) + 1

        for appt_type, count in type_counts.items():
            st.text(f"{appt_type}: {count}")

    with col2:
        # Display schedule statistics
        st.subheader("👩‍⚕️ Veterinarian Workload")
        vet_loads = {}
        for appt in appointments:
            vet_loads[appt.vet.name] = vet_loads.get(appt.vet.name, 0) + 1

        for vet_name, count in vet_loads.items():
            utilization = (count / 16) * 100  # Assuming 16 slots is max capacity
            st.progress(utilization / 100)
            st.text(f"{vet_name}: {count} appointments ({utilization:.1f}% utilization)")

    # Create and display Gantt chart
    st.subheader("📅 Daily Schedule")
    fig = create_gantt_chart(appointments, vets)
    st.plotly_chart(fig, use_container_width=True)

    # Detailed appointment list
    st.subheader("📝 Detailed Appointment List")
    for appt in appointments:
        with st.expander(
                f"{appt.start_time.strftime('%H:%M')} - {appt.pet_name} with {appt.vet.name}"
        ):
            cols = st.columns(4)
            with cols[0]:
                st.write("**Pet Details**")
                st.write(f"Name: {appt.pet_name}")
                st.write(f"Type: {appt.pet_type}")
            with cols[1]:
                st.write("**Appointment**")
                st.write(f"Type: {appt.appointment_type.value}")
                st.write(f"Status: {appt.status}")
            with cols[2]:
                st.write("**Time**")
                st.write(f"Start: {appt.start_time.strftime('%H:%M')}")
                st.write(f"End: {appt.end_time.strftime('%H:%M')}")
            with cols[3]:
                st.write("**Veterinarian**")
                st.write(appt.vet.name)
                st.write(f"Owner: {appt.owner_name}")


if __name__ == "__main__":
    main()