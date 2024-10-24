import random
from datetime import datetime, timedelta
from typing import Dict

from schedule import TimeSlot, Staff
from visit_type import VisitType


class VetClinicDataGenerator:
    def __init__(self):
        self.STAFF_TEMPLATES = {
            'Veterinarian': {
                'capabilities': [
                    VisitType.CONSULT, VisitType.WELLNESS, VisitType.SURGERY,
                    VisitType.EUTHANASIA, VisitType.DENTAL, VisitType.SPECIALTY
                ],
                'count': 5
            },
            'Veterinary Nurse': {
                'capabilities': [
                    VisitType.VACCINATION, VisitType.WELLNESS, VisitType.GROOMING,
                    VisitType.CONSULT
                ],
                'count': 4
            },
            'Veterinary Technician': {
                'capabilities': [
                    VisitType.VACCINATION, VisitType.GROOMING, VisitType.DENTAL
                ],
                'count': 3
            }
        }

        self.STAFF_NAMES = {
            'Veterinarian': [
                'Dr. Sarah Wilson', 'Dr. James Chen', 'Dr. Emily Rodriguez',
                'Dr. Michael Patel', 'Dr. Rachel Kim', 'Dr. David Thompson'
            ],
            'Veterinary Nurse': [
                'Nurse Jessica Brown', 'Nurse William Taylor', 'Nurse Maria Garcia',
                'Nurse Thomas Anderson', 'Nurse Lisa Martinez'
            ],
            'Veterinary Technician': [
                'Tech Alex Johnson', 'Tech Samantha Lee', 'Tech Robert White',
                'Tech Emma Davis'
            ]
        }

        # Species distribution for realistic appointment generation
        self.SPECIES_DISTRIBUTION = {
            'canine': 0.45,
            'feline': 0.35,
            'avian': 0.12,
            'exotic': 0.08
        }

        # Visit type distribution for realistic scheduling
        self.VISIT_TYPE_DISTRIBUTION = {
            VisitType.CONSULT: 0.25,
            VisitType.WELLNESS: 0.20,
            VisitType.VACCINATION: 0.20,
            VisitType.SURGERY: 0.10,
            VisitType.GROOMING: 0.10,
            VisitType.DENTAL: 0.08,
            VisitType.SPECIALTY: 0.05,
            VisitType.EUTHANASIA: 0.02
        }

    def generate_staff_roster(self) -> Dict[str, Staff]:
        """Generate a realistic staff roster with 12 staff members."""
        staff_roster = {}

        # Generate lunch times - spread throughout the day
        lunch_times = []
        base_lunch = datetime.now().replace(hour=11, minute=30, second=0, microsecond=0)
        for i in range(12):
            lunch_times.append(base_lunch + timedelta(minutes=15 * i))
        random.shuffle(lunch_times)

        lunch_idx = 0

        # Generate staff for each role
        for role, details in self.STAFF_TEMPLATES.items():
            names = random.sample(self.STAFF_NAMES[role], details['count'])
            for name in names:
                staff_roster[name] = Staff(
                    id=name,
                    capabilities=details['capabilities'],
                    lunch_start=lunch_times[lunch_idx]
                )
                lunch_idx += 1

        return staff_roster

    def generate_realistic_schedule(
            self,
            staff_roster: Dict[str, Staff],
            date: datetime = None,
            utilization_target: float = 0.85
    ) -> Dict[datetime, TimeSlot]:
        """
        Generate a realistic daily schedule with high utilization but occasional breaks.

        Args:
            staff_roster: Dictionary of staff members
            date: Target date for schedule generation
            utilization_target: Target utilization rate (0-1)
        """
        if date is None:
            date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

        schedule = {}

        # Track staff availability in 15-minute increments
        time_slots = []
        current_time = date
        while current_time.hour < 17:
            time_slots.append(current_time)
            current_time += timedelta(minutes=15)

        # Create staff availability matrix
        staff_availability = {
            staff_id: set(time_slots) for staff_id in staff_roster.keys()
        }

        # Remove lunch breaks from availability
        for staff_id, staff in staff_roster.items():
            lunch_end = staff.lunch_start + timedelta(hours=1)
            lunch_slots = set()
            current_time = staff.lunch_start
            while current_time < lunch_end:
                if current_time in time_slots:
                    lunch_slots.add(current_time)
                current_time += timedelta(minutes=15)
            staff_availability[staff_id] -= lunch_slots

        # Calculate target number of appointments
        total_slots = len(time_slots) * len(staff_roster)
        target_appointments = int(total_slots * utilization_target)

        # Generate appointments
        appointments_created = 0
        max_attempts = target_appointments * 2
        attempts = 0

        while appointments_created < target_appointments and attempts < max_attempts:
            attempts += 1

            # Select random time slot
            time_slot = random.choice(time_slots)

            # Select visit type based on distribution
            visit_type = random.choices(
                list(self.VISIT_TYPE_DISTRIBUTION.keys()),
                weights=list(self.VISIT_TYPE_DISTRIBUTION.values())
            )[0]

            # Select species based on distribution
            species = random.choices(
                list(self.SPECIES_DISTRIBUTION.keys()),
                weights=list(self.SPECIES_DISTRIBUTION.values())
            )[0]

            # Find available staff member
            available_staff = [
                staff_id for staff_id, staff in staff_roster.items()
                if visit_type in staff.capabilities
                   and time_slot in staff_availability[staff_id]
            ]

            if available_staff:
                staff_id = random.choice(available_staff)

                # Determine appointment duration
                if visit_type in [VisitType.SURGERY, VisitType.DENTAL]:
                    duration = 60
                elif visit_type in [VisitType.SPECIALTY, VisitType.EUTHANASIA]:
                    duration = 45
                else:
                    duration = 30

                # Check if enough consecutive slots are available
                slots_needed = duration // 15
                can_schedule = True
                affected_slots = set()

                current_slot = time_slot
                for _ in range(slots_needed):
                    if (current_slot not in staff_availability[staff_id] or
                            current_slot.hour >= 17):
                        can_schedule = False
                        break
                    affected_slots.add(current_slot)
                    current_slot += timedelta(minutes=15)

                if can_schedule:
                    # Create appointment
                    schedule[time_slot] = TimeSlot(
                        time_slot,
                        time_slot + timedelta(minutes=duration),
                        visit_type,
                        staff_id,
                        species
                    )

                    # Update staff availability
                    staff_availability[staff_id] -= affected_slots
                    appointments_created += 1

        # Add random 15-minute breaks
        for staff_id, availability in staff_availability.items():
            if len(availability) > 2:  # Only add breaks if there's room
                break_slots = random.sample(list(availability), 2)
                for slot in break_slots:
                    schedule[slot] = TimeSlot(
                        slot,
                        slot + timedelta(minutes=15),
                        VisitType.CONSULT,  # Use as placeholder for break
                        staff_id,
                        "break"
                    )

        return schedule


def test_data_generation():
    """Test the data generation with sample output"""
    generator = VetClinicDataGenerator()

    # Generate staff roster
    staff_roster = generator.generate_staff_roster()

    # Generate schedule
    schedule = generator.generate_realistic_schedule(staff_roster)

    # Print summary statistics
    total_appointments = len(schedule)
    appointment_types = {}
    species_counts = {}
    staff_workload = {}

    for slot in schedule.values():
        if slot.species != "break":
            appointment_types[slot.visit_type] = appointment_types.get(slot.visit_type, 0) + 1
            species_counts[slot.species] = species_counts.get(slot.species, 0) + 1
            staff_workload[slot.staff_id] = staff_workload.get(slot.staff_id, 0) + 1

    summary = {
        'total_staff': len(staff_roster),
        'total_appointments': total_appointments,
        'appointment_types': appointment_types,
        'species_distribution': species_counts,
        'staff_workload': staff_workload
    }

    # Generate Expiring inventory
    expiring_inventory = {
        VisitType.VACCINATION: 0.8,
        VisitType.SURGERY: 0.3,
        VisitType.DENTAL: 0.5
    }

    return staff_roster, schedule, expiring_inventory, summary

