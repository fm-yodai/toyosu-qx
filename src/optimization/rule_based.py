from typing import List, Dict
from ..simulation.entities import Order, Turret, TurretState
from .solver_base import BaseSolver

class RuleBasedSolver(BaseSolver):
    """
    Baseline Rule-based Dispatcher.
    - Assigns orders to turrets of the same wholesaler.
    - Assigns to IDLE or LOADING turrets.
    - Does not optimize for route, just capacity.
    """
    
    def solve(self, 
              orders: List[Order], 
              turrets: List[Turret], 
              current_time: float) -> Dict[str, List[Order]]:
        
        assignments: Dict[str, List[Order]] = {}
        
        # Helper: Get available turrets by wholesaler
        # Only consider turrets that are IDLE or LOADING (and not full)
        available_turrets = {}
        for t in turrets:
            if t.state in [TurretState.IDLE, TurretState.LOADING]:
                # Check capacity (current load + planned load)
                # Note: This simple check assumes all assigned orders will be loaded.
                # In reality, we need to track 'planned_load' if assignments are not immediate.
                # Here we assume assignments are immediately accepted into 'loaded_orders' or a queue.
                if len(t.loaded_orders) < t.capacity:
                    if t.wholesaler_id not in available_turrets:
                        available_turrets[t.wholesaler_id] = []
                    available_turrets[t.wholesaler_id].append(t)

        # Sort orders by deadline (earliest deadline first)
        sorted_orders = sorted(orders, key=lambda o: o.deadline)
        
        for order in sorted_orders:
            w_id = order.wholesaler_id
            candidates = available_turrets.get(w_id, [])
            
            if not candidates:
                continue
                
            # Strategy: Fill the turret that is already LOADING first, then IDLE.
            # Sort candidates: LOADING first, then by ID.
            candidates.sort(key=lambda t: (t.state != TurretState.LOADING, t.id))
            
            best_turret = candidates[0]
            
            # Assign
            if best_turret.id not in assignments:
                assignments[best_turret.id] = []
            
            assignments[best_turret.id].append(order)
            
            # Update virtual capacity for this step
            # (We don't modify the actual turret object here, just local tracking)
            # But since we iterate, we need to know if this turret is now full.
            # We can't easily track this without modifying the turret or a local counter.
            # For simplicity, we'll just assign and let the loop continue. 
            # Ideally we should decrement capacity.
            
            # Hack: Check if we exceeded capacity with *this* batch of assignments
            current_assigned_count = len(best_turret.loaded_orders) + len(assignments[best_turret.id])
            if current_assigned_count >= best_turret.capacity:
                candidates.remove(best_turret)
                
        return assignments
