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
    efficiency: float = 0.0

    def calculate_metrics(self):
        sheet_area = self.sheet.width * self.sheet.height
        self.used_area = sum(p.part.width * p.part.height for p in self.placed_parts)
        self.waste_area = sheet_area - self.used_area
        # Reusable waste is calculated by the engine and stored in self.reusable_waste_area
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
