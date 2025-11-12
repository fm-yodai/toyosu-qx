"""
Demand generator for orders.

Generates orders based on time-of-day intensity curves with
configurable lot sizes (S/M/L: 10/30/50kg).
"""

import random
from typing import Any

from .models import Node, NodeType, Order


class DemandGenerator:
    """
    Generates delivery orders based on time-of-day patterns.

    Uses Poisson-like intensity curves to model realistic demand
    throughout the market operating hours.
    """

    def __init__(
        self,
        config: dict[str, Any],
        nodes: dict[str, Node],
        seed: int | None = None,
    ):
        """
        Initialize demand generator.

        Args:
            config: Scenario configuration with demand curves
            nodes: Dictionary of nodes by ID
            seed: Random seed for reproducibility
        """
        self.config = config
        self.nodes = nodes
        self.rng = random.Random(seed)

        # Extract demand configuration
        demand_config = config.get("demand", {})
        self.base_rate = demand_config.get("base_rate", 0.1)  # orders per second
        raw_intensity_curve = demand_config.get(
            "intensity_curve",
            {
                "04:00": 0.5,
                "06:00": 1.5,
                "08:00": 2.0,
                "10:00": 1.0,
                "12:00": 0.3,
            },
        )
        self.intensity_points = self._build_intensity_points(raw_intensity_curve)
        self.max_intensity = max(value for _, value in self.intensity_points)

        # Lot sizes and their probabilities
        self.lot_sizes = demand_config.get("lot_sizes", [10, 30, 50])
        self.lot_probabilities = demand_config.get(
            "lot_probabilities", [0.5, 0.3, 0.2]
        )  # S:M:L = 50:30:20

        # Get wholesaler and retailer nodes
        self.wholesalers = [
            node for node in nodes.values() if node.type == NodeType.WHOLESALER
        ]
        self.retailers = [
            node for node in nodes.values() if node.type == NodeType.RETAILER
        ]

        self.order_counter = 0

    def get_intensity(self, time_sec: float) -> float:
        """
        Get demand intensity at a given time.

        Args:
            time_sec: Simulation time in seconds

        Returns:
            Intensity multiplier (1.0 = base rate)
        """
        if not self.intensity_points:
            return 1.0

        if len(self.intensity_points) == 1:
            return self.intensity_points[0][1]

        clamped_time = max(time_sec, 0.0)
        if clamped_time <= self.intensity_points[0][0]:
            return self.intensity_points[0][1]

        for idx in range(len(self.intensity_points) - 1):
            start_time, start_value = self.intensity_points[idx]
            end_time, end_value = self.intensity_points[idx + 1]
            if clamped_time <= end_time:
                span = end_time - start_time
                if span <= 0:
                    return end_value
                ratio = (clamped_time - start_time) / span
                return start_value + ratio * (end_value - start_value)

        return self.intensity_points[-1][1]

    def generate_orders(
        self, start_time: float, end_time: float
    ) -> list[Order]:
        """
        Generate orders for a time window.

        Args:
            start_time: Start of time window (simulation seconds)
            end_time: End of time window (simulation seconds)

        Returns:
            List of generated orders
        """
        orders: list[Order] = []
        lambda_max = self.base_rate * self.max_intensity

        if (
            lambda_max <= 0
            or start_time >= end_time
            or not self.wholesalers
            or not self.retailers
        ):
            return orders

        current_time = start_time
        while True:
            inter_arrival = self.rng.expovariate(lambda_max)
            current_time += inter_arrival
            if current_time >= end_time:
                break

            instantaneous_rate = self.base_rate * self.get_intensity(current_time)
            if instantaneous_rate <= 0:
                continue

            acceptance = instantaneous_rate / lambda_max
            if self.rng.random() > acceptance:
                continue

            origin = self.rng.choice(self.wholesalers)
            destination = self.rng.choice(self.retailers)
            weight = self.rng.choices(
                self.lot_sizes, weights=self.lot_probabilities, k=1
            )[0]

            order = Order(
                id=f"order_{self.order_counter:06d}",
                origin=origin.id,
                destination=destination.id,
                weight_kg=float(weight),
                created_at=current_time,
            )
            orders.append(order)
            self.order_counter += 1

        return orders

    def generate_order_at(self, time_sec: float) -> Order | None:
        """
        Generate a single order at a specific time (event-driven).

        Args:
            time_sec: Simulation time in seconds

        Returns:
            Order or None if no order generated
        """
        intensity = self.get_intensity(time_sec)
        rate = self.base_rate * intensity

        # Probability of order in this second
        if self.rng.random() < rate:
            origin = self.rng.choice(self.wholesalers)
            destination = self.rng.choice(self.retailers)
            weight = self.rng.choices(
                self.lot_sizes, weights=self.lot_probabilities, k=1
            )[0]

            order = Order(
                id=f"order_{self.order_counter:06d}",
                origin=origin.id,
                destination=destination.id,
                weight_kg=float(weight),
                created_at=time_sec,
            )
            self.order_counter += 1
            return order

        return None

    def _build_intensity_points(
        self, curve: dict[str, float]
    ) -> list[tuple[float, float]]:
        """
        Convert HH:MM curve definition to simulation-relative seconds.
        """
        points: list[tuple[float, float]] = []
        for time_str, multiplier in curve.items():
            seconds = self._time_to_seconds(time_str)
            points.append((float(seconds), float(multiplier)))

        if not points:
            return [(0.0, 1.0)]

        points.sort(key=lambda item: item[0])
        base_time = points[0][0]
        normalized = [(sec - base_time, value) for sec, value in points]
        return normalized

    @staticmethod
    def _time_to_seconds(time_str: str) -> int:
        """Convert HH:MM string to seconds."""
        hour_str, minute_str = time_str.split(":")
        hour = int(hour_str)
        minute = int(minute_str)
        return hour * 3600 + minute * 60
