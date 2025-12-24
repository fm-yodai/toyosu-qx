"""
Core data models for Toyosu-QX simulation.

Defines the main entities: Tare (turret truck), Order, Node (location),
Grid (2D space), and various event/state enums.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


@dataclass
class Grid:
    """
    2D grid space representing the market layout.

    The grid consists of corridors (通路) where tares can move.
    Movement is restricted to horizontal (x-axis) and vertical (y-axis)
    directions only (Manhattan distance).

    Attributes:
        width: Grid width in cells
        height: Grid height in cells
        cell_size_m: Size of each cell in meters (default 10m)
    """
    width: int
    height: int
    cell_size_m: float = 10.0  # Each cell is 10m x 10m

    def is_valid_position(self, x: int, y: int) -> bool:
        """Check if position is within grid bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def manhattan_distance(self, x1: int, y1: int, x2: int, y2: int) -> int:
        """
        Calculate Manhattan distance between two grid positions.

        In a grid with corridors, tares can only move horizontally
        or vertically, so the distance is |x1-x2| + |y1-y2| cells.

        Args:
            x1, y1: Start position
            x2, y2: End position

        Returns:
            Manhattan distance in cells
        """
        return abs(x1 - x2) + abs(y1 - y2)

    def distance_meters(self, x1: int, y1: int, x2: int, y2: int) -> float:
        """
        Calculate distance in meters between two grid positions.

        Args:
            x1, y1: Start position
            x2, y2: End position

        Returns:
            Distance in meters
        """
        return self.manhattan_distance(x1, y1, x2, y2) * self.cell_size_m


class TareState(Enum):
    """State of a tare truck."""
    IDLE = "idle"  # Waiting at wholesaler
    LOADING = "loading"  # Loading cargo
    TRAVELING = "traveling"  # En route to destination
    UNLOADING = "unloading"  # Unloading at retailer
    TRADE_PROC = "trade_proc"  # Processing trade confirmation


class EventType(Enum):
    """Event types in the simulation."""
    LOAD_START = "load_start"
    LOAD_END = "load_end"
    DEPART = "depart"
    ARRIVE = "arrive"
    UNLOAD_START = "unload_start"
    UNLOAD_END = "unload_end"
    TRADE_CONFIRM = "trade_confirm"
    ORDER_GENERATED = "order_generated"
    ORDER_ASSIGNED = "order_assigned"
    ORDER_DELIVERED = "order_delivered"


class NodeType(Enum):
    """Type of location node."""
    WHOLESALER = "wholesaler"  # 仲卸
    RETAILER = "retailer"  # 小売


@dataclass
class Node:
    """
    A location in the market (wholesaler or retailer).

    Attributes:
        id: Unique node identifier
        type: WHOLESALER or RETAILER
        x: X grid coordinate (cell position)
        y: Y grid coordinate (cell position)
        name: Human-readable name (optional)
    """
    id: str
    type: NodeType
    x: int  # Grid cell x-coordinate
    y: int  # Grid cell y-coordinate
    name: Optional[str] = None


@dataclass
class Order:
    """
    A delivery order from wholesaler to retailer.

    Attributes:
        id: Unique order identifier
        origin: Wholesaler node ID
        destination: Retailer node ID
        weight_kg: Weight in kg (10/30/50 typical)
        created_at: Simulation time when order was generated (seconds)
        assigned_at: When order was assigned to a tare (optional)
        delivered_at: When order was delivered (optional)
        tare_id: ID of tare assigned to this order (optional)
    """
    id: str
    origin: str  # Node ID
    destination: str  # Node ID
    weight_kg: float
    created_at: float  # simulation time in seconds
    assigned_at: Optional[float] = None
    delivered_at: Optional[float] = None
    tare_id: Optional[str] = None


@dataclass
class Tare:
    """
    A turret truck (ターレ) that delivers orders.

    Attributes:
        id: Unique tare identifier
        home: Wholesaler node ID (owner)
        capacity_kg: Maximum load capacity
        state: Current state (IDLE, LOADING, etc.)
        current_node: Current location node ID
        current_load_kg: Current total load weight
        orders: List of order IDs currently loaded
        last_state_change: Simulation time of last state change
        total_distance_m: Cumulative distance traveled (meters)
        total_operating_sec: Total time spent not idle (seconds)
    """
    id: str
    home: str  # Node ID of owning wholesaler
    capacity_kg: float
    state: TareState = TareState.IDLE
    current_node: Optional[str] = None
    current_load_kg: float = 0.0
    orders: list[str] = field(default_factory=list)  # Order IDs
    last_state_change: float = 0.0
    total_distance_m: float = 0.0
    total_operating_sec: float = 0.0


@dataclass
class SimEvent:
    """
    A discrete event in the simulation log.

    Attributes:
        ts: Timestamp (simulation seconds)
        run_id: Unique run identifier
        tare_id: Tare involved (optional)
        node: Node ID where event occurred (optional)
        event: Event type
        state: Tare state after event (optional)
        load_kg: Current load weight (optional)
        payload: Additional event-specific data (optional)
    """
    ts: float
    run_id: str
    event: EventType
    tare_id: Optional[str] = None
    node: Optional[str] = None
    state: Optional[TareState] = None
    load_kg: Optional[float] = None
    payload: Optional[dict] = None
