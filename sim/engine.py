"""
SimPy-based discrete event simulation engine.

Manages the event loop, tare resources, and coordinates the simulation
of loading, traveling, unloading, and trade confirmation events.
"""

import math
from typing import Any

import simpy

from .models import EventType, Node, Order, SimEvent, Tare, TareState


class SimulationEngine:
    """
    Core simulation engine using SimPy.

    Manages discrete events at 1-second granularity for tare operations.
    """

    def __init__(
        self,
        run_id: str,
        config: dict[str, Any],
        nodes: dict[str, Node],
        tares: dict[str, Tare],
    ):
        """
        Initialize simulation engine.

        Args:
            run_id: Unique identifier for this simulation run
            config: Configuration parameters (speed, alpha_load, etc.)
            nodes: Dictionary of Node objects by ID
            tares: Dictionary of Tare objects by ID
        """
        self.run_id = run_id
        self.config = config
        self.nodes = nodes
        self.tares = tares
        self.env = simpy.Environment()
        self.events: list[SimEvent] = []

        # Extract config parameters
        self.speed_kmph = config.get("speed_kmph", 8.0)
        self.alpha_load = config.get("alpha_load", 0.3)  # s/kg
        self.beta_load = config.get("beta_load", 10.0)  # s
        self.trade_proc_sec = config.get("trade_proc_sec", 30)

    def log_event(
        self,
        event: EventType,
        tare_id: str | None = None,
        node: str | None = None,
        state: TareState | None = None,
        load_kg: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        """Log a simulation event."""
        sim_event = SimEvent(
            ts=self.env.now,
            run_id=self.run_id,
            event=event,
            tare_id=tare_id,
            node=node,
            state=state,
            load_kg=load_kg,
            payload=payload,
        )
        self.events.append(sim_event)

    def distance(self, node_a_id: str, node_b_id: str) -> float:
        """
        Calculate Euclidean distance between two nodes.

        Args:
            node_a_id: First node ID
            node_b_id: Second node ID

        Returns:
            Distance in meters
        """
        node_a = self.nodes[node_a_id]
        node_b = self.nodes[node_b_id]
        dx = node_a.x - node_b.x
        dy = node_a.y - node_b.y
        return math.sqrt(dx * dx + dy * dy)

    def travel_time(self, distance_m: float) -> float:
        """
        Calculate travel time for a given distance.

        Args:
            distance_m: Distance in meters

        Returns:
            Travel time in seconds
        """
        distance_km = distance_m / 1000.0
        time_hours = distance_km / self.speed_kmph
        return time_hours * 3600.0  # Convert to seconds

    def loading_time(self, weight_kg: float) -> float:
        """
        Calculate loading time based on weight.

        Uses linear model: t = α * W + β

        Args:
            weight_kg: Weight to load in kg

        Returns:
            Loading time in seconds
        """
        return self.alpha_load * weight_kg + self.beta_load

    def tare_process(self, tare: Tare, orders: list[Order], destination: str) -> Any:
        """
        SimPy process for a tare delivery trip.

        Sequence:
        1. LOADING: Load orders at wholesaler
        2. TRAVELING: Travel to destination
        3. UNLOADING: Unload at retailer
        4. TRADE_PROC: Process trade confirmation
        5. TRAVELING: Return to wholesaler
        6. Back to IDLE

        Args:
            tare: Tare truck object
            orders: List of orders to deliver
            destination: Destination node ID

        Yields:
            SimPy events
        """
        # Phase 1: Loading
        total_weight = sum(order.weight_kg for order in orders)
        load_time = self.loading_time(total_weight)

        tare.state = TareState.LOADING
        tare.last_state_change = self.env.now
        self.log_event(
            EventType.LOAD_START,
            tare_id=tare.id,
            node=tare.current_node,
            state=tare.state,
            load_kg=total_weight,
            payload={"order_ids": [o.id for o in orders]},
        )

        yield self.env.timeout(load_time)

        tare.current_load_kg = total_weight
        tare.orders = [o.id for o in orders]
        self.log_event(
            EventType.LOAD_END,
            tare_id=tare.id,
            node=tare.current_node,
            state=tare.state,
            load_kg=total_weight,
        )

        # Phase 2: Travel to destination
        origin = tare.current_node
        dist = self.distance(origin, destination)
        travel_duration = self.travel_time(dist)

        tare.state = TareState.TRAVELING
        tare.last_state_change = self.env.now
        tare.total_distance_m += dist
        self.log_event(
            EventType.DEPART,
            tare_id=tare.id,
            node=origin,
            state=tare.state,
            load_kg=total_weight,
            payload={"destination": destination, "distance_m": dist},
        )

        yield self.env.timeout(travel_duration)

        tare.current_node = destination
        self.log_event(
            EventType.ARRIVE,
            tare_id=tare.id,
            node=destination,
            state=tare.state,
            load_kg=total_weight,
        )

        # Phase 3: Unloading
        unload_time = self.loading_time(total_weight)  # Same formula
        tare.state = TareState.UNLOADING
        tare.last_state_change = self.env.now
        self.log_event(
            EventType.UNLOAD_START,
            tare_id=tare.id,
            node=destination,
            state=tare.state,
            load_kg=total_weight,
        )

        yield self.env.timeout(unload_time)

        self.log_event(
            EventType.UNLOAD_END,
            tare_id=tare.id,
            node=destination,
            state=tare.state,
            load_kg=0.0,
        )

        # Mark orders as delivered
        for order in orders:
            order.delivered_at = self.env.now
            self.log_event(
                EventType.ORDER_DELIVERED,
                tare_id=tare.id,
                node=destination,
                payload={"order_id": order.id},
            )

        tare.current_load_kg = 0.0
        tare.orders = []

        # Phase 4: Trade confirmation
        tare.state = TareState.TRADE_PROC
        tare.last_state_change = self.env.now
        yield self.env.timeout(self.trade_proc_sec)

        self.log_event(
            EventType.TRADE_CONFIRM,
            tare_id=tare.id,
            node=destination,
            state=tare.state,
        )

        # Phase 5: Return to wholesaler
        return_dist = self.distance(destination, tare.home)
        return_travel = self.travel_time(return_dist)

        tare.state = TareState.TRAVELING
        tare.last_state_change = self.env.now
        tare.total_distance_m += return_dist
        self.log_event(
            EventType.DEPART,
            tare_id=tare.id,
            node=destination,
            state=tare.state,
            load_kg=0.0,
            payload={"destination": tare.home, "distance_m": return_dist},
        )

        yield self.env.timeout(return_travel)

        tare.current_node = tare.home
        tare.state = TareState.IDLE
        tare.last_state_change = self.env.now
        self.log_event(
            EventType.ARRIVE,
            tare_id=tare.id,
            node=tare.home,
            state=tare.state,
            load_kg=0.0,
        )

    def run(self, until: float) -> None:
        """
        Run the simulation until a given time.

        Args:
            until: Simulation end time in seconds
        """
        self.env.run(until=until)

    def get_events(self) -> list[SimEvent]:
        """Get all logged events."""
        return self.events
