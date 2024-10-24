from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import numpy as np
from enum import Enum


class VisitType(Enum):
    CONSULT = "consult"
    WELLNESS = "wellness"
    VACCINATION = "vaccination"
    SURGERY = "surgery"
    GROOMING = "grooming"
    EUTHANASIA = "euthanasia"
    DENTAL = "dental"
    SPECIALTY = "specialty"


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
        expiring_inventory: Dict[VisitType, float]
) -> float:
    """Calculate a score for a proposed appointment time based on multiple factors."""

    score = 0.0

    # Factor 1: Staff availability and capability (0-20 points)
    available_staff = [
        s for s in staff_roster.values()
        if visit_type in s.capabilities
           and abs((s.lunch_start - proposed_time).total_seconds()) > 3600
    ]
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

    # Factor 4: Health complexity consideration (0-15 points)
    if 9 <= proposed_time.hour <= 14:  # Prefer complex cases during middle of day
        score += 15 * (1 - pet.health_complexity)
    else:
        score += 15 * pet.health_complexity

    # Factor 5: Expiring inventory (0-10 points)
    if visit_type in expiring_inventory:
        score += 10 * expiring_inventory[visit_type]

    # Factor 6: Customer reliability (0-15 points)
    if customer.late_history > 0.2 or customer.no_show_history > 0.1:
        if 10 <= proposed_time.hour <= 15:  # High demand hours
            score += 15
    else:
        score += 15

    # Factor 7: Time of day preferences (0-10 points)
    if 9 <= proposed_time.hour <= 16:  # Core hours
        score += 10
    elif proposed_time.hour < 9 or proposed_time.hour >= 16:
        score += 5

    return score


def get_three_best_appointments(
        schedule: Dict[datetime, TimeSlot],
        staff_roster: Dict[str, Staff],
        type_of_visit: VisitType,
        customer_details: Customer,
        pet_details: Pet,
        expiring_inventory: Dict[VisitType, float]
) -> List[datetime]:
    """
    Get the three best appointment times based on multiple criteria.
    Returns a list of three datetime objects representing optimal appointment times.
    """

    # Generate potential time slots (every 30 minutes from 9 AM to 5 PM)
    current_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    potential_times = []

    while current_date.hour < 17:
        if current_date not in schedule:  # Only consider unbooked slots
            potential_times.append(current_date)
        current_date += timedelta(minutes=30)

    # Score each potential time slot
    scored_times = [
        (
            time,
            calculate_slot_score(
                time,
                schedule,
                staff_roster,
                type_of_visit,
                customer_details,
                pet_details,
                expiring_inventory
            )
        )
        for time in potential_times
    ]

    # Sort by score and return top 3
    scored_times.sort(key=lambda x: x[1], reverse=True)
    return [time for time, score in scored_times[:3]]


# Example usage and testing function
def test_scheduler():
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

    best_times = get_three_best_appointments(
        schedule,
        staff_roster,
        VisitType.VACCINATION,
        customer,
        pet,
        expiring_inventory
    )

    return best_times