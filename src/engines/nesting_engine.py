from abc import ABC, abstractmethod
from typing import List, Optional
from src.models.models import Part, Sheet, NestingResult, ManufacturingConstraints

class NestingEngine(ABC):
    """
    Common interface for all nesting algorithms.
    """
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def optimize(self, sheet_type: Sheet, parts: List[Part], constraints: Optional[ManufacturingConstraints] = None) -> NestingResult:
        """
        Executes nesting optimization. 
        Note: Implementation should handle creating multiple sheets if necessary.
        """
        pass
