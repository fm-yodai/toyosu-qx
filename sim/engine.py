"""
SimPy-based discrete event simulation engine.

Manages the event loop, tare resources, and coordinates the simulation
of loading, traveling, unloading, and trade confirmation events.
"""

from typing import Any

import simpy

from .models import EventType, Grid, Node, Order, SimEvent, Tare, TareState


class SimulationEngine:
    """
    Core simulation engine using SimPy.

    Manages discrete events at 1-second granularity for tare operations.
    Uses a 2D grid space where movement is restricted to corridors
    (horizontal and vertical only - Manhattan distance).
    """

    def __init__(
        self,
        run_id: str,
        config: dict[str, Any],
        nodes: dict[str, Node],
        tares: dict[str, Tare],
        grid: Grid | None = None,
    ):
        """
        Initialize simulation engine.

        Args:
            run_id: Unique identifier for this simulation run
            config: Configuration parameters (speed, alpha_load, etc.)
            nodes: Dictionary of Node objects by ID
            tares: Dictionary of Tare objects by ID
            grid: 2D grid space (optional, created from config if not provided)
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

        # Initialize grid (default: 30x30 grid, 10m per cell)
        if grid is not None:
            self.grid = grid
        else:
            grid_config = config.get("grid", {})
            self.grid = Grid(
                width=grid_config.get("width", 30),
                height=grid_config.get("height", 30),
                cell_size_m=grid_config.get("cell_size_m", 10.0),
            )

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
        Calculate Manhattan distance between two nodes.

        In a grid with corridors, tares can only move horizontally
        or vertically, so the distance is |x1-x2| + |y1-y2| cells
        multiplied by the cell size in meters.

        Args:
            node_a_id: First node ID
            node_b_id: Second node ID

        Returns:
            Distance in meters
        """
        node_a = self.nodes[node_a_id]
        node_b = self.nodes[node_b_id]
        return self.grid.distance_meters(node_a.x, node_a.y, node_b.x, node_b.y)

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

    def calculate_position_at_time(
        self,
        origin_id: str,
        dest_id: str,
        elapsed_sec: float,
        total_travel_sec: float,
    ) -> tuple[float, float]:
        """
        Calculate position along Manhattan path at a given time.

        Movement follows Manhattan distance: first X-axis, then Y-axis.

        Args:
            origin_id: Origin node ID
            dest_id: Destination node ID
            elapsed_sec: Time elapsed since departure
            total_travel_sec: Total travel time

        Returns:
            (x, y) position as floats (can be fractional during movement)
        """
        origin = self.nodes[origin_id]
        dest = self.nodes[dest_id]

        # Calculate progress (0.0 to 1.0)
        progress = min(elapsed_sec / total_travel_sec, 1.0) if total_travel_sec > 0 else 1.0

        # Manhattan path: first X, then Y
        dx = dest.x - origin.x
        dy = dest.y - origin.y
        total_dist = abs(dx) + abs(dy)

        if total_dist == 0:
            return float(origin.x), float(origin.y)

        # Distance traveled so far
        dist_traveled = progress * total_dist

        # First move in X direction
        x_dist = abs(dx)
        if dist_traveled <= x_dist:
            # Still moving in X direction
            x_progress = dist_traveled / x_dist if x_dist > 0 else 1.0
            new_x = origin.x + (dx * x_progress) if dx != 0 else origin.x
            new_y = float(origin.y)
        else:
            # X complete, now moving in Y direction
            new_x = float(dest.x)
            y_dist = abs(dy)
            y_traveled = dist_traveled - x_dist
            y_progress = y_traveled / y_dist if y_dist > 0 else 1.0
            new_y = origin.y + (dy * y_progress) if dy != 0 else origin.y

        return new_x, new_y

    def travel_with_position_logging(
        self,
        tare: Tare,
        origin_id: str,
        dest_id: str,
        load_kg: float,
    ) -> Any:
        """
        SimPy process for traveling with position logged every second.

        Args:
            tare: Tare truck
            origin_id: Origin node ID
            dest_id: Destination node ID
            load_kg: Current load weight

        Yields:
            SimPy events
        """
        dist = self.distance(origin_id, dest_id)
        total_travel_sec = self.travel_time(dist)

        # Log position every second during travel
        elapsed = 0.0
        while elapsed < total_travel_sec:
            # Calculate current position
            x, y = self.calculate_position_at_time(origin_id, dest_id, elapsed, total_travel_sec)

            self.log_event(
                EventType.POSITION_UPDATE,
                tare_id=tare.id,
                state=tare.state,
                load_kg=load_kg,
                payload={
                    "x": round(x, 2),
                    "y": round(y, 2),
                    "origin": origin_id,
                    "destination": dest_id,
                    "progress": round(elapsed / total_travel_sec, 3) if total_travel_sec > 0 else 1.0,
                },
            )

            # Wait 1 second (or remaining time if less than 1 second)
            wait_time = min(1.0, total_travel_sec - elapsed)
            yield self.env.timeout(wait_time)
            elapsed += wait_time

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

        # Travel with position logging every second
        yield from self.travel_with_position_logging(tare, origin, destination, total_weight)

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

        # Travel with position logging every second
        yield from self.travel_with_position_logging(tare, destination, tare.home, 0.0)

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
