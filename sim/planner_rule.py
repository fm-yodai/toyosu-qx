"""
Rule-based planner for tare assignment.

Phase 1 implementation: Simple nearest-idle-truck assignment with
5-minute departure rule and same-destination consolidation.
"""

from typing import Any

from .models import Node, Order, Tare, TareState


class RuleBasedPlanner:
    """
    Simple rule-based planner for order assignment.

    Rules:
    1. Find idle tares at the order's origin wholesaler
    2. Assign to nearest available tare
    3. Consolidate orders to same destination
    4. Depart after min_stay_sec (5-minute rule) or when min_load_ratio reached
    """

    def __init__(
        self,
        config: dict[str, Any],
        nodes: dict[str, Node],
        tares: dict[str, Tare],
    ):
        """
        Initialize planner.

        Args:
            config: Configuration parameters
            nodes: Dictionary of nodes by ID
            tares: Dictionary of tares by ID
        """
        self.config = config
        self.nodes = nodes
        self.tares = tares

        # Extract departure trigger config
        depart_config = config.get("depart_trigger", {})
        self.min_stay_sec = depart_config.get("min_stay_sec", 300)  # 5 minutes
        self.min_load_ratio = depart_config.get("min_load_ratio", 0.5)

        # Consolidation policy
        self.consolidation = config.get("consolidation", "same_destination_only")

        # Pending order queue: origin -> destination -> list of orders
        self.pending_orders: dict[str, dict[str, list[Order]]] = {}

    def add_order(self, order: Order, current_time: float) -> None:
        """
        Add a new order to the pending queue.

        Args:
            order: Order to add
            current_time: Current simulation time
        """
        if order.origin not in self.pending_orders:
            self.pending_orders[order.origin] = {}
        if order.destination not in self.pending_orders[order.origin]:
            self.pending_orders[order.origin][order.destination] = []

        self.pending_orders[order.origin][order.destination].append(order)

    def get_idle_tares_at(self, node_id: str) -> list[Tare]:
        """
        Get all idle tares at a given node.

        Args:
            node_id: Node ID to search

        Returns:
            List of idle tares at the node
        """
        return [
            tare
            for tare in self.tares.values()
            if tare.state == TareState.IDLE
            and tare.current_node == node_id
        ]

    def assign_orders(self, current_time: float) -> list[tuple[Tare, list[Order], str]]:
        """
        Assign pending orders to tares based on rules.

        Returns:
            List of (tare, orders, destination) tuples ready to depart
        """
        assignments: list[tuple[Tare, list[Order], str]] = []

        for origin, destinations in list(self.pending_orders.items()):
            idle_tares = self.get_idle_tares_at(origin)

            if not idle_tares:
                continue

            for destination, orders in list(destinations.items()):
                if not orders:
                    continue

                # Find a tare for this destination
                tare = self._select_tare(idle_tares, orders)
                if tare is None:
                    continue

                # Consolidate orders for this destination up to capacity
                selected_orders = self._consolidate_orders(tare, orders, current_time)

                if not selected_orders:
                    continue

                if not self.should_depart(tare, selected_orders, current_time):
                    # Keep orders queued until departure rule satisfied
                    continue

                assignments.append((tare, selected_orders, destination))

                # Remove assigned orders from pending
                for order in selected_orders:
                    orders.remove(order)
                    order.assigned_at = current_time
                    order.tare_id = tare.id

                # Remove tare from idle list
                if tare in idle_tares:
                    idle_tares.remove(tare)

                # Clean up empty destination queues
                if not orders:
                    del destinations[destination]

            # Clean up empty origin queues
            if not destinations:
                del self.pending_orders[origin]

        return assignments

    def _select_tare(self, idle_tares: list[Tare], orders: list[Order]) -> Tare | None:
        """
        Select a tare for orders using simple FIFO strategy.

        Args:
            idle_tares: List of available idle tares
            orders: Orders to be assigned

        Returns:
            Selected tare or None if no suitable tare found
        """
        if not idle_tares:
            return None

        # Simple rule: first available idle tare
        # Future: could prioritize by last_state_change (longest idle)
        return idle_tares[0]

    def _consolidate_orders(
        self, tare: Tare, orders: list[Order], current_time: float
    ) -> list[Order]:
        """
        Consolidate orders for a tare up to capacity and departure rules.

        Args:
            tare: Tare to load
            orders: Available orders for the destination
            current_time: Current simulation time

        Returns:
            List of orders to load on the tare
        """
        selected: list[Order] = []
        total_weight = 0.0
        capacity = tare.capacity_kg

        # Sort orders by creation time (FIFO)
        sorted_orders = sorted(orders, key=lambda o: o.created_at)

        for order in sorted_orders:
            if total_weight + order.weight_kg <= capacity:
                selected.append(order)
                total_weight += order.weight_kg

                # Check if we should depart based on rules
                load_ratio = total_weight / capacity
                oldest_order_age = current_time - selected[0].created_at

                # Depart if min_stay_sec passed OR min_load_ratio reached
                if (
                    oldest_order_age >= self.min_stay_sec
                    or load_ratio >= self.min_load_ratio
                ):
                    break
            else:
                # Can't fit more orders
                break

        return selected

    def should_depart(
        self, tare: Tare, orders: list[Order], current_time: float
    ) -> bool:
        """
        Check if a tare should depart based on departure rules.

        Args:
            tare: Tare to check
            orders: Orders loaded on tare
            current_time: Current simulation time

        Returns:
            True if tare should depart
        """
        if not orders:
            return False

        total_weight = sum(o.weight_kg for o in orders)
        load_ratio = total_weight / tare.capacity_kg

        oldest_order = min(orders, key=lambda o: o.created_at)
        wait_time = current_time - oldest_order.created_at

        # 5-minute rule OR load ratio threshold
        return wait_time >= self.min_stay_sec or load_ratio >= self.min_load_ratio
