import csv
import os
from typing import Any, Dict
from dataclasses import asdict
from .entities import Order, Turret

class SimulationLogger:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.events = []
        
    def log_event(self, time: float, event_type: str, entity_id: str, details: Dict[str, Any]):
        """Log a generic simulation event."""
        event = {
            "time": time,
            "type": event_type,
            "entity_id": entity_id,
            **details
        }
        self.events.append(event)
        
    def save_logs(self):
        """Save collected logs to CSV/Parquet."""
        # For now, simple CSV
        if not self.events:
            return
            
        import polars as pl
        # Use from_dicts with large inference length to ensure all columns (x, y, etc.) are captured
        # even if they don't appear in the first 100 rows (e.g. ORDER_CREATED events).
        df = pl.from_dicts(self.events, infer_schema_length=10000)
        df.write_csv(os.path.join(self.log_dir, "events.csv"))
