"""
KPI aggregation and calculation.

Computes key performance indicators from simulation events:
- Utilization rate
- Operating hours
- Travel distance
- Average load per trip
- Lead time distribution
- Fulfillment rate
- Split delivery rate
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .models import EventType, Order, SimEvent, Tare, TareState


@dataclass
class KPIMetric:
    """A single KPI metric value."""

    run_id: str
    metric: str
    value: float
    window: str | None = None
    ts: float | None = None


class KPIAggregator:
    """
    Aggregates KPIs from simulation events.

    Computes metrics for tares, orders, and overall system performance.
    """

    def __init__(self, run_id: str, config: dict[str, Any]):
        """
        Initialize KPI aggregator.

        Args:
            run_id: Unique run identifier
            config: Configuration parameters
        """
        self.run_id = run_id
        self.config = config
        self.metrics: list[KPIMetric] = []

    def compute_kpis(
        self,
        events: list[SimEvent],
        tares: dict[str, Tare],
        orders: dict[str, Order],
    ) -> list[KPIMetric]:
        """
        Compute all KPIs from events.

        Args:
            events: List of simulation events
            tares: Dictionary of tares by ID
            orders: Dictionary of orders by ID

        Returns:
            List of KPI metrics
        """
        self.metrics = []

        # Tare-level KPIs
        self._compute_tare_kpis(events, tares)

        # Order-level KPIs
        self._compute_order_kpis(orders)

        # System-level KPIs
        self._compute_system_kpis(events, tares, orders)

        return self.metrics

    def _compute_tare_kpis(
        self, events: list[SimEvent], tares: dict[str, Tare]
    ) -> None:
        """Compute tare-level KPIs."""
        # Get simulation duration
        if not events:
            return

        sim_duration = max(e.ts for e in events)

        for tare in tares.values():
            # Utilization rate: time not idle / total time
            idle_time = self._compute_idle_time(events, tare.id, sim_duration)
            utilization = 1.0 - (idle_time / sim_duration) if sim_duration > 0 else 0.0

            self.metrics.append(
                KPIMetric(
                    run_id=self.run_id,
                    metric=f"tare_{tare.id}_utilization",
                    value=utilization,
                )
            )

            # Total distance
            self.metrics.append(
                KPIMetric(
                    run_id=self.run_id,
                    metric=f"tare_{tare.id}_distance_m",
                    value=tare.total_distance_m,
                )
            )

            # Number of trips
            trips = self._count_trips(events, tare.id)
            self.metrics.append(
                KPIMetric(
                    run_id=self.run_id,
                    metric=f"tare_{tare.id}_trips",
                    value=float(trips),
                )
            )

            # Average load per trip
            if trips > 0:
                avg_load = self._compute_avg_load(events, tare.id, trips)
                self.metrics.append(
                    KPIMetric(
                        run_id=self.run_id,
                        metric=f"tare_{tare.id}_avg_load_kg",
                        value=avg_load,
                    )
                )

    def _compute_order_kpis(self, orders: dict[str, Order]) -> None:
        """Compute order-level KPIs."""
        delivered_orders = [o for o in orders.values() if o.delivered_at is not None]

        if not delivered_orders:
            return

        # Lead times
        lead_times = [
            o.delivered_at - o.created_at for o in delivered_orders
        ]

        # Mean lead time
        mean_lt = sum(lead_times) / len(lead_times)
        self.metrics.append(
            KPIMetric(
                run_id=self.run_id,
                metric="lead_time_mean_sec",
                value=mean_lt,
            )
        )

        # 95th percentile lead time
        lead_times_sorted = sorted(lead_times)
        p95_index = int(len(lead_times_sorted) * 0.95)
        p95_lt = lead_times_sorted[p95_index] if p95_index < len(lead_times_sorted) else lead_times_sorted[-1]
        self.metrics.append(
            KPIMetric(
                run_id=self.run_id,
                metric="lead_time_p95_sec",
                value=p95_lt,
            )
        )

        # Fulfillment rate
        total_orders = len(orders)
        fulfillment_rate = len(delivered_orders) / total_orders if total_orders > 0 else 0.0
        self.metrics.append(
            KPIMetric(
                run_id=self.run_id,
                metric="fulfillment_rate",
                value=fulfillment_rate,
            )
        )

    def _compute_system_kpis(
        self,
        events: list[SimEvent],
        tares: dict[str, Tare],
        orders: dict[str, Order],
    ) -> None:
        """Compute system-level KPIs."""
        # Total distance traveled
        total_distance = sum(t.total_distance_m for t in tares.values())
        self.metrics.append(
            KPIMetric(
                run_id=self.run_id,
                metric="system_total_distance_m",
                value=total_distance,
            )
        )

        # Total trips
        total_trips = sum(self._count_trips(events, t.id) for t in tares.values())
        self.metrics.append(
            KPIMetric(
                run_id=self.run_id,
                metric="system_total_trips",
                value=float(total_trips),
            )
        )

        # Average system utilization
        sim_duration = max(e.ts for e in events) if events else 0.0
        if sim_duration > 0 and tares:
            avg_util = sum(
                1.0 - (self._compute_idle_time(events, t.id, sim_duration) / sim_duration)
                for t in tares.values()
            ) / len(tares)
            self.metrics.append(
                KPIMetric(
                    run_id=self.run_id,
                    metric="system_avg_utilization",
                    value=avg_util,
                )
            )

    def _compute_idle_time(self, events: list[SimEvent], tare_id: str, sim_end: float) -> float:
        """Compute total idle time for a tare."""
        tare_events = [e for e in events if e.tare_id == tare_id]
        tare_events.sort(key=lambda e: e.ts)

        idle_time = 0.0
        last_idle_start = None

        for event in tare_events:
            if event.state == TareState.IDLE:
                if last_idle_start is None:
                    last_idle_start = event.ts
            else:
                if last_idle_start is not None:
                    idle_time += event.ts - last_idle_start
                    last_idle_start = None

        # If still idle at end
        if last_idle_start is not None:
            final_ts = sim_end if sim_end >= 0 else (tare_events[-1].ts if tare_events else 0.0)
            idle_time += max(0.0, final_ts - last_idle_start)

        return idle_time

    def _count_trips(self, events: list[SimEvent], tare_id: str) -> int:
        """Count number of trips for a tare."""
        # Count DEPART events to retailer (not return trips)
        depart_events = [
            e
            for e in events
            if e.tare_id == tare_id
            and e.event == EventType.DEPART
            and e.payload
            and e.payload.get("destination")
            and e.load_kg
            and e.load_kg > 0
        ]
        return len(depart_events)

    def _compute_avg_load(self, events: list[SimEvent], tare_id: str, trips: int) -> float:
        """Compute average load per trip for a tare."""
        # Sum load weights at DEPART events
        depart_events = [
            e
            for e in events
            if e.tare_id == tare_id
            and e.event == EventType.DEPART
            and e.load_kg
            and e.load_kg > 0
        ]

        total_load = sum(e.load_kg for e in depart_events)
        return total_load / trips if trips > 0 else 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Convert metrics to pandas DataFrame."""
        if not self.metrics:
            return pd.DataFrame()

        data = {
            "run_id": [m.run_id for m in self.metrics],
            "metric": [m.metric for m in self.metrics],
            "value": [m.value for m in self.metrics],
            "window": [m.window for m in self.metrics],
            "ts": [m.ts for m in self.metrics],
        }
        return pd.DataFrame(data)
