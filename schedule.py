from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Set, Optional
from plotly import graph_objects as go

from visit_type import VisitType

@dataclass
class TimeSlot:
    start_time: datetime
    end_time: datetime
    visit_type: VisitType
    staff_id: str
    species: str


@dataclass
class Staff:
    id: str
    capabilities: List[VisitType]
    lunch_start: datetime


@dataclass
class Customer:
    id: str
    late_history: float  # Percentage of late arrivals
    no_show_history: float  # Percentage of no-shows


@dataclass
class Pet:
    id: str
    species: str
    health_complexity: float  # 0-1 scale of appointment complexity
    visit_history: List[TimeSlot]


def calculate_slot_score(
        proposed_time: datetime,
        schedule: Dict[datetime, TimeSlot],
        staff_roster: Dict[str, Staff],
        visit_type: VisitType,
        customer: Customer,
        pet: Pet,
        expiring_inventory: Dict[VisitType, float],
        time_slot_generator: 'AdvancedTimeSlotGenerator'
) -> float:
    """Calculate a score for a proposed appointment time based on multiple factors."""

    score = 0.0

    # Get appointment details from generator
    appointment_details = time_slot_generator.get_appointment_details(
        proposed_time,
        visit_type,
        pet
    )

    # Factor 1: Staff availability and capability (0-20 points)
    available_staff = time_slot_generator._check_staff_availability(
        proposed_time,
        appointment_details['duration'],
        staff_roster,
        schedule,
        visit_type
    )
    if not available_staff:
        return 0
    score += 20 * (len(available_staff) / len(staff_roster))

    # Factor 2: Visit type alignment (0-15 points)
    neighboring_slots = [
        slot for time, slot in schedule.items()
        if abs((time - proposed_time).total_seconds()) <= 3600
    ]
    similar_type_count = sum(1 for slot in neighboring_slots if slot.visit_type == visit_type)
    score += 15 * (similar_type_count / max(1, len(neighboring_slots)))

    # Factor 3: Species alignment (0-15 points)
    same_species_count = sum(1 for slot in neighboring_slots if slot.species == pet.species)
    score += 15 * (same_species_count / max(1, len(neighboring_slots)))

    # Factor 4: Health complexity consideration (0-10 points)
    if appointment_details['duration'] >= appointment_details['duration']:
        score += 10  # Adequate time allocated for complexity
    else:
        score += 5  # Minimum required time allocated

    # Factor 5: Preferred time range (0-10 points)
    if appointment_details['is_preferred_time']:
        score += 10

    # Factor 6: Expiring inventory (0-10 points)
    if visit_type in expiring_inventory:
        score += 10 * expiring_inventory[visit_type]

    # Factor 7: Customer reliability (0-10 points)
    peak_hours = 10 <= proposed_time.hour <= 15
    if customer.late_history > 0.2 or customer.no_show_history > 0.1:
        if peak_hours:  # High demand hours better for unreliable clients
            score += 10
        else:
            score += 5
    else:
        if peak_hours:  # Reliable clients get more flexibility
            score += 5
        else:
            score += 10

    # Factor 8: Padding time optimization (0-10 points)
    padding_score = 10
    for existing_time, slot in schedule.items():
        time_diff = abs((existing_time - proposed_time).total_seconds() / 60)
        if time_diff < appointment_details['padding_before']:
            padding_score -= 2
        if time_diff < appointment_details['padding_after']:
            padding_score -= 2
    score += max(0, padding_score)

    return score


def get_three_best_appointments(
        schedule: Dict[datetime, TimeSlot],
        staff_roster: Dict[str, Staff],
        type_of_visit: VisitType,
        customer_details: Customer,
        pet_details: Pet,
        expiring_inventory: Dict[VisitType, float],
        potential_slots: Optional[List[datetime]] = None,
        time_slot_generator: Optional['AdvancedTimeSlotGenerator'] = None
) -> List[datetime]:
    """
    Get the three best appointment times based on multiple criteria.
    Returns a list of three datetime objects representing optimal appointment times.

    Args:
        schedule: Dictionary of existing appointments
        staff_roster: Dictionary of staff members
        type_of_visit: Type of visit being scheduled
        customer_details: Customer information
        pet_details: Pet information
        expiring_inventory: Dictionary of inventory expiration status
        potential_slots: Optional list of pre-generated potential time slots
        time_slot_generator: Optional AdvancedTimeSlotGenerator instance
    """

    if potential_slots is None:
        # Generate potential time slots (every 30 minutes from 9 AM to 5 PM)
        current_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        potential_slots = []

        while current_date.hour < 17:
            if current_date not in schedule:
                potential_slots.append(current_date)
            current_date += timedelta(minutes=30)

    # Score each potential time slot
    scored_times = []
    for time in potential_slots:
        score = calculate_slot_score(
            time,
            schedule,
            staff_roster,
            type_of_visit,
            customer_details,
            pet_details,
            expiring_inventory,
            time_slot_generator
        ) if time_slot_generator else 0

        # Additional scoring for slots from the generator
        if time_slot_generator:
            details = time_slot_generator.get_appointment_details(
                time,
                type_of_visit,
                pet_details
            )

            # Bonus points for optimal duration
            if details['duration'] == time_slot_generator.visit_configs[type_of_visit].recommended_duration.value:
                score += 5

            # Penalty for non-preferred times
            if not details['is_preferred_time']:
                score -= 10

        scored_times.append((time, score))

    # Sort by score and return top 3
    scored_times.sort(key=lambda x: x[1], reverse=True)
    return [time for time, score in scored_times[:3]]


# Example usage with the advanced time slot generator
def test_advanced_scheduler():
    generator = AdvancedTimeSlotGenerator()

    # Sample data setup
    schedule = {
        datetime(2024, 10, 24, 9, 0): TimeSlot(
            datetime(2024, 10, 24, 9, 0),
            datetime(2024, 10, 24, 9, 30),
            VisitType.VACCINATION,
            "staff1",
            "dog"
        )
    }

    staff_roster = {
        "staff1": Staff(
            "staff1",
            [VisitType.VACCINATION, VisitType.WELLNESS],
            datetime(2024, 10, 24, 12, 0)
        ),
        "staff2": Staff(
            "staff2",
            [VisitType.SURGERY, VisitType.DENTAL],
            datetime(2024, 10, 24, 13, 0)
        )
    }

    customer = Customer("cust1", 0.1, 0.05)
    pet = Pet("pet1", "dog", 0.3, [])
    expiring_inventory = {VisitType.VACCINATION: 0.8}

    # Generate potential slots using the advanced generator
    potential_slots = generator.generate_potential_slots(
        schedule,
        staff_roster,
        VisitType.VACCINATION,
        pet
    )

    # Get best appointments using the enhanced system
    best_times = get_three_best_appointments(
        schedule,
        staff_roster,
        VisitType.VACCINATION,
        customer,
        pet,
        expiring_inventory,
        potential_slots,
        generator
    )

    return best_times


from schedule import VisitType, Staff, TimeSlot, Pet


class TimeSlotDuration(Enum):
    SHORT = 15
    STANDARD = 30
    EXTENDED = 45
    LONG = 60


@dataclass
class VisitDurationConfig:
    """Configuration for visit type duration and padding"""
    min_duration: TimeSlotDuration
    recommended_duration: TimeSlotDuration
    max_duration: TimeSlotDuration
    padding_before: int  # minutes
    padding_after: int  # minutes
    preferred_time_ranges: List[tuple[int, int]]  # List of (start_hour, end_hour)


class AdvancedTimeSlotGenerator:
    def __init__(self):
        self.visit_configs = {
            VisitType.CONSULT: VisitDurationConfig(
                TimeSlotDuration.STANDARD,
                TimeSlotDuration.STANDARD,
                TimeSlotDuration.EXTENDED,
                5, 5,
                [(9, 17)]
            ),
            VisitType.WELLNESS: VisitDurationConfig(
                TimeSlotDuration.STANDARD,
                TimeSlotDuration.STANDARD,
                TimeSlotDuration.EXTENDED,
                5, 5,
                [(9, 17)]
            ),
            VisitType.VACCINATION: VisitDurationConfig(
                TimeSlotDuration.SHORT,
                TimeSlotDuration.STANDARD,
                TimeSlotDuration.STANDARD,
                5, 5,
                [(9, 17)]
            ),
            VisitType.SURGERY: VisitDurationConfig(
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                15, 15,
                [(9, 14)]  # Surgeries preferably in morning
            ),
            VisitType.GROOMING: VisitDurationConfig(
                TimeSlotDuration.EXTENDED,
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                10, 10,
                [(9, 16)]
            ),
            VisitType.EUTHANASIA: VisitDurationConfig(
                TimeSlotDuration.EXTENDED,
                TimeSlotDuration.EXTENDED,
                TimeSlotDuration.LONG,
                15, 15,
                [(10, 16)]  # Avoid early morning/late evening
            ),
            VisitType.DENTAL: VisitDurationConfig(
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                15, 15,
                [(9, 14)]  # Dentals preferably in morning
            ),
            VisitType.SPECIALTY: VisitDurationConfig(
                TimeSlotDuration.EXTENDED,
                TimeSlotDuration.LONG,
                TimeSlotDuration.LONG,
                10, 10,
                [(9, 16)]
            )
        }

    def _is_time_in_preferred_range(
            self,
            time: datetime,
            visit_type: VisitType
    ) -> bool:
        """Check if time falls within preferred ranges for visit type"""
        config = self.visit_configs[visit_type]
        hour = time.hour

        return any(
            start <= hour <= end
            for start, end in config.preferred_time_ranges
        )

    def _check_staff_availability(
            self,
            time: datetime,
            duration: int,
            staff_roster: Dict[str, Staff],
            schedule: Dict[datetime, TimeSlot],
            visit_type: VisitType
    ) -> Set[str]:
        """Return set of available staff IDs for given time period"""
        available_staff = set()

        for staff_id, staff in staff_roster.items():
            # Check if staff can perform this type of visit
            if visit_type not in staff.capabilities:
                continue

            # Check if staff is on lunch break
            lunch_end = staff.lunch_start + timedelta(hours=1)
            if staff.lunch_start <= time < lunch_end:
                continue

            # Check if staff is already booked
            is_available = True
            check_time = time
            while check_time < time + timedelta(minutes=duration):
                if check_time in schedule and schedule[check_time].staff_id == staff_id:
                    is_available = False
                    break
                check_time += timedelta(minutes=15)

            if is_available:
                available_staff.add(staff_id)

        return available_staff

    def generate_potential_slots(
            self,
            schedule: Dict[datetime, TimeSlot],
            staff_roster: Dict[str, Staff],
            visit_type: VisitType,
            pet_details: Pet,
            start_date: Optional[datetime] = None
    ) -> List[datetime]:
        """Generate list of potential time slots based on sophisticated criteria"""

        if start_date is None:
            start_date = datetime.now().replace(minute=0, second=0, microsecond=0)
            # If current time is past 5 PM, start with next day
            if start_date.hour >= 17:
                start_date = start_date + timedelta(days=1)
                start_date = start_date.replace(hour=9)

        config = self.visit_configs[visit_type]
        potential_slots = []

        # Adjust duration based on pet health complexity
        base_duration = config.recommended_duration.value
        if pet_details.health_complexity > 0.7:
            duration = config.max_duration.value
        elif pet_details.health_complexity < 0.3:
            duration = config.min_duration.value
        else:
            duration = base_duration

        # Generate slots for the next 5 business days
        current_date = start_date
        days_checked = 0
        while days_checked < 5:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                current_time = current_date.replace(hour=9, minute=0)

                while current_time.hour < 17:
                    # Check if slot meets all criteria
                    if (
                            self._is_time_in_preferred_range(current_time, visit_type) and
                            self._check_staff_availability(
                                current_time,
                                duration + config.padding_before + config.padding_after,
                                staff_roster,
                                schedule,
                                visit_type
                            )
                    ):
                        # Check for conflicts with existing appointments
                        has_conflict = False
                        check_time = current_time
                        while check_time < current_time + timedelta(minutes=duration):
                            if check_time in schedule:
                                has_conflict = True
                                break
                            check_time += timedelta(minutes=15)

                        if not has_conflict:
                            potential_slots.append(current_time)

                    current_time += timedelta(minutes=15)
                days_checked += 1

            current_date += timedelta(days=1)

        return potential_slots

    def get_appointment_details(
            self,
            time: datetime,
            visit_type: VisitType,
            pet_details: Pet
    ) -> Dict:
        """Get detailed information about a potential appointment"""
        config = self.visit_configs[visit_type]

        # Calculate duration based on pet health complexity
        if pet_details.health_complexity > 0.7:
            duration = config.max_duration.value
        elif pet_details.health_complexity < 0.3:
            duration = config.min_duration.value
        else:
            duration = config.recommended_duration.value

        return {
            'start_time': time,
            'end_time': time + timedelta(minutes=duration),
            'duration': duration,
            'padding_before': config.padding_before,
            'padding_after': config.padding_after,
            'is_preferred_time': self._is_time_in_preferred_range(time, visit_type)
        }

