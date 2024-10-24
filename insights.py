from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Tuple

import streamlit as st

from schedule import TimeSlot


class ScheduleInsights:
    def __init__(
            self,
            schedule: Dict[datetime, 'TimeSlot'],
            staff_roster: Dict[str, 'Staff'],
            potential_slots: List[datetime]
    ):
        self.schedule = schedule
        self.staff_roster = staff_roster
        self.potential_slots = potential_slots

    def analyze_schedule(self) -> Dict[str, List[Tuple[str, str]]]:
        """Analyze schedule and return insights with suggestions"""
        insights = {
            "efficiency": [],
            "workload": [],
            "optimization": [],
            "risk": []
        }

        # Efficiency Insights
        self._analyze_time_distribution(insights)
        self._analyze_appointment_clustering(insights)
        self._analyze_break_distribution(insights)

        # Workload Insights
        self._analyze_staff_workload(insights)
        self._analyze_specialization_distribution(insights)  # Added back

        # Optimization Opportunities
        self._analyze_peak_hours(insights)
        self._analyze_appointment_duration(insights)

        # Risk Analysis
        self._analyze_schedule_risks(insights)

        return insights

    def _analyze_peak_hours(self, insights: Dict):
        """Analyze peak hours and suggest optimizations"""
        hourly_count = defaultdict(int)
        for time in self.schedule:
            hourly_count[time.hour] += 1

        # Find peak hours
        peak_hours = []
        for hour, count in hourly_count.items():
            if count >= len(self.staff_roster) * 0.8:  # 80% capacity
                peak_hours.append(hour)

        if peak_hours:
            insights["optimization"].append((
                "Peak Hours Identified",
                f"Consider adding support staff during {', '.join(f'{h:02d}:00' for h in peak_hours)}"
            ))

    def _analyze_appointment_duration(self, insights: Dict):
        """Analyze appointment durations and suggest optimizations"""
        durations = []
        for slot in self.schedule.values():
            duration = (slot.end_time - slot.start_time).total_seconds() / 60
            durations.append(duration)

        if durations:
            avg_duration = sum(durations) / len(durations)
            if avg_duration > 45:
                insights["optimization"].append((
                    "Long Appointments",
                    "Consider splitting complex appointments across multiple shorter sessions"
                ))

    def _analyze_schedule_risks(self, insights: Dict):
        """Analyze potential schedule risks"""
        # Check for back-to-back complex appointments
        complex_appointments = 0
        for slot in self.schedule.values():
            duration = (slot.end_time - slot.start_time).total_seconds() / 60
            if duration >= 45:
                complex_appointments += 1

        if complex_appointments > len(self.staff_roster) * 2:
            insights["risk"].append((
                "High Complex Appointment Load",
                "Multiple long appointments may increase risk of delays"
            ))

    def _analyze_time_distribution(self, insights: Dict):
        """Analyze distribution of appointments throughout the day"""
        hourly_count = defaultdict(int)
        for time in self.schedule:
            hourly_count[time.hour] += 1

        # Check for uneven distribution
        max_hour = max(hourly_count.values(), default=0)
        min_hour = min(hourly_count.values(), default=0)
        if max_hour - min_hour > 3:
            insights["efficiency"].append((
                "Uneven Time Distribution",
                "Consider redistributing appointments to balance the daily schedule"
            ))

        # Check for underutilized periods
        for hour in range(9, 17):
            if hourly_count[hour] < len(self.staff_roster) * 0.5:
                insights["optimization"].append((
                    f"Underutilized Period: {hour}:00",
                    f"Consider booking more appointments during {hour}:00-{hour + 1}:00"
                ))

    def _analyze_appointment_clustering(self, insights: Dict):
        """Analyze clustering of similar appointments"""
        visit_sequences = []
        current_sequence = []

        for time, slot in sorted(self.schedule.items()):
            if not current_sequence:
                current_sequence = [slot]
            else:
                if (time - current_sequence[-1].end_time).total_seconds() <= 900:  # 15 minutes
                    current_sequence.append(slot)
                else:
                    visit_sequences.append(current_sequence)
                    current_sequence = [slot]

        if current_sequence:
            visit_sequences.append(current_sequence)

        # Analyze sequences for optimization opportunities
        for sequence in visit_sequences:
            if len(sequence) >= 3:
                visit_types = [slot.visit_type for slot in sequence]
                if len(set(visit_types)) == len(visit_types):
                    insights["optimization"].append((
                        "Appointment Clustering Opportunity",
                        "Consider grouping similar appointment types together for efficiency"
                    ))

    def _analyze_break_distribution(self, insights: Dict):
        """Analyze distribution of breaks and gaps"""
        staff_breaks = defaultdict(list)

        for time, slot in sorted(self.schedule.items()):
            if slot.species == "break":
                staff_breaks[slot.staff_id].append(time)

        for staff_id, breaks in staff_breaks.items():
            if len(breaks) < 2:
                insights["risk"].append((
                    f"Insufficient Breaks: {staff_id}",
                    "Schedule additional short breaks to prevent fatigue"
                ))

            # Check break spacing
            if len(breaks) >= 2:
                break_gaps = [(breaks[i + 1] - breaks[i]).total_seconds() / 3600
                              for i in range(len(breaks) - 1)]
                if max(break_gaps) > 4:
                    insights["workload"].append((
                        f"Break Distribution: {staff_id}",
                        "Consider redistributing breaks more evenly throughout the day"
                    ))

    def _analyze_staff_workload(self, insights: Dict):
        """Analyze workload distribution among staff"""
        staff_appointments = defaultdict(int)
        staff_duration = defaultdict(int)

        for slot in self.schedule.values():
            staff_appointments[slot.staff_id] += 1
            duration = (slot.end_time - slot.start_time).total_seconds() / 60
            staff_duration[slot.staff_id] += duration

        # Check workload balance
        max_appointments = max(staff_appointments.values())
        min_appointments = min(staff_appointments.values())
        if max_appointments - min_appointments > 3:
            insights["workload"].append((
                "Uneven Workload Distribution",
                "Consider redistributing appointments among available staff"
            ))

        # Check individual workload
        for staff_id, duration in staff_duration.items():
            if duration > 420:  # 7 hours
                insights["risk"].append((
                    f"Heavy Workload: {staff_id}",
                    "Consider reducing appointment load or adding breaks"
                ))

    def display_insights(self):
        """Display insights in an organized and visually appealing way"""
        st.header("🔍 Schedule Insights & Suggestions")

        insights = self.analyze_schedule()

        # Display efficiency insights
        with st.expander("⚡ Efficiency Insights", expanded=True):
            for title, suggestion in insights["efficiency"]:
                st.markdown(f"**{title}**")
                st.info(suggestion)

        # Display workload insights
        with st.expander("👥 Workload Analysis", expanded=True):
            for title, suggestion in insights["workload"]:
                st.markdown(f"**{title}**")
                st.info(suggestion)

        # Display optimization opportunities
        with st.expander("📈 Optimization Opportunities", expanded=True):
            for title, suggestion in insights["optimization"]:
                st.markdown(f"**{title}**")
                st.success(suggestion)

        # Display risk analysis
        with st.expander("⚠️ Risk Analysis", expanded=True):
            for title, suggestion in insights["risk"]:
                st.markdown(f"**{title}**")
                st.warning(suggestion)

        # Display summary metrics
        st.subheader("📊 Schedule Health Score")
        self._display_health_metrics()

    def _display_health_metrics(self):
        """Display schedule health metrics"""
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            efficiency_score = self._calculate_efficiency_score()
            st.metric(
                "Efficiency",
                f"{efficiency_score}%",
                help="Based on time distribution and appointment clustering"
            )

        with col2:
            workload_score = self._calculate_workload_score()
            st.metric(
                "Workload Balance",
                f"{workload_score}%",
                help="Based on staff utilization and break distribution"
            )

        with col3:
            optimization_score = self._calculate_optimization_score()
            st.metric(
                "Optimization",
                f"{optimization_score}%",
                help="Based on resource utilization and scheduling patterns"
            )

        with col4:
            risk_score = self._calculate_risk_score()
            st.metric(
                "Risk Level",
                f"{risk_score}%",
                help="Based on identified scheduling risks and conflicts"
            )

    def _calculate_efficiency_score(self) -> int:
        """Calculate schedule efficiency score"""
        score = 100
        hourly_count = defaultdict(int)

        for time in self.schedule:
            hourly_count[time.hour] += 1

        # Penalize for uneven distribution
        max_hour = max(hourly_count.values(), default=0)
        min_hour = min(hourly_count.values(), default=0)
        score -= (max_hour - min_hour) * 5

        return max(0, min(100, score))

    def _calculate_workload_score(self) -> int:
        """Calculate workload balance score"""
        score = 100
        staff_appointments = defaultdict(int)

        for slot in self.schedule.values():
            staff_appointments[slot.staff_id] += 1

        if staff_appointments:
            max_appointments = max(staff_appointments.values())
            min_appointments = min(staff_appointments.values())
            score -= (max_appointments - min_appointments) * 10

        return max(0, min(100, score))

    def _calculate_optimization_score(self) -> int:
        """Calculate schedule optimization score"""
        score = 100
        total_slots = len(self.potential_slots)
        used_slots = len(self.schedule)

        if total_slots > 0:
            utilization = (used_slots / total_slots) * 100
            if utilization < 70:
                score -= (70 - utilization)
            elif utilization > 90:
                score -= (utilization - 90)

        return max(0, min(100, score))

    def _calculate_risk_score(self) -> int:
        """Calculate schedule risk score"""
        score = 100
        staff_duration = defaultdict(int)

        for slot in self.schedule.values():
            duration = (slot.end_time - slot.start_time).total_seconds() / 60
            staff_duration[slot.staff_id] += duration

        for duration in staff_duration.values():
            if duration > 420:  # 7 hours
                score -= 20
            elif duration > 360:  # 6 hours
                score -= 10

        return max(0, min(100, score))


# Usage in the main application:
"""
# After getting the schedule and potential slots
insights = ScheduleInsights(schedule, staff_roster, potential_slots)
insights.display_insights()
"""