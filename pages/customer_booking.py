from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Set

import streamlit as st


@dataclass
class Veterinarian:
    id: str
    name: str
    specialties: Set[str]
    experience_years: int
    base_rate: float
    schedule: Dict[str, List[datetime]] = field(default_factory=dict)
    max_daily_appointments: int = 8
    emergency_qualified: bool = False

    def is_available(self, time_slot: datetime) -> bool:
        """Check if vet is available at given time slot."""
        date_key = time_slot.date().isoformat()
        if date_key not in self.schedule:
            return True
        return len(self.schedule[date_key]) < self.max_daily_appointments

    def book_appointment(self, time_slot: datetime):
        """Book an appointment for the vet."""
        date_key = time_slot.date().isoformat()
        if date_key not in self.schedule:
            self.schedule[date_key] = []
        self.schedule[date_key].append(time_slot)

@dataclass
class EmergencyCase:
    severity_level: int  # 1-5, where 5 is most severe
    symptoms: List[str]
    pet_type: 'PetType'
    estimated_duration: int
    required_specialty: Optional[str] = None

@dataclass
class AppointmentOption:
    datetime: datetime
    price: float
    vet: Veterinarian
    discount: Optional[float] = None
    message: Optional[str] = None
    priority_level: Optional[str] = None
    estimated_duration: int = 30  # minutes
    waiting_list_position: Optional[int] = None
    cancellation_policy: str = "Standard 24-hour notice required"

class ClinicDemand(Enum):
    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"

class PetType(Enum):
    CAT = "feline"
    DOG = "canine"
    EXOTIC = "exotic"
    BIRD = "avian"

class AppointmentType(Enum):
    CHECKUP = "checkup"
    VACCINATION = "vaccination"
    SURGERY = "surgery"
    EMERGENCY = "emergency"
    GROOMING = "grooming"
    DENTAL = "dental"
    SPECIALTY_CONSULT = "specialty_consult"

class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    WINTER = "winter"

class EmergencyHandler:
    def __init__(self, vets: List[Veterinarian]):
        self.emergency_qualified_vets = [v for v in vets if v.emergency_qualified]
        self.emergency_slots = defaultdict(list)
        self.waiting_list = []

    def assess_emergency(self, case: EmergencyCase) -> Dict:
        """Assess emergency case and determine handling strategy."""
        wait_time = self._calculate_wait_time(case)
        available_vet = self._find_available_emergency_vet(case)

        return {
            'wait_time': wait_time,
            'vet': available_vet,
            'severity_level': case.severity_level,
            'needs_referral': available_vet is None and case.severity_level >= 4,
            'recommended_action': self._get_recommended_action(case, wait_time, available_vet)
        }

    def _calculate_wait_time(self, case: EmergencyCase) -> int:
        """Calculate estimated wait time in minutes based on current load and severity."""
        base_wait = len(self.waiting_list) * 15
        severity_adjustment = (6 - case.severity_level) * 10
        return max(0, base_wait + severity_adjustment)

    def _find_available_emergency_vet(self, case: EmergencyCase) -> Optional[Veterinarian]:
        """Find the most suitable available emergency vet."""
        available_vets = [v for v in self.emergency_qualified_vets if v.is_available(datetime.now())]
        if case.required_specialty:
            available_vets = [v for v in available_vets if case.required_specialty in v.specialties]
        return min(available_vets, key=lambda v: len(v.schedule), default=None)

    def _get_recommended_action(self, case: EmergencyCase, wait_time: int, available_vet: Optional[Veterinarian]) -> str:
        if case.severity_level >= 4 and not available_vet:
            return "Immediate referral to emergency animal hospital"
        elif wait_time > 60 and case.severity_level >= 3:
            return "Consider referral to partner clinic"
        elif available_vet:
            return f"Proceed with emergency appointment with Dr. {available_vet.name}"
        else:
            return f"Add to waiting list (estimated wait: {wait_time} minutes)"

class CapacityPlanner:
    def __init__(self, vets: List[Veterinarian]):
        self.vets = vets
        self.overbooking_threshold = 0.8
        self.max_overbook_slots = 2
        self.waiting_lists = defaultdict(list)

    def check_capacity(self, date: datetime) -> Dict:
        """Check clinic capacity for a given date."""
        total_slots = sum(v.max_daily_appointments for v in self.vets)
        booked_slots = sum(len(v.schedule.get(date.date().isoformat(), [])) for v in self.vets)

        utilization = booked_slots / total_slots
        can_overbook = utilization >= self.overbooking_threshold

        return {
            'utilization': utilization,
            'available_regular_slots': total_slots - booked_slots,
            'can_overbook': can_overbook,
            'waiting_list_length': len(self.waiting_lists[date.date().isoformat()]),
            'recommended_action': self._get_capacity_recommendation(utilization)
        }

    def _get_capacity_recommendation(self, utilization: float) -> str:
        if utilization >= 0.95:
            return "Implement emergency-only policy"
        elif utilization >= 0.85:
            return "Start waiting list"
        elif utilization <= 0.5:
            return "Implement promotional pricing"
        return "Normal operations"

class SeasonalPricingEngine:
    def __init__(self):
        self.SEASONAL_MULTIPLIERS = {
            Season.SPRING: {
                'vaccination': 1.2,  # Higher demand for vaccinations
                'checkup': 1.1,
                'grooming': 1.15
            },
            Season.SUMMER: {
                'emergency': 1.25,  # More emergencies
                'grooming': 1.3,
                'vaccination': 0.9
            },
            Season.FALL: {
                'checkup': 0.9,
                'dental': 0.85,
                'vaccination': 0.95
            },
            Season.WINTER: {
                'emergency': 1.15,
                'grooming': 0.8,
                'dental': 1.1
            }
        }

        self.SEASONAL_PROMOTIONS = {
            Season.SPRING: ["Spring vaccination campaign - 10% off all vaccinations"],
            Season.SUMMER: ["Summer grooming special - Package deals available"],
            Season.FALL: ["Fall health check - Comprehensive exam package"],
            Season.WINTER: ["Winter wellness - Dental cleaning discount"]
        }

    def get_seasonal_adjustment(self, appointment_type: AppointmentType, date: datetime) -> Dict:
        season = self._get_season(date)
        base_multiplier = self.SEASONAL_MULTIPLIERS[season].get(
            appointment_type.value, 1.0
        )

        # Additional adjustments based on specific dates
        holiday_adjustment = self._get_holiday_adjustment(date)
        weather_adjustment = self._get_weather_adjustment(season)

        final_multiplier = base_multiplier * holiday_adjustment * weather_adjustment

        return {
            'multiplier': final_multiplier,
            'promotions': self.SEASONAL_PROMOTIONS[season],
            'season': season.value
        }

    def _get_season(self, date: datetime) -> Season:
        month = date.month
        if 3 <= month <= 5:
            return Season.SPRING
        elif 6 <= month <= 8:
            return Season.SUMMER
        elif 9 <= month <= 11:
            return Season.FALL
        else:
            return Season.WINTER

    def _get_holiday_adjustment(self, date: datetime) -> float:
        # Example holiday adjustments
        holiday_periods = {
            (12, 20, 12, 31): 1.2,  # Holiday season premium
            (7, 1, 7, 7): 0.8,      # July 4th week discount
        }

        for (start_month, start_day, end_month, end_day), multiplier in holiday_periods.items():
            if (date.month, date.day) >= (start_month, start_day) and \
               (date.month, date.day) <= (end_month, end_day):
                return multiplier
        return 1.0

    def _get_weather_adjustment(self, season: Season) -> float:
        # Simplified weather adjustment based on season
        weather_multipliers = {
            Season.SUMMER: 1.1,  # Higher prices during peak season
            Season.WINTER: 0.95  # Slight discount during slower season
        }
        return weather_multipliers.get(season, 1.0)

def get_appointment_options(
    client_preferred_time: datetime,
    appointment_type: AppointmentType,
    pet_type: PetType,
    required_specialty: Optional[str] = None,
    is_emergency: bool = False,
    symptoms: Optional[List[str]] = None,
    severity_level: Optional[int] = None,
    is_repeat_customer: bool = False,
    insurance_coverage: bool = False
) -> List[AppointmentOption]:
    """
    Enhanced appointment scheduling system with emergency handling, multiple vets,
    seasonal pricing, and capacity management.
    """
    # Initialize veterinarians (in practice, this would come from a database)
    vets = [
        Veterinarian(
            id="V1", name="Dr. Smith",
            specialties={"general", "surgery"},
            experience_years=15, base_rate=100.00,
            emergency_qualified=True
        ),
        Veterinarian(
            id="V2", name="Dr. Johnson",
            specialties={"exotic"},
            experience_years=8, base_rate=90.00
        ),
        Veterinarian(
            id="V3", name="Dr. Patel",
            specialties={"general", "dental"},
            experience_years=12, base_rate=95.00,
            emergency_qualified=True
        )
    ]

    # Initialize handlers
    emergency_handler = EmergencyHandler(vets)
    capacity_planner = CapacityPlanner(vets)
    seasonal_pricing = SeasonalPricingEngine()
    options = []

    # Handle emergency cases
    if is_emergency and symptoms and severity_level:
        emergency_case = EmergencyCase(
            severity_level=severity_level,
            symptoms=symptoms,
            pet_type=pet_type,
            estimated_duration=45,
            required_specialty=required_specialty
        )

        assessment = emergency_handler.assess_emergency(emergency_case)
        if assessment['vet']:
            # Create emergency appointment option
            seasonal_adj = seasonal_pricing.get_seasonal_adjustment(
                AppointmentType.EMERGENCY,
                client_preferred_time
            )

            emergency_price = (assessment['vet'].base_rate * 1.5 *
                             seasonal_adj['multiplier'])

            options.append(AppointmentOption(
                datetime=client_preferred_time + timedelta(minutes=15),
                price=emergency_price,
                vet=assessment['vet'],
                message=f"Emergency slot - {assessment['recommended_action']}",
                priority_level="HIGH",
                estimated_duration=45,
                cancellation_policy="Emergency appointments cannot be cancelled"
            ))
            return options

    # Check capacity for regular appointments
    capacity_status = capacity_planner.check_capacity(client_preferred_time)

    # Get seasonal pricing adjustments
    seasonal_adj = seasonal_pricing.get_seasonal_adjustment(
        appointment_type,
        client_preferred_time
    )

    # Filter suitable vets
    suitable_vets = [
        v for v in vets
        if not required_specialty or required_specialty in v.specialties
    ]

    if not suitable_vets:
        return [AppointmentOption(
            datetime=client_preferred_time,
            price=0,
            vet=vets[0],  # Default vet for message
            message="No suitable veterinarian available for this specialty. Consider referral.",
            priority_level="LOW"
        )]

    # Generate options based on capacity and veterinarian availability
    for vet in suitable_vets:
        if vet.is_available(client_preferred_time):
            base_price = vet.base_rate * seasonal_adj['multiplier']

            # Apply experience multiplier
            experience_multiplier = 1 + (vet.experience_years * 0.01)
            price = base_price * experience_multiplier

            # Apply repeat customer discount
            if is_repeat_customer:
                price *= 0.9

            # Apply insurance coverage
            if insurance_coverage:
                price *= 0.7

            options.append(AppointmentOption(
                datetime=client_preferred_time,
                price=price,
                vet=vet,
                discount=seasonal_adj.get('promotions', []),
                message=f"Available with Dr. {vet.name}",
                estimated_duration=45 if appointment_type == AppointmentType.SURGERY else 30,
                cancellation_policy="Standard 24-hour notice required"
            ))

    # Handle overbooking if necessary
    if not options and capacity_status['can_overbook']:
        overbook_vet = min(suitable_vets, key=lambda v: len(v.schedule))
        overbook_price = overbook_vet.base_rate * 1.2  # 20% premium for overbooked slots

        options.append(AppointmentOption(
            datetime=client_preferred_time,
            price=overbook_price,
            vet=overbook_vet,
            message="Overbooked slot - may experience delays",
            estimated_duration=30,
            waiting_list_position=len(capacity_planner.waiting_lists[
                client_preferred_time.date().isoformat()
            ]) + 1
        ))

    return options

def initialize_vets():
    return [
        Veterinarian(
            id="V1", name="Dr. Smith",
            specialties={"general", "surgery"},
            experience_years=15, base_rate=100.00,
            emergency_qualified=True
        ),
        Veterinarian(
            id="V2", name="Dr. Johnson",
            specialties={"exotic", "birds"},
            experience_years=8, base_rate=90.00
        ),
        Veterinarian(
            id="V3", name="Dr. Patel",
            specialties={"general", "dental"},
            experience_years=12, base_rate=95.00,
            emergency_qualified=True
        )
    ]

def main():
    st.set_page_config(page_title="Veterinary Clinic Appointment Scheduler", layout="wide")

    st.title("🐾 Clinic Appointment Scheduler")

    # Initialize session state for storing appointment data
    if 'appointments' not in st.session_state:
        st.session_state.appointments = [
            AppointmentOption(
                datetime=datetime.now().replace(hour=9, minute=0),
                price=100.00,
                vet=Veterinarian(
                    id="V1", name="Dr. Smith",
                    specialties={"general", "surgery"},
                    experience_years=15, base_rate=100.00,
                    emergency_qualified=True
                )
            )

        ]

    # Sidebar for appointment type selection
    with st.sidebar:
        st.header("Appointment Settings")

        # Basic appointment details
        appointment_type = st.selectbox(
            "Appointment Type",
            options=[type.value for type in AppointmentType]
        )

        pet_type = st.selectbox(
            "Pet Type",
            options=[type.value for type in PetType]
        )

        # Date and time selection
        appointment_date = st.date_input(
            "Preferred Date",
            min_value=datetime.now().date(),
            max_value=datetime.now().date() + timedelta(days=60)
        )

        appointment_time = st.time_input(
            "Preferred Time",
            value=datetime.now().replace(hour=9, minute=0).time()
        )

        # Additional details
        is_repeat_customer = st.checkbox("Repeat Customer")
        insurance_coverage = st.checkbox("Has Insurance Coverage")

        # Emergency-specific details
        is_emergency = st.checkbox("Emergency Case")

        if is_emergency:
            severity_level = st.slider("Emergency Severity (1-5)", 1, 5, 3)
            symptoms = st.multiselect(
                "Symptoms",
                options=["difficulty breathing", "lethargy", "vomiting", "trauma",
                        "severe pain", "bleeding", "poisoning", "seizures"]
            )
        else:
            severity_level = None
            symptoms = None

        # Specialty requirements
        required_specialty = st.selectbox(
            "Required Specialty",
            options=["None", "general", "surgery", "exotic", "birds", "dental"]
        )
        if required_specialty == "None":
            required_specialty = None

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Available Appointments")

        if st.button("Find Available Appointments"):
            # Combine date and time into datetime
            preferred_time = datetime.combine(appointment_date, appointment_time)

            # Get appointment options
            options = get_appointment_options(
                client_preferred_time=preferred_time,
                appointment_type=AppointmentType(appointment_type),
                pet_type=PetType(pet_type),
                required_specialty=required_specialty,
                is_emergency=is_emergency,
                symptoms=symptoms,
                severity_level=severity_level,
                is_repeat_customer=is_repeat_customer,
                insurance_coverage=insurance_coverage
            )

            # Display appointment options
            if options:
                for i, option in enumerate(options, 1):
                    with st.expander(f"Option {i}: Dr. {option.vet.name} - ${option.price:.2f}"):
                        st.write(f"**Date/Time:** {option.datetime.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Duration:** {option.estimated_duration} minutes")
                        if option.discount:
                            st.write(f"**Promotions:** {option.discount}")
                        if option.message:
                            st.write(f"**Note:** {option.message}")
                        if option.waiting_list_position:
                            st.write(f"**Waiting List Position:** {option.waiting_list_position}")
                        st.write(f"**Cancellation Policy:** {option.cancellation_policy}")

                        if st.button(f"Book Appointment with Dr. {option.vet.name}", key=f"book_{i}"):
                            option.vet.book_appointment(option.datetime)
                            st.session_state.appointments.append(option)
                            st.success("Appointment booked successfully!")
            else:
                st.warning("No available appointments found for the selected criteria.")

    with col2:
        st.header("Your Appointments")
        if st.session_state.appointments:
            for i, apt in enumerate(st.session_state.appointments, 1):
                if apt is not None and hasattr(apt, 'datetime'):
                    with st.expander(f"Appointment {i}"):
                        st.write(f"**Date:** {apt.datetime.strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"**Doctor:** Dr. {apt.vet.name}")
                        st.write(f"**Price:** ${apt.price:.2f}")
                        st.write(f"**Duration:** {apt.estimated_duration} minutes")
                        if st.button("Cancel Appointment", key=f"cancel_{i}"):
                            st.session_state.appointments.remove(apt)
                            st.success("Appointment cancelled successfully!")
        else:
            st.info("No appointments booked yet.")

if __name__ == "__main__":
    main()
