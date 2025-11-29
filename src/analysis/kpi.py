import polars as pl
import os

class KPICalculator:
    def __init__(self, log_dir: str):
        self.log_dir = log_dir
        self.events_path = os.path.join(log_dir, "events.csv")
        
    def calculate(self):
        if not os.path.exists(self.events_path):
            print("No events log found.")
            return
            
        df = pl.read_csv(self.events_path)
        
        # 1. Lead Time (Delivery Time - Creation Time)
        # Get creation times
        created = df.filter(pl.col("type") == "ORDER_CREATED").select(
            pl.col("order_id"), 
            pl.col("time").alias("created_time")
        )
        
        # Get delivery times
        delivered = df.filter(pl.col("type") == "DELIVERY").select(
            pl.col("order_id"),
            pl.col("time").alias("delivery_time")
        )
        
        # Join
        lt_df = created.join(delivered, on="order_id", how="inner")
        lt_df = lt_df.with_columns(
            (pl.col("delivery_time") - pl.col("created_time")).alias("lead_time")
        )
        
        avg_lt = lt_df["lead_time"].mean()
        p95_lt = lt_df["lead_time"].quantile(0.95)
        
        print(f"KPI: Average Lead Time = {avg_lt:.2f} s")
        print(f"KPI: 95% Lead Time = {p95_lt:.2f} s")
        
        # 2. Utilization
        # We need to track state duration.
        # Filter STATE_CHANGE events.
        # Group by entity_id, sort by time.
        # Calculate duration of each state.
        
        # Simple approximation: Count samples if we logged periodically?
        # We logged POSITION every 10s with state.
        pos_df = df.filter(pl.col("type") == "POSITION")
        if not pos_df.is_empty():
            # Count occurrences of each state
            state_counts = pos_df.group_by("state").count()
            total_samples = pos_df.height
            
            print("KPI: State Distribution (Sampled):")
            print(state_counts)
            
        # 3. Distance
        # Sum of distances between consecutive POSITION logs?
        # Or use MOVE events if we had them.
        # We didn't log MOVE distance explicitly, but we have coordinates in POSITION.
        # We can calculate distance from coordinates.
        
        if not pos_df.is_empty():
            # Sort by entity_id, time
            pos_df = pos_df.sort(["entity_id", "time"])
            # Calculate dist between consecutive rows for same entity
            # This is hard in pure polars without window functions or shift.
            # Polars has shift.
            
            pos_df = pos_df.with_columns([
                pl.col("x").shift(1).over("entity_id").alias("prev_x"),
                pl.col("y").shift(1).over("entity_id").alias("prev_y")
            ])
            
            # Filter out first row (where prev is null)
            pos_df = pos_df.drop_nulls(["prev_x", "prev_y"])
            
            # Ensure numeric types
            pos_df = pos_df.with_columns([
                pl.col("x").cast(pl.Float64),
                pl.col("y").cast(pl.Float64),
                pl.col("prev_x").cast(pl.Float64),
                pl.col("prev_y").cast(pl.Float64)
            ])
            
            # Calc Manhattan distance
            pos_df = pos_df.with_columns(
                (
                    (pl.col("x") - pl.col("prev_x")).abs() + 
                    (pl.col("y") - pl.col("prev_y")).abs()
                ).alias("step_dist")
            )
            
            total_dist = pos_df["step_dist"].sum()
            print(f"KPI: Total Distance = {total_dist:.2f} units")

        return {
            "avg_lead_time": avg_lt,
            "p95_lead_time": p95_lt,
            "total_distance": total_dist if not pos_df.is_empty() else 0
        }
