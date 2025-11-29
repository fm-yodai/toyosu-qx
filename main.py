import os
from src.utils.config import SCENARIO_BASELINE
from src.optimization.rule_based import RuleBasedSolver
from src.simulation.core import Simulation

def main():
    # Setup
    scenario = SCENARIO_BASELINE
    solver = RuleBasedSolver()
    log_dir = os.path.join("logs", scenario.name)
    
    print(f"Starting simulation: {scenario.name}")
    print(f"Duration: {scenario.sim.duration_seconds}s")
    print(f"Turrets: {scenario.sim.num_turrets}")
    print(f"Orders: {scenario.sim.num_orders}")
    
    # Run
    sim = Simulation(scenario, solver, log_dir)
    sim.run()
    
    # Basic check
    completed = len(sim.completed_orders)
    total = len(sim.orders)
    print(f"Completed Orders: {completed}/{total}")
    
    if completed < total:
        print("Warning: Not all orders were completed.")
        
    # Calculate KPIs
    from src.analysis.kpi import KPICalculator
    kpi = KPICalculator(log_dir)
    kpi.calculate()
    
    # Generate Animation
    from src.visualization.animator import Animator
    anim = Animator(
        log_dir, 
        width=scenario.market.width, 
        height=scenario.market.height,
        parking_start_x=scenario.market.parking_start_x
    )
    anim.create_animation()
        
if __name__ == "__main__":
    main()
