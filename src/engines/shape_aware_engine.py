import numpy as np
import time
from typing import List, Optional, Tuple
from src.engines.nesting_engine import NestingEngine
from src.models.models import Part, Sheet, NestingResult, PlacedPart, SheetResult, ManufacturingConstraints

class ShapeAwareEngine(NestingEngine):
    """
    Experimental engine that uses a grid-based occupancy map to allow 
    tight packing of complex shapes by nesting them in each other's bounding boxes.
    """
    def __init__(self, resolution_mm: float = 10.0):
        super().__init__(name="Shape-Aware Engine")
        self.resolution = resolution_mm

    def _get_shape_mask(self, part: Part, w: float, h: float, rotated: bool, cell_w: int, cell_h: int) -> np.ndarray:
        """Returns a boolean mask of the actual shape area in grid cells."""
        mask = np.zeros((cell_h, cell_w), dtype=bool)
        meta = getattr(part, 'metadata', {})
        shape = meta.get('shape', 'RECT').upper()
        
        if shape == 'RECT':
            mask[:, :] = True
        elif shape in ['TRIANGLE', 'ISOSCELES_TRIANGLE']:
            # Isosceles Triangle
            for y in range(cell_h):
                yy = (y + 0.5) * self.resolution
                # In normalized coords 0 to 1
                row_progress = yy / h
                if row_progress > 1: row_progress = 1
                half_width_at_y = (1 - row_progress) * 0.5
                start_x = int((0.5 - half_width_at_y) * cell_w)
                end_x = int((0.5 + half_width_at_y) * cell_w)
                mask[y, start_x:end_x] = True
        elif shape == 'RIGHT_TRIANGLE':
            for y in range(cell_h):
                yy = (y + 0.5) * self.resolution
                row_progress = yy / h
                if row_progress > 1: row_progress = 1
                # Standard Right Triangle: (0,0), (w,0), (0,h)
                if not rotated:
                    width_at_y = int((1 - row_progress) * cell_w)
                    mask[y, :width_at_y] = True
                else:
                    # Rotated (just an example, depends on orientation)
                    width_at_y = int(row_progress * cell_w)
                    mask[y, :width_at_y] = True
        elif shape == 'CIRCLE':
            center_x = cell_w / 2
            center_y = cell_h / 2
            radius_cells = (min(w, h) / 2) / self.resolution
            y_indices, x_indices = np.ogrid[:cell_h, :cell_w]
            dist_sq = (x_indices - center_x)**2 + (y_indices - center_y)**2
            mask = dist_sq <= radius_cells**2
        elif shape == 'SEMI_CIRCLE':
            center_x = cell_w / 2
            center_y = 0 # Base is bottom
            radius_cells = (w / 2) / self.resolution
            y_indices, x_indices = np.ogrid[:cell_h, :cell_w]
            dist_sq = (x_indices - center_x)**2 + (y_indices - center_y)**2
            mask = (dist_sq <= radius_cells**2) & (y_indices >= 0)
        elif shape == 'QUARTER_CIRCLE':
            center_x = 0
            center_y = 0
            radius_cells = w / self.resolution
            y_indices, x_indices = np.ogrid[:cell_h, :cell_w]
            dist_sq = (x_indices - center_x)**2 + (y_indices - center_y)**2
            mask = dist_sq <= radius_cells**2
        else:
            mask[:, :] = True
            
        return mask

    def _find_first_fit(self, grid: np.ndarray, mask: np.ndarray, cell_w: int, cell_h: int) -> Tuple[Optional[int], Optional[int]]:
        gh, gw = grid.shape
        # Optimization: Pre-calculate if ANY part of a bounding box is free
        # before doing expensive bitwise AND with the complex mask.
        for y in range(gh - cell_h + 1):
            for x in range(gw - cell_w + 1):
                # 1. Quick check: Is the first corner free?
                if grid[y, x]: continue
                
                # 2. Medium check: Is the whole bounding box free? 
                # If YES, then mask fit is guaranteed.
                if not np.any(grid[y:y+cell_h, x:x+cell_w]):
                    return x, y
                
                # 3. Slow check: Does the actual shape overlap with existing shapes?
                # Only needed if the bounding box has some overlap.
                if not np.any(grid[y:y+cell_h, x:x+cell_w] & mask):
                    return x, y
        return None, None

    def optimize(self, sheet_template: Sheet, parts: List[Part], constraints: Optional[ManufacturingConstraints] = None) -> NestingResult:
        start_time = time.time()
        if constraints is None:
            constraints = ManufacturingConstraints()

        kerf = constraints.kerf
        margin = constraints.margin
        
        # Grid dimensions
        grid_w = int((sheet_template.width) / self.resolution)
        grid_h = int((sheet_template.height) / self.resolution)
        
        remaining_parts = parts[:]
        # Sort by area for greedy first-fit
        remaining_parts.sort(key=lambda p: p.width * p.height, reverse=True)
        
        sheet_results: List[SheetResult] = []
        
        while remaining_parts:
            current_sheet_res = SheetResult(sheet=sheet_template)
            grid = np.zeros((grid_h, grid_w), dtype=bool)
            
            # Mark margins as occupied
            margin_cells = int(margin / self.resolution)
            if margin_cells > 0:
                grid[:margin_cells, :] = True
                grid[grid_h-margin_cells:, :] = True
                grid[:, :margin_cells] = True
                grid[:, grid_w-margin_cells:] = True

            placed_on_this_sheet = []
            still_to_process = []
            
            for part in remaining_parts:
                placed = False
                
                # Orientations
                orientations = [(part.width, part.height, False)]
                if constraints.allow_rotation and part.width != part.height:
                    orientations.append((part.height, part.width, True))
                
                for w, h, rotated in orientations:
                    # Dimensions in grid cells (include kerf)
                    rw = w + kerf
                    rh = h + kerf
                    cell_w = int(np.ceil(rw / self.resolution))
                    cell_h = int(np.ceil(rh / self.resolution))
                    
                    if cell_w > grid_w or cell_h > grid_h:
                        continue
                        
                    # Get shape mask in grid cells
                    mask = self._get_shape_mask(part, w, h, rotated, cell_w, cell_h)
                    
                    # Find first fit
                    found_x, found_y = self._find_first_fit(grid, mask, cell_w, cell_h)
                    
                    if found_x is not None:
                        # Place it
                        grid[found_y:found_y+cell_h, found_x:found_x+cell_w] |= mask
                        placed_on_this_sheet.append(PlacedPart(
                            part=part, 
                            x=found_x * self.resolution, 
                            y=found_y * self.resolution, 
                            is_rotated=rotated
                        ))
                        placed = True
                        break
                
                if not placed:
                    still_to_process.append(part)
            
            if not placed_on_this_sheet:
                # If we can't place ANY part on a fresh sheet, skip it
                if remaining_parts:
                    still_to_process.append(remaining_parts.pop(0))
                continue

            current_sheet_res.placed_parts = placed_on_this_sheet
            current_sheet_res.calculate_metrics(constraints.min_reusable_area, constraints.min_reusable_dim)
            sheet_results.append(current_sheet_res)
            remaining_parts = still_to_process

        return NestingResult(
            sheets=sheet_results,
            total_parts_requested=len(parts),
            total_parts_placed=sum(len(s.placed_parts) for s in sheet_results),
            runtime_seconds=time.time() - start_time
        )
