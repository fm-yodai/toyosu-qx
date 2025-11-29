import polars as pl
import plotly.express as px
import pandas as pd
import os
import numpy as np

class Animator:
    def __init__(self, log_dir: str, width: int = 50, height: int = 50, parking_start_x: int = 40):
        self.log_dir = log_dir
        self.width = width
        self.height = height
        self.parking_start_x = parking_start_x
        
    def create_animation(self, output_file="animation.html"):
        events_path = os.path.join(self.log_dir, "events.csv")
        if not os.path.exists(events_path):
            print("No events log found for animation.")
            return

        df = pl.read_csv(events_path)
        pos_df = df.filter(pl.col("type") == "POSITION")
        
        if pos_df.is_empty():
            print("No position data found.")
            return
            
        # Convert to pandas for easier resampling/interpolation
        pdf = pos_df.to_pandas()
        
        # Ensure time is numeric
        pdf['time'] = pd.to_numeric(pdf['time'])
        
        # Get all unique times and entities
        min_time = int(pdf['time'].min())
        max_time = int(pdf['time'].max())
        all_times = np.arange(min_time, max_time + 1)
        entities = pdf['entity_id'].unique()
        
        # Create a full index (time x entity)
        full_index = pd.MultiIndex.from_product([all_times, entities], names=['time', 'entity_id'])
        
        # Reindex
        pdf_indexed = pdf.set_index(['time', 'entity_id'])
        # Remove duplicates if any
        pdf_indexed = pdf_indexed[~pdf_indexed.index.duplicated(keep='first')]
        
        # Reindex to full range
        pdf_full = pdf_indexed.reindex(full_index)
        
        # Reset index to work with columns
        pdf_full = pdf_full.reset_index()
        
        # Interpolate per entity
        # We need to sort by entity, then time
        pdf_full = pdf_full.sort_values(['entity_id', 'time'])
        
        # Interpolate X and Y
        pdf_full['x'] = pdf_full.groupby('entity_id')['x'].transform(lambda group: group.interpolate(method='linear'))
        pdf_full['y'] = pdf_full.groupby('entity_id')['y'].transform(lambda group: group.interpolate(method='linear'))
        
        # Forward fill state (state doesn't interpolate, it persists)
        pdf_full['state'] = pdf_full.groupby('entity_id')['state'].transform(lambda group: group.ffill().bfill())
        
        # Fill NaNs (if any remaining at start/end)
        pdf_full = pdf_full.fillna(method='ffill').fillna(method='bfill')
        
        # Downsample for visualization if too large (e.g. every 5 seconds)
        # User asked for 1s, but for 4 hours (14400s) it might be heavy.
        # Let's try 10s for now, or 5s.
        # If duration is 3600s, 1s is 3600 frames. Plotly can handle it but file will be large.
        # Let's do every 10s to match the log frequency for now, since interpolation adds no real info if we only logged every 10s.
        # Wait, if I interpolate, I can show smooth movement.
        # But if I only logged every 10s, linear interpolation is just a straight line.
        # Let's stick to the logged data points for the first version to keep it simple and fast.
        # Actually, the user asked for "1s granularity".
        # I'll resample to 1s.
        
        # Filter to every 5th frame to keep file size manageable for this demo
        # pdf_vis = pdf_full[pdf_full['time'] % 5 == 0]
        pdf_vis = pdf_full # Use full 1s resolution
        
        print(f"Generating animation with {len(pdf_vis)} frames...")
        
        fig = px.scatter(
            pdf_vis, 
            x="x", y="y", 
            animation_frame="time", 
            animation_group="entity_id",
            color="state", 
            hover_name="entity_id",
            range_x=[0, self.width], 
            range_y=[0, self.height],
            title="Toyosu QX Simulation"
        )
        
        # Add Parking Zone indicator
        fig.add_shape(
            type="rect",
            x0=self.parking_start_x, y0=0,
            x1=self.width, y1=self.height,
            fillcolor="LightSalmon", opacity=0.3,
            layer="below", line_width=0,
        )
        
        fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 50 # 20fps
        
        output_path = os.path.join(self.log_dir, output_file)
        fig.write_html(output_path)
        print(f"Animation saved to {output_path}")
