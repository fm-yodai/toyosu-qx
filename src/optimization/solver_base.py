from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..simulation.entities import Order, Turret

class BaseSolver(ABC):
    """Abstract base class for all optimization solvers."""
    
    def __init__(self, **kwargs):
        self.config = kwargs

    @abstractmethod
    def solve(self, 
              orders: List[Order], 
              turrets: List[Turret], 
              current_time: float) -> Dict[str, List[Order]]:
        """
        Decide which orders should be assigned to which turrets.
        
        Args:
            orders: List of unassigned or pending orders.
            turrets: List of available turrets.
            current_time: Current simulation time.
            
        Returns:
            Dictionary mapping turret_id to a list of assigned Orders.
            The list implies the sequence of processing (or just a batch to be routed).
        """
        pass
