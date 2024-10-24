from datetime import datetime

from appt_types import AppointmentType


class PricingCalculator:
    def __init__(self):
        # Base rates per appointment type (30-minute base)
        self.BASE_RATES = {
            AppointmentType.CHECKUP: 75.00,
            AppointmentType.VACCINATION: 65.00,
            AppointmentType.SURGERY: 250.00,
            AppointmentType.EMERGENCY: 150.00,
            AppointmentType.GROOMING: 55.00,
            AppointmentType.DENTAL: 120.00
        }

        # Duration multipliers
        self.DURATION_MULTIPLIERS = {
            30: 1.0,  # Base price for 30 minutes
            45: 1.4,  # 40% increase for 45 minutes
            60: 1.8  # 80% increase for 60 minutes
        }

        # Pet type multipliers
        self.PET_TYPE_MULTIPLIERS = {
            "Dog": 1.0,
            "Cat": 1.0,
            "Bird": 1.2,
            "Rabbit": 1.1,
            "Hamster": 0.9
        }

        # Time of day multipliers
        self.TIME_OF_DAY_MULTIPLIERS = {
            "early_morning": 0.9,  # Before 10 AM
            "peak_hours": 1.2,  # 10 AM - 2 PM
            "afternoon": 1.0,  # 2 PM - 4 PM
            "evening": 0.95  # After 4 PM
        }

    def calculate_price(self, appointment_type: AppointmentType,
                        duration: int, pet_type: str,
                        start_time: datetime,
                        is_emergency: bool = False,
                        is_repeat_customer: bool = False) -> dict:
        # Get base price
        base_price = self.BASE_RATES[appointment_type]

        # Apply duration multiplier
        duration_multiplier = self.DURATION_MULTIPLIERS.get(duration, 1.0)
        price = base_price * duration_multiplier

        # Apply pet type multiplier
        pet_multiplier = self.PET_TYPE_MULTIPLIERS.get(pet_type, 1.0)
        price *= pet_multiplier

        # Apply time of day multiplier
        hour = start_time.hour
        if hour < 10:
            time_multiplier = self.TIME_OF_DAY_MULTIPLIERS["early_morning"]
        elif 10 <= hour < 14:
            time_multiplier = self.TIME_OF_DAY_MULTIPLIERS["peak_hours"]
        elif 14 <= hour < 16:
            time_multiplier = self.TIME_OF_DAY_MULTIPLIERS["afternoon"]
        else:
            time_multiplier = self.TIME_OF_DAY_MULTIPLIERS["evening"]

        price *= time_multiplier

        # Apply emergency multiplier if applicable
        if is_emergency:
            price *= 1.5

        # Apply repeat customer discount if applicable
        if is_repeat_customer:
            price *= 0.9  # 10% discount

        # Calculate breakdown
        breakdown = {
            "base_price": base_price,
            "duration_adjustment": f"{(duration_multiplier - 1) * 100:+.0f}%",
            "pet_type_adjustment": f"{(pet_multiplier - 1) * 100:+.0f}%",
            "time_of_day_adjustment": f"{(time_multiplier - 1) * 100:+.0f}%",
            "emergency_fee": "Yes" if is_emergency else "No",
            "repeat_customer_discount": "Yes" if is_repeat_customer else "No",
            "final_price": round(price, 2)
        }

        return breakdown

