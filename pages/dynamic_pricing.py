import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Set

import pandas as pd
import plotly.figure_factory as ff
import streamlit as st

from appt_types import AppointmentType
from pricing_calculator import PricingCalculator


# Data structures
@dataclass
class Veterinarian:
    id: str
    name: str
    specialties: Set[str]
    color: str


@dataclass
class Appointment:
    id: str  # Added ID for tracking
    start_time: datetime
    end_time: datetime
    pet_name: str
    pet_type: str
    appointment_type: AppointmentType
    vet: Veterinarian
    owner_name: str
    status: str = "Confirmed"
    notes: str = ""


# Initialize session state
def init_session_state():
    if 'appointments' not in st.session_state:
        st.session_state.appointments = []
    if 'vets' not in st.session_state:
        st.session_state.vets = initialize_vets()
    if 'editing_appointment' not in st.session_state:
        st.session_state.editing_appointment = None
    if 'show_edit_modal' not in st.session_state:
        st.session_state.show_edit_modal = False
    if 'delete_mode' not in st.session_state:
        st.session_state.delete_mode = False


def initialize_vets():
    return [
        Veterinarian(
            id="V1",
            name="Dr. Smith",
            specialties={"general", "surgery"},
            color="rgb(33, 150, 243)"
        ),
        Veterinarian(
            id="V2",
            name="Dr. Johnson",
            specialties={"exotic", "birds"},
            color="rgb(76, 175, 80)"
        ),
        Veterinarian(
            id="V3",
            name="Dr. Patel",
            specialties={"general", "dental"},
            color="rgb(156, 39, 176)"
        )
    ]


def generate_sample_appointments(selected_date: datetime, vets: List[Veterinarian]) -> List[Appointment]:
    if len(st.session_state.appointments) > 0:
        return st.session_state.appointments

    appointments = []
    pet_types = ["Dog", "Cat", "Bird", "Rabbit", "Hamster"]
    pet_names = ["Max", "Luna", "Charlie", "Bella", "Rocky", "Lucy", "Bailey", "Daisy"]
    owner_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"]

    for i in range(random.randint(15, 20)):
        hour = random.randint(9, 16)
        minute = random.choice([0, 15, 30, 45])
        duration = random.choice([30, 45, 60])

        start_time = selected_date.replace(hour=hour, minute=minute)
        end_time = start_time + timedelta(minutes=duration)

        appointment = Appointment(
            id=f"APT{i + 1}",
            start_time=start_time,
            end_time=end_time,
            pet_name=random.choice(pet_names),
            pet_type=random.choice(pet_types),
            appointment_type=random.choice(list(AppointmentType)),
            vet=random.choice(vets),
            owner_name=random.choice(owner_names),
            status=random.choice(["Confirmed", "Check-in", "In Progress", "Completed"]),
            notes=""
        )
        appointments.append(appointment)

    st.session_state.appointments = sorted(appointments, key=lambda x: x.start_time)
    return st.session_state.appointments


def edit_appointment_modal():
    if st.session_state.editing_appointment is None:
        return

    apt = st.session_state.editing_appointment
    pricing_calculator = PricingCalculator()

    with st.form(key="edit_appointment_form", clear_on_submit=True):
        st.subheader("Edit Appointment")

        # Basic information
        col1, col2 = st.columns(2)

        with col1:
            new_pet_name = st.text_input("Pet Name", apt.pet_name)
            new_pet_type = st.selectbox(
                "Pet Type",
                ["Dog", "Cat", "Bird", "Rabbit", "Hamster"],
                index=["Dog", "Cat", "Bird", "Rabbit", "Hamster"].index(apt.pet_type)
            )
            new_owner_name = st.text_input("Owner Name", apt.owner_name)
            is_repeat_customer = st.checkbox("Repeat Customer", value=False)

        with col2:
            new_appointment_type = st.selectbox(
                "Appointment Type",
                [type.value for type in AppointmentType],
                index=[type.value for type in AppointmentType].index(apt.appointment_type.value)
            )
            new_vet = st.selectbox(
                "Veterinarian",
                st.session_state.vets,
                index=[v.id for v in st.session_state.vets].index(apt.vet.id),
                format_func=lambda x: x.name
            )
            new_status = st.selectbox(
                "Status",
                ["Confirmed", "Check-in", "In Progress", "Completed"],
                index=["Confirmed", "Check-in", "In Progress", "Completed"].index(apt.status)
            )
            is_emergency = st.checkbox("Emergency Appointment", value=False)

        # Time selection
        st.subheader("Appointment Time")
        time_col1, time_col2 = st.columns(2)

        current_duration = int((apt.end_time - apt.start_time).total_seconds() / 60)

        with time_col1:
            new_date = st.date_input("Date", apt.start_time.date())
            new_start_time = st.time_input("Start Time", apt.start_time.time())

        with time_col2:
            duration = st.selectbox(
                "Duration (minutes)",
                [30, 45, 60],
                index=[30, 45, 60].index(current_duration)
            )

        # Calculate and display pricing
        price_info = pricing_calculator.calculate_price(
            appointment_type=AppointmentType(new_appointment_type),
            duration=duration,
            pet_type=new_pet_type,
            start_time=datetime.combine(new_date, new_start_time),
            is_emergency=is_emergency,
            is_repeat_customer=is_repeat_customer
        )

        # Display pricing breakdown
        st.subheader("📊 Pricing Breakdown")
        price_col1, price_col2 = st.columns(2)

        with price_col1:
            st.write(f"Base Price: ${price_info['base_price']:.2f}")
            st.write(f"Duration Adjustment: {price_info['duration_adjustment']}")
            st.write(f"Pet Type Adjustment: {price_info['pet_type_adjustment']}")

        with price_col2:
            st.write(f"Time of Day Adjustment: {price_info['time_of_day_adjustment']}")
            if price_info['emergency_fee'] == "Yes":
                st.write("Emergency Fee: +50%")
            if price_info['repeat_customer_discount'] == "Yes":
                st.write("Repeat Customer Discount: -10%")

        st.markdown(f"### Final Price: ${price_info['final_price']:.2f}")

        # Notes
        new_notes = st.text_area("Notes", apt.notes)

        # Form submit buttons
        submit_col1, submit_col2 = st.columns(2)
        with submit_col1:
            submit_button = st.form_submit_button(
                label="Save Changes",
                type="primary",
                use_container_width=True
            )
        with submit_col2:
            cancel_button = st.form_submit_button(
                label="Cancel",
                type="secondary",
                use_container_width=True
            )

        # Handle form submission
        if submit_button:
            new_start_datetime = datetime.combine(new_date, new_start_time)
            new_end_datetime = new_start_datetime + timedelta(minutes=duration)

            new_appointment = Appointment(
                id=apt.id,
                start_time=new_start_datetime,
                end_time=new_end_datetime,
                pet_name=new_pet_name,
                pet_type=new_pet_type,
                appointment_type=AppointmentType(new_appointment_type),
                vet=new_vet,
                owner_name=new_owner_name,
                status=new_status,
                notes=f"{new_notes}\nPrice: ${price_info['final_price']:.2f}"
            )

            idx = next(i for i, a in enumerate(st.session_state.appointments) if a.id == apt.id)
            st.session_state.appointments[idx] = new_appointment
            st.session_state.editing_appointment = None
            st.session_state.show_edit_modal = False
            st.rerun()

        if cancel_button:
            st.session_state.editing_appointment = None
            st.session_state.show_edit_modal = False
            st.rerun()

    # Delete button outside form
    if st.button("🗑️ Delete Appointment", type="primary", use_container_width=True):
        st.session_state.appointments = [
            a for a in st.session_state.appointments if a.id != apt.id
        ]
        st.session_state.editing_appointment = None
        st.session_state.show_edit_modal = False
        st.rerun()

def create_gantt_chart(appointments: List[Appointment], vets: List[Veterinarian]):
    df_dict = {
        'Task': [],
        'Start': [],
        'Finish': [],
        'Resource': [],
        'Description': [],
    }

    colors = []

    for appt in appointments:
        df_dict['Task'].append(appt.vet.name)
        df_dict['Start'].append(appt.start_time)
        df_dict['Finish'].append(appt.end_time)
        df_dict['Resource'].append(appt.appointment_type.value)
        df_dict['Description'].append(
            f"<b>{appt.pet_name}</b> ({appt.pet_type})<br>"
            f"Owner: {appt.owner_name}<br>"
            f"Status: {appt.status}<br>"
            f"Click to edit"
        )
        colors.append(appt.vet.color)

    df = pd.DataFrame(df_dict)

    fig = ff.create_gantt(
        df,
        colors=colors,
        index_col='Resource',
        show_colorbar=True,
        group_tasks=True,
        showgrid_x=True,
        showgrid_y=True,
        height=400,
        title='Daily Clinic Schedule'
    )

    # Make the chart interactive
    fig.update_layout(
        xaxis_title="Time",
        yaxis_title="Veterinarian",
        font=dict(size=12),
        hoverlabel=dict(bgcolor="white"),
        showlegend=True
    )

    # Add custom data for click events
    for i, trace in enumerate(fig.data):
        trace.customdata = list(range(len(trace.x)))
        trace.hovertemplate = (
            "%{text}<br>"
            "<extra></extra>"
        )

    return fig


def main():
    init_session_state()

    st.title("🐾 Veterinary Clinic Daily Schedule")

    # Main interface
    col1, col2 = st.columns([2, 3])

    with col1:
        selected_date = st.date_input("Select Date", datetime.now())
        selected_datetime = datetime.combine(selected_date, datetime.min.time())

        # Generate or retrieve appointments
        appointments = generate_sample_appointments(selected_datetime, st.session_state.vets)

        # Add new appointment button
        if st.button("➕ Add New Appointment"):
            # Create empty appointment for editing
            new_apt = Appointment(
                id=f"APT{len(appointments) + 1}",
                start_time=selected_datetime.replace(hour=9),
                end_time=selected_datetime.replace(hour=9) + timedelta(minutes=30),
                pet_name="",
                pet_type="Dog",
                appointment_type=AppointmentType.CHECKUP,
                vet=st.session_state.vets[0],
                owner_name="",
                status="Confirmed",
                notes=""
            )
            st.session_state.editing_appointment = new_apt
            st.session_state.show_edit_modal = True
            st.rerun()

    # Summary statistics
    st.subheader("📊 Daily Summary")
    total_appointments = len(appointments)
    st.metric("Total Appointments", total_appointments)

    # Appointments by type
    st.subheader("📋 Appointments by Type")
    type_counts = {}
    for appt in appointments:
        if appt is not None and hasattr(appt, 'appointment_type'):
            type_value = appt.visit_type.value if hasattr(appt, 'visit_type') else appt.appointment_type.value
            type_counts[type_value] = type_counts.get(type_value, 0) + 1

    for appt_type, count in type_counts.items():
        st.text(f"{appt_type}: {count}")

    with col2:
        # Veterinarian workload
        st.subheader("👩‍⚕️ Veterinarian Workload")
        vet_loads = {}
        for appt in appointments:
            vet_loads[appt.vet.name] = vet_loads.get(appt.vet.name, 0) + 1

        for vet_name, count in vet_loads.items():
            utilization = (count / 16) * 100
            st.progress(utilization / 100)
            st.text(f"{vet_name}: {count} appointments ({utilization:.1f}% utilization)")

    # Gantt chart with click handling
    st.subheader("📅 Daily Schedule")
    fig = create_gantt_chart(appointments, st.session_state.vets)

    # Use Streamlit's native plotly chart display with events
    clicked = st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": False}
    )

    # Show edit modal if active
    if st.session_state.show_edit_modal:
        edit_appointment_modal()

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
                if appt is not None:
                    st.write("**Time**")
                    st.write(f"Start: {appt.start_time.strftime('%H:%M')}")
                    st.write(f"End: {appt.end_time.strftime('%H:%M')}")

            with cols[3]:
                st.write("**Actions**")
                # Use unique keys for each button
                edit_col, delete_col = st.columns(2)
                with edit_col:
                    if st.button("✏️ Edit", key=f"edit_{appt.id}"):
                        st.session_state.editing_appointment = appt
                        st.session_state.show_edit_modal = True
                        st.rerun()

                with delete_col:
                    if st.button("🗑️ Delete", key=f"delete_{appt.id}"):
                        if st.session_state.appointments:
                            st.session_state.appointments = [
                                a for a in st.session_state.appointments if a.id != appt.id
                            ]
                            st.rerun()


if __name__ == "__main__":
    main()