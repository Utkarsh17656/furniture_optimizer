from typing import List, Optional
import time
from src.engines.nesting_engine import NestingEngine
from src.models.models import Part, Sheet, NestingResult, PlacedPart, SheetResult, ManufacturingConstraints
from src.utils.waste_calculator import WasteCalculator

class Rect:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class ShelfNestingEngine(NestingEngine):
    """
    Implements a Multi-Sheet Shelf-based nesting algorithm with Manufacturing Constraints.
    """

    def __init__(self):
        super().__init__(name="Shelf Engine")

    def optimize(self, sheet_template: Sheet, parts: List[Part], constraints: Optional[ManufacturingConstraints] = None) -> NestingResult:
        start_time = time.time()
        
        if constraints is None:
            constraints = ManufacturingConstraints()

        kerf = constraints.kerf
        margin = constraints.margin
        
        # Effective sheet dimensions
        eff_width = sheet_template.width - 2 * margin
        eff_height = sheet_template.height - 2 * margin

        # Sort parts by height (decreasing)
        sorted_parts = sorted(parts, key=lambda p: p.height, reverse=True)
        
        remaining_parts = sorted_parts[:]
        sheet_results: List[SheetResult] = []
        
        while remaining_parts:
            current_sheet_res = SheetResult(sheet=sheet_template)
            placed_on_this_sheet = []
            free_rects = []
            
            # Shelf state
            current_x = margin
            current_y = margin
            current_shelf_height = 0.0
            
            still_to_process = []
            
            for part in remaining_parts:
                placed = False
                
                # Orientations to try
                orientations = [(part.width, part.height, False)]
                if constraints.allow_rotation and part.width != part.height:
                    orientations.append((part.height, part.width, True))

                # Sort orientations - for Shelf, we prefer the one that fits best in height if possible
                # or just try both.
                
                for w, h, rotated in orientations:
                    if w > eff_width or h > eff_height:
                        continue
                    
                    # Try to place in current shelf
                    temp_x = current_x
                    temp_y = current_y
                    
                    # Add kerf if not the first part in shelf
                    offset_x = kerf if current_x > margin else 0
                    
                    if temp_x + offset_x + w <= margin + eff_width and temp_y + h <= margin + eff_height:
                        # Fits in current shelf
                        placed_on_this_sheet.append(PlacedPart(part=part, x=temp_x + offset_x, y=temp_y, is_rotated=rotated))
                        current_x = temp_x + offset_x + w
                        current_shelf_height = max(current_shelf_height, h)
                        placed = True
                        break
                    else:
                        # Try to start new shelf
                        new_shelf_y = current_y + current_shelf_height + (kerf if current_shelf_height > 0 else 0)
                        if new_shelf_y + h <= margin + eff_height:
                            # Record remaining space in the old shelf as a free rect
                            remaining_w = (margin + eff_width) - current_x
                            if remaining_w > 0 and current_shelf_height > 0:
                                free_rects.append(Rect(current_x, current_y, remaining_w, current_shelf_height))
                                
                            # Start new shelf
                            current_y = new_shelf_y
                            current_x = margin
                            placed_on_this_sheet.append(PlacedPart(part=part, x=current_x, y=current_y, is_rotated=rotated))
                            current_x = margin + w
                            current_shelf_height = h
                            placed = True
                            break
                
                if not placed:
                    still_to_process.append(part)

            # Record remaining space in the final shelf
            remaining_w = (margin + eff_width) - current_x
            if remaining_w > 0 and current_shelf_height > 0:
                free_rects.append(Rect(current_x, current_y, remaining_w, current_shelf_height))
                
            # Record remaining space above the final shelf
            final_y = current_y + current_shelf_height
            remaining_h = (margin + eff_height) - final_y
            if remaining_h > 0:
                free_rects.append(Rect(margin, final_y, eff_width, remaining_h))

            current_sheet_res.placed_parts = placed_on_this_sheet
            
            # Calculate reusable waste explicitly for shelf engine
            current_sheet_res.reusable_waste_area = WasteCalculator.calculate_reusable_waste(
                free_rects,
                constraints.min_reusable_area,
                constraints.min_reusable_dim
            )
            
            # Shelf engine produces non-overlapping free rects, so we can just filter them directly
            for r in free_rects:
                if r.width * r.height >= constraints.min_reusable_area and min(r.width, r.height) >= constraints.min_reusable_dim:
                    current_sheet_res.reusable_scraps.append({
                        "width": round(r.width, 2),
                        "height": round(r.height, 2),
                        "area": round(r.width * r.height, 2)
                    })
            
            current_sheet_res.calculate_metrics()
            sheet_results.append(current_sheet_res)
            
            # To prevent infinite loops: if we couldn't place any part on a fresh sheet
            if not placed_on_this_sheet and remaining_parts:
                print(f"Warning: Part {remaining_parts[0].id} cannot fit with current constraints.")
                remaining_parts.pop(0)
            else:
                remaining_parts = still_to_process

        return NestingResult(
            sheets=sheet_results,
            total_parts_requested=len(parts),
            total_parts_placed=sum(len(s.placed_parts) for s in sheet_results),
            runtime_seconds=time.time() - start_time
        )
