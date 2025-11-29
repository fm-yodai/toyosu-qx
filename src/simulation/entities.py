from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, Optional

class TurretState(Enum):
    IDLE = "IDLE"
    MOVING = "MOVING"
    LOADING = "LOADING"
    UNLOADING = "UNLOADING"

@dataclass
class Order:
    id: str
    origin: Tuple[int, int]
    dest: Tuple[int, int]
    volume: int
    created_time: float
    deadline: float
    # Owner wholesaler ID could be added here if needed for the baseline rule
    wholesaler_id: str = "default_wholesaler" 
    
    # Status tracking
    pickup_time: Optional[float] = None
    delivery_time: Optional[float] = None
    assigned_turret_id: Optional[str] = None

@dataclass
class Turret:
    id: str
    wholesaler_id: str # Turret belongs to a specific wholesaler
    capacity: int
    speed: float # m/s
    
    # Dynamic state
    location: Tuple[int, int] = (0, 0)
    state: TurretState = TurretState.IDLE
    current_load: int = 0
    loaded_orders: list[Order] = field(default_factory=list)
    loading_start_time: Optional[float] = None
    
    # For simulation logic
    action_process = None # SimPy process
