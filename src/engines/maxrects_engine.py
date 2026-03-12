from typing import List, Optional, Tuple
import time
from src.engines.nesting_engine import NestingEngine
from src.models.models import Part, Sheet, NestingResult, PlacedPart, SheetResult, ManufacturingConstraints

class Rect:
    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def intersects(self, other: 'Rect') -> bool:
        return not (other.x >= self.x + self.width or
                    other.x + other.width <= self.x or
                    other.y >= self.y + self.height or
                    other.y + other.height <= self.y)

    def contains(self, other: 'Rect') -> bool:
        return (other.x >= self.x and
                other.y >= self.y and
                other.x + other.width <= self.x + self.width and
                other.y + other.height <= self.y + self.height)

class MaxRectsEngine(NestingEngine):
    """
    Implements the MaxRects algorithm with Manufacturing Constraints.
    """

    def __init__(self):
        super().__init__(name="MaxRects Engine")

    def optimize(self, sheet_template: Sheet, parts: List[Part], constraints: Optional[ManufacturingConstraints] = None) -> NestingResult:
        start_time = time.time()
        
        if constraints is None:
            constraints = ManufacturingConstraints()

        kerf = constraints.kerf
        margin = constraints.margin
        
        remaining_parts = parts[:]
        sheet_results: List[SheetResult] = []
        
        while remaining_parts:
            current_sheet_res = SheetResult(sheet=sheet_template)
            
            # Initial free rectangle is the sheet minus margins
            free_rects: List[Rect] = [Rect(
                margin, margin, 
                sheet_template.width - 2 * margin, 
                sheet_template.height - 2 * margin
            )]
            
            placed_on_this_sheet = []
            
            # Sort remaining parts by area (decreasing)
            remaining_parts.sort(key=lambda p: p.width * p.height, reverse=True)
            
            i = 0
            while i < len(remaining_parts):
                part = remaining_parts[i]
                
                best_rect = None
                best_rotated = False
                min_short_side_fit = float('inf')
                
                # Try all orientations
                orientations = [(part.width, part.height, False)]
                if constraints.allow_rotation and part.width != part.height:
                    orientations.append((part.height, part.width, True))

                for w, h, rotated in orientations:
                    # Account for kerf during placement checks
                    # We need to ensure that the placed part (plus kerf on right and top) fits in the free rect
                    # Actually, a better way is to consider that every part 'occupies' (w + kerf, h + kerf)
                    # except maybe on the boundaries.
                    
                    for rect in free_rects:
                        if rect.width >= w and rect.height >= h:
                            leftover_w = rect.width - w
                            leftover_h = rect.height - h
                            short_side_fit = min(leftover_w, leftover_h)
                            
                            if short_side_fit < min_short_side_fit:
                                min_short_side_fit = short_side_fit
                                best_rect = rect
                                best_rotated = rotated

                if best_rect:
                    # Place part
                    w = part.height if best_rotated else part.width
                    h = part.width if best_rotated else part.height
                    
                    placed_parts_obj = PlacedPart(part=part, x=best_rect.x, y=best_rect.y, is_rotated=best_rotated)
                    placed_on_this_sheet.append(placed_parts_obj)
                    
                    # Split logic: The area 'taken' includes the kerf
                    # We treat the placed part as slightly larger to account for kerf
                    # but only internally for splitting.
                    taken_rect = Rect(best_rect.x, best_rect.y, w + kerf, h + kerf)
                    
                    new_free_rects = []
                    for rect in free_rects:
                        if rect.intersects(taken_rect):
                            new_free_rects.extend(self._split_rect(rect, taken_rect))
                        else:
                            new_free_rects.append(rect)
                    
                    free_rects = self._prune_rects(new_free_rects)
                    remaining_parts.pop(i)
                else:
                    i += 1
            
            if not placed_on_this_sheet:
                if remaining_parts:
                    print(f"Warning: Part {remaining_parts[0].id} cannot fit on a fresh sheet with constraints.")
                    remaining_parts.pop(0)
                continue

            current_sheet_res.placed_parts = placed_on_this_sheet
            current_sheet_res.calculate_metrics()
            sheet_results.append(current_sheet_res)

        return NestingResult(
            sheets=sheet_results,
            total_parts_requested=len(parts),
            total_parts_placed=sum(len(s.placed_parts) for s in sheet_results),
            runtime_seconds=time.time() - start_time
        )

    def _split_rect(self, free_rect: Rect, part_rect: Rect) -> List[Rect]:
        new_rects = []
        if part_rect.y < free_rect.y + free_rect.height and part_rect.y + part_rect.height > free_rect.y:
            if part_rect.x > free_rect.x and part_rect.x < free_rect.x + free_rect.width:
                new_rects.append(Rect(free_rect.x, free_rect.y, part_rect.x - free_rect.x, free_rect.height))
            if part_rect.x + part_rect.width < free_rect.x + free_rect.width:
                new_rects.append(Rect(part_rect.x + part_rect.width, free_rect.y, free_rect.x + free_rect.width - (part_rect.x + part_rect.width), free_rect.height))

        if part_rect.x < free_rect.x + free_rect.width and part_rect.x + part_rect.width > free_rect.x:
            if part_rect.y > free_rect.y and part_rect.y < free_rect.y + free_rect.height:
                new_rects.append(Rect(free_rect.x, free_rect.y, free_rect.width, part_rect.y - free_rect.y))
            if part_rect.y + part_rect.height < free_rect.y + free_rect.height:
                new_rects.append(Rect(free_rect.x, part_rect.y + part_rect.height, free_rect.width, free_rect.y + free_rect.height - (part_rect.y + part_rect.height)))
        return new_rects

    def _prune_rects(self, rects: List[Rect]) -> List[Rect]:
        pruned = []
        for i in range(len(rects)):
            is_contained = False
            for j in range(len(rects)):
                if i != j and rects[j].contains(rects[i]):
                    is_contained = True
                    break
            if not is_contained:
                pruned.append(rects[i])
        return pruned
