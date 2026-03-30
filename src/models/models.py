from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass(frozen=True)
class Part:
    """Represents a rectangular part to be cut from a sheet."""
    id: str
    width: float
    height: float
    name: str = ""
    material: str = ""
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Dimensions must be positive. Got {self.width}x{self.height}")

@dataclass(frozen=True)
class Sheet:
    """Represents a raw plywood or material sheet."""
    id: str
    width: float
    height: float
    material: str = ""

    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError(f"Dimensions must be positive. Got {self.width}x{self.height}")

@dataclass
class PlacedPart:
    """Represents a Part placed on a Sheet at a specific coordinate."""
    part: Part
    x: float
    y: float
    is_rotated: bool = False
    
    @property
    def width(self) -> float:
        return self.part.height if self.is_rotated else self.part.width
        
    @property
    def height(self) -> float:
        return self.part.width if self.is_rotated else self.part.height

@dataclass(frozen=True)
class ManufacturingConstraints:
    """Real-world constraints for the cutting process."""
    kerf: float = 0.0          # Saw blade thickness
    margin: float = 0.0        # Edge margin around the sheet
    allow_rotation: bool = True # Whether parts can be rotated 90 deg
    cost_per_sheet: float = 0.0 # Cost per material sheet
    min_reusable_area: float = 46450.0 # Minimum area (sq mm) to be considered reusable (default ~0.5 sq ft)
    min_reusable_dim: float = 100.0    # Minimum dimension (mm) to be considered reusable

@dataclass
class SheetResult:
    """Result of nesting for a single sheet."""
    sheet: Sheet
    placed_parts: List[PlacedPart] = field(default_factory=list)
    used_area: float = 0.0
    waste_area: float = 0.0
    reusable_waste_area: float = 0.0
    scrap_waste_area: float = 0.0
    reusable_scraps: List[Dict] = field(default_factory=list)
    efficiency: float = 0.0

    def calculate_metrics(self, min_reusable_area: float = 46450.0, min_reusable_dim: float = 100.0):
        sheet_area = self.sheet.width * self.sheet.height
        true_used_area = 0.0
        
        for p in self.placed_parts:
            meta = getattr(p.part, 'metadata', {})
            shape = meta.get('shape', 'RECT').upper()
            w = p.width
            h = p.height
            bbox_area = w * h
            
            # 1. Calculate the true area of the placed shape
            import math
            if shape in ['TRIANGLE', 'RIGHT_TRIANGLE', 'ISOSCELES_TRIANGLE', 'SCALENE_TRIANGLE']:
                true_area = 0.5 * bbox_area
            elif shape == 'CIRCLE':
                true_area = math.pi * ((w/2)**2)
            elif shape == 'SEMI_CIRCLE':
                # BBox is D x D/2. Area is 0.5 * pi * (D/2)^2
                true_area = 0.5 * math.pi * ((w/2)**2)
            elif shape == 'QUARTER_CIRCLE':
                true_area = 0.25 * math.pi * (w**2)
            else:
                true_area = bbox_area
                
            true_used_area += true_area
            
            # 2. Extract Reusable Scraps from the bounding box (specifically for RIGHT_TRIANGLE)
            if shape == 'RIGHT_TRIANGLE':
                leftover_area = bbox_area - true_area
                if leftover_area >= min_reusable_area and min(w, h) >= min_reusable_dim:
                    self.reusable_waste_area += leftover_area
                    self.reusable_scraps.append({
                        "id": f"OFFCUT-{p.part.id}",
                        "type": "RIGHT_TRIANGLE",
                        "x": round(p.x, 2),
                        "y": round(p.y, 2),
                        "width": round(w, 2),
                        "height": round(h, 2),
                        "area": round(leftover_area, 2),
                        "is_offcut": True,
                        "offcut_orientation": p.is_rotated,
                        "offcut_variant": "STANDARD"
                    })
            elif shape in ['ISOSCELES_TRIANGLE', 'TRIANGLE', 'SCALENE_TRIANGLE']:
                offset = 0.5 if shape != 'SCALENE_TRIANGLE' else 0.2
                
                # Left offcut
                w1 = w * offset
                h1 = h
                area1 = 0.5 * w1 * h1
                if area1 >= min_reusable_area and min(w1, h1) >= min_reusable_dim:
                    self.reusable_waste_area += area1
                    self.reusable_scraps.append({
                        "id": f"OFFCUT-L-{p.part.id}",
                        "type": "RIGHT_TRIANGLE",
                        "x": round(p.x, 2),
                        "y": round(p.y, 2),
                        "width": round(w1, 2),
                        "height": round(h1, 2),
                        "area": round(area1, 2),
                        "is_offcut": True,
                        "offcut_variant": "TOP_LEFT"
                    })
                    
                # Right offcut
                w2 = w * (1 - offset)
                h2 = h
                area2 = 0.5 * w2 * h2
                if area2 >= min_reusable_area and min(w2, h2) >= min_reusable_dim:
                    self.reusable_waste_area += area2
                    self.reusable_scraps.append({
                        "id": f"OFFCUT-R-{p.part.id}",
                        "type": "RIGHT_TRIANGLE",
                        "x": round(p.x + w1, 2),
                        "y": round(p.y, 2),
                        "width": round(w2, 2),
                        "height": round(h2, 2),
                        "area": round(area2, 2),
                        "is_offcut": True,
                        "offcut_variant": "TOP_RIGHT"
                    })

        
        self.used_area = true_used_area
        self.waste_area = sheet_area - self.used_area
        # Reusable waste (from free rects) was added to self.reusable_waste_area by the engine already
        self.scrap_waste_area = self.waste_area - self.reusable_waste_area
        self.efficiency = (self.used_area / sheet_area) * 100 if sheet_area > 0 else 0

    @property
    def wastage_percentage(self) -> float:
        return 100.0 - self.efficiency

@dataclass
class NestingResult:
    """Overall result of a nesting operation, possibly covering multiple sheets."""
    sheets: List[SheetResult] = field(default_factory=list)
    total_parts_requested: int = 0
    total_parts_placed: int = 0
    runtime_seconds: float = 0.0
    
    # Store candidates if ran in intelligent mode
    candidates_data: List[Dict] = field(default_factory=list)
    baseline_savings: float = 0.0

    @property
    def total_used_area(self) -> float:
        return sum(s.used_area for s in self.sheets)
    
    @property
    def total_waste_area(self) -> float:
        return sum(s.waste_area for s in self.sheets)
        
    @property
    def total_reusable_waste_area(self) -> float:
        return sum(s.reusable_waste_area for s in self.sheets)
        
    @property
    def total_scrap_waste_area(self) -> float:
        return sum(s.scrap_waste_area for s in self.sheets)
    
    @property
    def overall_efficiency(self) -> float:
        if not self.sheets: return 0.0
        return sum(s.efficiency for s in self.sheets) / len(self.sheets)

    @property
    def wastage_percentage(self) -> float:
        return 100.0 - self.overall_efficiency
