from dataclasses import dataclass, field

@dataclass
class MarketConfig:
    """Configuration for the market layout."""
    width: int = 300  # Grid width (x-axis)
    height: int = 100 # Grid height (y-axis)
    parking_zone_width: int = 20 # Width of the parking area on the right
    
    @property
    def parking_start_x(self) -> int:
        return self.width - self.parking_zone_width

@dataclass
class TurretConfig:
    """Configuration for Turret Trucks."""
    speed: float = 2.0  # m/s
    capacity: int = 1   # Number of pallets/units
    loading_time: int = 30 # seconds
    unloading_time: int = 30 # seconds

@dataclass
class SimulationConfig:
    """Configuration for the simulation run."""
    duration_seconds: int = 3600 * 4  # 4 hours
    random_seed: int = 42
    num_turrets: int = 10
    num_orders: int = 100
    order_interval_mean: int = 120 # seconds between orders (exponential)

@dataclass
class Scenario:
    """Complete simulation scenario."""
    name: str
    market: MarketConfig = field(default_factory=MarketConfig)
    turret: TurretConfig = field(default_factory=TurretConfig)
    sim: SimulationConfig = field(default_factory=SimulationConfig)

# Predefined Scenarios
SCENARIO_BASELINE = Scenario(
    name="baseline_dev",
    market=MarketConfig(width=300, height=100),
    turret=TurretConfig(speed=2.0, capacity=1),
    sim=SimulationConfig(
        duration_seconds=3600, 
        random_seed=42, 
        num_turrets=10, 
        num_orders=100
    )
)
