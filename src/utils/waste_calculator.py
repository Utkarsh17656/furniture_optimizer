from typing import List, Tuple, Any

class WasteCalculator:
    @staticmethod
    def calculate_reusable_waste(rects: List[Any], min_area: float, min_dim: float) -> float:
        """
        Calculates the union area of all rectangles that meet the minimum size criteria.
        Expects objects with .x, .y, .width, .height
        """
        valid_rects = []
        for r in rects:
            if r.width * r.height >= min_area and min(r.width, r.height) >= min_dim:
                valid_rects.append(r)
                
        if not valid_rects:
            return 0.0
            
        return WasteCalculator._union_area(valid_rects)
        
    @staticmethod
    def _union_area(rects: List[Any]) -> float:
        """Calculates the exact area of the union of rectangles."""
        if not rects:
            return 0.0
            
        # Extract unique x coordinates
        x_coords = []
        for r in rects:
            x_coords.extend([r.x, r.x + r.width])
        
        x_coords = sorted(list(set(x_coords)))
        
        # Build x intervals
        total_area = 0.0
        
        for i in range(len(x_coords) - 1):
            x1 = x_coords[i]
            x2 = x_coords[i+1]
            width = x2 - x1
            
            if width <= 0:
                continue
                
            # Find all segments that span this x-interval
            y_intervals = []
            for r in rects:
                if r.x <= x1 and r.x + r.width >= x2:
                    y_intervals.append((r.y, r.y + r.height))
                    
            if not y_intervals:
                continue
                
            # Merge y intervals and compute height in this x-interval
            y_intervals.sort()
            h_sum = 0.0
            current_start, current_end = y_intervals[0]
            
            for start, end in y_intervals[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    h_sum += (current_end - current_start)
                    current_start, current_end = start, end
            
            h_sum += (current_end - current_start)
            total_area += width * h_sum
            
        return total_area
