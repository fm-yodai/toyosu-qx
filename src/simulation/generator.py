import random
from typing import List, Tuple
from .entities import Order
from ..utils.config import Scenario

class DataGenerator:
    def __init__(self, scenario: Scenario):
        self.scenario = scenario
        random.seed(scenario.sim.random_seed)
        
    def generate_orders(self) -> List[Order]:
        """Generate a list of orders based on the scenario."""
        orders = []
        sim_config = self.scenario.sim
        market_config = self.scenario.market
        
        for i in range(sim_config.num_orders):
            # Random creation time (uniform for now, can be Poisson process)
            created_time = random.uniform(0, sim_config.duration_seconds - 3600)
            
            # Origin: Wholesaler Zone (x < parking_start_x)
            # Dest: Parking Zone (x >= parking_start_x)
            
            parking_start = market_config.parking_start_x
            
            origin = (
                random.randint(0, parking_start - 1), 
                random.randint(0, market_config.height - 1)
            )
            
            dest = (
                random.randint(parking_start, market_config.width - 1), 
                random.randint(0, market_config.height - 1)
            )
                
            # Deadline: created_time + random buffer (30-60 mins)
            deadline = created_time + random.uniform(1800, 3600)
            
            # Wholesaler assignment (randomly W0 or W1)
            wholesaler_id = f"W{random.randint(0, 1)}"
            
            order = Order(
                id=f"O{i}",
                origin=origin,
                dest=dest,
                volume=1, # Default volume
                created_time=created_time,
                deadline=deadline,
                wholesaler_id=wholesaler_id
            )
            orders.append(order)
            
        # Sort by created time
        orders.sort(key=lambda x: x.created_time)
        return orders
