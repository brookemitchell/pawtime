from dataclasses import dataclass
from typing import Dict, List, Set, Tuple
from datetime import datetime

@dataclass
class Appointment:
    time: int
    vet: str
    tech: str
    service: str
    price: float = 0.0

class ScheduleManager:
    def __init__(self):
        self.vets = {'sri', 'saurabh', 'krishan'}
        self.techs = {'brooke', 'dave', 'duncan'}
        self.base_prices = {
            'consultation': 50,
            'surgery': 200
        }
        self.slots = range(9, 17)  # 9 AM to 4 PM
        self.demand = {
            9: 5, 10: 10, 11: 7, 12: 8,
            13: 12, 14: 1, 15: 6, 16: 3
        }
        self.scheduled: List[Appointment] = []
        
    def calculate_price(self, service: str, time: int) -> float:
        """Calculate price based on service type and demand."""
        base_price = self.base_prices[service]
        demand_count = self.demand[time]
        
        if demand_count < 5:
            return base_price
        elif demand_count < 10:
            return base_price * 1.2
        elif demand_count < 15:
            return base_price * 1.5
        return base_price * 2.0

    def is_available(self, vet: str, tech: str, time: int) -> bool:
        """Check if both vet and tech are available at given time."""
        for appointment in self.scheduled:
            if time == appointment.time:
                if vet == appointment.vet or tech == appointment.tech:
                    return False
        return True

    def schedule_appointment(self, time: int, vet: str, tech: str, service: str) -> bool:
        """Schedule an appointment if resources are available."""
        if (vet in self.vets and 
            tech in self.techs and 
            time in self.slots and 
            self.is_available(vet, tech, time)):
            
            price = self.calculate_price(service, time)
            appointment = Appointment(time, vet, tech, service, price)
            self.scheduled.append(appointment)
            print(f"Scheduled appointment at {time}:00 with {vet} and {tech} for {service}.")
            return True
        return False

    def clear_schedules(self):
        """Clear all scheduled appointments."""
        self.scheduled.clear()

    def schedule_all(self):
        """Schedule all possible appointments."""
        # Schedule consultations
        for time in self.slots:
            for vet in self.vets:
                for tech in self.techs:
                    self.schedule_appointment(time, vet, tech, 'consultation')

        # After consultations, try to schedule any possible surgeries
        for time in self.slots:
            for vet in self.vets:
                for tech in self.techs:
                    self.schedule_appointment(time, vet, tech, 'surgery')

    def print_schedule_with_prices(self):
        """Print all scheduled appointments with their prices."""
        for appointment in self.scheduled:
            print(f"Price for appointment at {appointment.time}:00 with {appointment.vet} "
                  f"for {appointment.service}: ${appointment.price:.2f}")

def main():
    scheduler = ScheduleManager()
    scheduler.clear_schedules()
    scheduler.schedule_all()
    scheduler.print_schedule_with_prices()

if __name__ == "__main__":
    main()