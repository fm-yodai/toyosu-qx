from typing import Tuple, List
import math

class MarketMap:
    def __init__(self, width: int, height: int, parking_start_x: int):
        self.width = width
        self.height = height
        self.parking_start_x = parking_start_x
        
    def is_parking_zone(self, loc: Tuple[int, int]) -> bool:
        return loc[0] >= self.parking_start_x
        
    def is_wholesaler_zone(self, loc: Tuple[int, int]) -> bool:
        return loc[0] < self.parking_start_x
        
    def get_distance(self, p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate Manhattan distance between two points."""
        return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
    
    def get_path(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Generate a path from start to end using Manhattan routing.
        Returns a list of coordinate tuples including start and end.
        """
        # ... (existing implementation if needed, but we might replace it or just add get_waypoints)
        # Actually, let's just replace get_path logic or add get_waypoints.
        # The user wants "grid", so let's keep get_path for detailed steps if needed, 
        # but for movement we want waypoints.
        pass

    def get_waypoints(self, start: Tuple[int, int], end: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Return the key waypoints for Manhattan routing (Start -> Corner -> End).
        """
        if start == end:
            return [start]
            
        waypoints = [start]
        # Corner point: Move X first, then Y
        # (end_x, start_y)
        corner = (end[0], start[1])
        
        if corner != start and corner != end:
            waypoints.append(corner)
            
        waypoints.append(end)
        return waypoints

    def is_valid_location(self, loc: Tuple[int, int]) -> bool:
        x, y = loc
        return 0 <= x < self.width and 0 <= y < self.height
