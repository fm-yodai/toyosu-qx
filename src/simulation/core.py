import simpy
from typing import List, Dict, Optional
from .entities import Turret, Order, TurretState
from .market import MarketMap
from .generator import DataGenerator
from .logger import SimulationLogger
from ..utils.config import Scenario
from ..optimization.solver_base import BaseSolver

class Simulation:
    def __init__(self, scenario: Scenario, solver: BaseSolver, log_dir: str):
        self.scenario = scenario
        self.solver = solver
        self.env = simpy.Environment()
        self.market = MarketMap(
            scenario.market.width, 
            scenario.market.height,
            scenario.market.parking_start_x
        )
        self.logger = SimulationLogger(log_dir)
        
        self.turrets: List[Turret] = []
        self.orders: List[Order] = []
        self.completed_orders: List[Order] = []
        
        self.generator = DataGenerator(scenario)

    def initialize(self):
        """Setup turrets and initial state."""
        # Generate Orders
        self.orders = self.generator.generate_orders()
        print(f"Generated {len(self.orders)} orders.")
        
        # Log order creation
        for o in self.orders:
            self.logger.log_event(o.created_time, "ORDER_CREATED", "SYSTEM", {"order_id": o.id})
        
        # Create Turrets
        for i in range(self.scenario.sim.num_turrets):
            t_config = self.scenario.turret
            # Distribute wholesalers: W0, W1, W0, W1...
            w_id = f"W{i % 2}"
            turret = Turret(
                id=f"T{i}",
                wholesaler_id=w_id,
                capacity=t_config.capacity,
                speed=t_config.speed
            )
            # Initial location (depot?) - Let's assume (0,0) or random
            turret.location = (0, 0) 
            
            self.turrets.append(turret)
            self.env.process(self.turret_process(turret))
            
        # Order release process (simulating orders becoming available)
        # For now, we assume all orders are known but have 'created_time'.
        # The dispatcher should only see orders where created_time <= now.
        
        # Dispatcher process
        self.env.process(self.dispatcher_process())
        
        # Logger process (periodic status logging)
        self.env.process(self.logging_process())

    def run(self):
        self.initialize()
        self.env.run(until=self.scenario.sim.duration_seconds)
        self.logger.save_logs()
        print("Simulation finished.")

    def dispatcher_process(self):
        """Periodically runs the solver to assign orders."""
        while True:
            # Filter orders: Unassigned AND created_time <= now
            available_orders = [
                o for o in self.orders 
                if o.assigned_turret_id is None and o.created_time <= self.env.now
            ]
            
            if available_orders:
                assignments = self.solver.solve(available_orders, self.turrets, self.env.now)
                
                for turret_id, assigned_orders in assignments.items():
                    turret = next((t for t in self.turrets if t.id == turret_id), None)
                    if turret:
                        for order in assigned_orders:
                            order.assigned_turret_id = turret.id
                            turret.loaded_orders.append(order)
                            self.logger.log_event(self.env.now, "ASSIGN", turret.id, {"order_id": order.id})
            
            yield self.env.timeout(60) # Run every minute

    def turret_process(self, turret: Turret):
        """Main lifecycle of a turret."""
        while True:
            if turret.state == TurretState.IDLE:
                if turret.loaded_orders:
                    turret.state = TurretState.LOADING
                    turret.loading_start_time = self.env.now
                    self.logger.log_event(self.env.now, "STATE_CHANGE", turret.id, {"state": "LOADING"})
                else:
                    yield self.env.timeout(1)
            
            elif turret.state == TurretState.LOADING:
                # Check departure conditions
                should_depart = False
                
                # 1. Full capacity
                if len(turret.loaded_orders) >= turret.capacity:
                    should_depart = True
                
                # 2. Wait time > 5 min
                if turret.loading_start_time and (self.env.now - turret.loading_start_time >= 300):
                    should_depart = True
                    
                # 3. Deadline approaching (15 min)
                if turret.loaded_orders:
                    min_deadline = min(o.deadline for o in turret.loaded_orders)
                    if min_deadline - self.env.now < 900:
                        should_depart = True
                
                if should_depart and turret.loaded_orders:
                    turret.state = TurretState.MOVING
                    self.logger.log_event(self.env.now, "STATE_CHANGE", turret.id, {"state": "MOVING"})
                else:
                    # Wait for more orders or time
                    yield self.env.timeout(1)
            
            elif turret.state == TurretState.MOVING:
                # Process orders: Pickup -> Delivery
                # For baseline, we assume orders are already "at the turret" (instant pickup at depot/start)
                # or we need to go to origin then dest.
                # Let's assume we need to visit Origin then Dest for each order.
                # Or if they are consolidated, visit all Origins then all Dests.
                # Simple VRP: Visit all locations in optimal order?
                # Baseline: Just visit in order of list.
                
                # Create a route
                route = []
                for order in turret.loaded_orders:
                    # If we are not at origin, go to origin (Pickup)
                    # But wait, 'loaded_orders' implies they are ON the truck?
                    # If they are assigned but not picked up, we need to go to origin.
                    # Let's assume 'loaded_orders' means "Assigned and ready to be picked up".
                    # We need to distinguish "Assigned" vs "Onboard".
                    # For simplicity in M1 Baseline:
                    # 1. Go to Origin of Order 1 (Pickup)
                    # 2. Go to Dest of Order 1 (Delivery)
                    # (This is inefficient but baseline).
                    # Better Baseline: Collect all, then Deliver all?
                    # Let's do: Visit all Origins, then all Dests.
                    
                    route.append((order.origin, "PICKUP", order))
                    route.append((order.dest, "DELIVERY", order))
                
                # Optimize route? No, baseline. Just follow sequence?
                # Let's sort route by some heuristic or just keep it.
                # If we have multiple orders, maybe Pickup O1, Pickup O2, Deliver O1, Deliver O2?
                # Let's just iterate through the orders as they are in the list.
                
                # We need to actually move.
                current_orders = list(turret.loaded_orders) # Copy
                
                for order in current_orders:
                    # Go to Origin
                    yield from self.move_to(turret, order.origin)
                    self.logger.log_event(self.env.now, "PICKUP", turret.id, {"order_id": order.id})
                    order.pickup_time = self.env.now
                    
                    # Go to Dest
                    yield from self.move_to(turret, order.dest)
                    self.logger.log_event(self.env.now, "DELIVERY", turret.id, {"order_id": order.id})
                    order.delivery_time = self.env.now
                    self.completed_orders.append(order)
                    
                # Clear orders
                turret.loaded_orders.clear()
                turret.loading_start_time = None
                turret.state = TurretState.IDLE
                self.logger.log_event(self.env.now, "STATE_CHANGE", turret.id, {"state": "IDLE"})
                
            else:
                yield self.env.timeout(1)

    def move_to(self, turret: Turret, target: tuple):
        """Move turret to target location using Manhattan waypoints with step-by-step updates."""
        waypoints = self.market.get_waypoints(turret.location, target)
        
        # waypoints[0] is current location
        for next_wp in waypoints[1:]:
            # Determine axis and direction
            start_pos = turret.location
            if start_pos == next_wp:
                continue
                
            axis = 0 if next_wp[0] != start_pos[0] else 1
            direction = 1 if next_wp[axis] > start_pos[axis] else -1
            
            # Move step by step to keep location updated for the logger
            current_pos = list(start_pos)
            while current_pos[axis] != next_wp[axis]:
                current_pos[axis] += direction
                # Move 1 unit
                duration = 1.0 / turret.speed
                yield self.env.timeout(duration)
                turret.location = tuple(current_pos)
            
            # Arrived at waypoint (Corner or End) - Force Log
            self.logger.log_event(self.env.now, "POSITION", turret.id, {
                "x": turret.location[0], 
                "y": turret.location[1], 
                "state": turret.state.value
            })

    def logging_process(self):
        """Log periodic stats."""
        while True:
            # Log positions of all turrets
            for t in self.turrets:
                self.logger.log_event(self.env.now, "POSITION", t.id, {"x": t.location[0], "y": t.location[1], "state": t.state.value})
            yield self.env.timeout(10) # Log every 10 seconds
