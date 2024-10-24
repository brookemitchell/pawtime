from enum import Enum


class AppointmentType(Enum):
    CHECKUP = "Checkup"
    VACCINATION = "Vaccination"
    SURGERY = "Surgery"
    EMERGENCY = "Emergency"
    GROOMING = "Grooming"
    DENTAL = "Dental"
