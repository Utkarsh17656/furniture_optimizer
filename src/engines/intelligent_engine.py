import time
import random
import copy
from typing import List, Optional, Dict, Tuple
from src.engines.nesting_engine import NestingEngine
from src.engines.maxrects_engine import MaxRectsEngine
from src.engines.shelf_engine import ShelfNestingEngine
from src.engines.shape_aware_engine import ShapeAwareEngine
from src.models.models import Part, Sheet, NestingResult, ManufacturingConstraints

class SolutionGenerator:
    """Generates multiple candidate layouts using different algorithms and permutations."""
    def __init__(self):
        self.engines = {
            "MaxRects": MaxRectsEngine(),
            "Shelf": ShelfNestingEngine(),
            "ShapeAware": ShapeAwareEngine()
        }

    def generate_candidates(self, sheet_type: Sheet, parts: List[Part], constraints: ManufacturingConstraints) -> List[Tuple[NestingResult, str]]:
        candidates = []
        
        # We will try the following sorting strategies
        strategies = [
            ("Area Descending", lambda p: p.width * p.height, True),
            ("Height Descending", lambda p: p.height, True),
            ("Width Descending", lambda p: p.width, True),
        ]
        
        # Try both engines
        for engine_name, engine in self.engines.items():
            for strategy_name, sort_key, rev in strategies:
                ordered_parts = sorted(parts, key=sort_key, reverse=rev)
                
                # Test with rotations globally configured
                res = engine.optimize(sheet_type, copy.deepcopy(ordered_parts), constraints)
                candidates.append((res, f"{engine_name} - {strategy_name}"))
                
                # If constraints allow rotation, also try forcing NO rotation 
                # (sometimes heuristics pack better without rotation if parts are uniform)
                if constraints.allow_rotation:
                    strict_constraints = ManufacturingConstraints(
                        kerf=constraints.kerf,
                        margin=constraints.margin,
                        allow_rotation=False,
                        cost_per_sheet=constraints.cost_per_sheet
                    )
                    res_no_rot = engine.optimize(sheet_type, copy.deepcopy(ordered_parts), strict_constraints)
                    candidates.append((res_no_rot, f"{engine_name} - {strategy_name} (No Rotation)"))

        # Let's add a few randomized permutations to escape local minima
        random.seed(42)  # For deterministic behavior if needed, or remove for true random
        for i in range(5):
            shuffled_parts = parts[:]
            random.shuffle(shuffled_parts)
            for engine_name, engine in self.engines.items():
                res = engine.optimize(sheet_type, copy.deepcopy(shuffled_parts), constraints)
                candidates.append((res, f"{engine_name} - Randomized {i+1}"))
                
        return candidates

class Evaluator:
    """Scores a NestingResult based on metrics (sheets used, wastage, cost)."""
    @staticmethod
    def calculate_cost(result: NestingResult, cost_per_sheet: float) -> Tuple[float, float]:
        sheets_count = len(result.sheets)
        total_material_cost = sheets_count * cost_per_sheet
        
        # Waste cost is proportional to the wastage percentage
        # A sheet costs `cost_per_sheet`, so waste cost = cost_per_sheet * waste_area / sheet_area
        waste_cost = 0.0
        for s in result.sheets:
            sheet_area = s.sheet.width * s.sheet.height
            if sheet_area > 0:
                fraction_wasted = s.waste_area / sheet_area
                waste_cost += fraction_wasted * cost_per_sheet
                
        return total_material_cost, waste_cost

    @staticmethod
    def score(result: NestingResult) -> float:
        # A lower score is better.
        # Primary: Number of sheets (heavily weighted)
        # Secondary: Total waste area (which depends on number of sheets)
        # Tertiary: Overall efficiency (to break ties by rewarding tighter baseline packing)
        # Note: We subtract efficiency because higher efficiency is better
        score = len(result.sheets) * 1000000 + result.total_waste_area - (result.overall_efficiency * 10)
        return score

class Selector:
    """Selects the best layout from candidate solutions."""
    @staticmethod
    def select_best(candidates: List[Tuple[NestingResult, str]]) -> Tuple[NestingResult, str]:
        # Filter out candidates that didn't place all parts
        # If none placed all parts, we just pick the best score
        max_placed = max([c[0].total_parts_placed for c in candidates] + [0])
        valid_candidates = [c for c in candidates if c[0].total_parts_placed == max_placed]
        
        if not valid_candidates:
            valid_candidates = candidates
            
        return min(valid_candidates, key=lambda c: Evaluator.score(c[0]))

class Reporter:
    """Packages the selected layout with comparison metrics."""
    @staticmethod
    def generate_report(best_result: NestingResult, best_name: str, all_candidates: List[Tuple[NestingResult, str]], cost_per_sheet: float) -> NestingResult:
        candidate_reports = []
        for res, name in all_candidates:
            mat_cost, waste_cost = Evaluator.calculate_cost(res, cost_per_sheet)
            candidate_reports.append({
                "algorithm": name,
                "sheets": len(res.sheets),
                "utilization": res.overall_efficiency,
                "wastage": res.wastage_percentage,
                "material_cost": mat_cost,
                "waste_cost": waste_cost,
                "score": Evaluator.score(res)
            })
            
        unique_reports = []
        seen = set()
        for c in sorted(candidate_reports, key=lambda x: x['score']):
            sig = (c['sheets'], round(c['utilization'], 2), c['algorithm'])
            if sig not in seen:
                seen.add(sig)
                unique_reports.append(c)
                
        best_result.candidates_data = unique_reports
        
        baseline = next((c for c in unique_reports if "MaxRects - Area Descending" in c['algorithm']), None)
        if baseline:
            best_mat_cost, _ = Evaluator.calculate_cost(best_result, cost_per_sheet)
            best_result.baseline_savings = baseline['material_cost'] - best_mat_cost
        
        return best_result

class IntelligentEngine(NestingEngine):
    """
    Intelligent optimization engine using multiple strategies.
    Implements Phase 1, Phase 5, Phase 6 goals.
    """
    def __init__(self):
        super().__init__(name="Intelligent Multi-Solution Engine")
        self.generator = SolutionGenerator()
        
    def optimize(self, sheet_template: Sheet, parts: List[Part], constraints: Optional[ManufacturingConstraints] = None) -> NestingResult:
        start_time = time.time()
        
        if constraints is None:
            constraints = ManufacturingConstraints()
            
        print(f"Generating multiple candidate solutions... (Input: {len(parts)} parts)")

        # 1. Generate solutions
        candidates = self.generator.generate_candidates(sheet_template, parts, constraints)
        
        # 2. Add evaluator & selector
        best_result, best_name = Selector.select_best(candidates)
        
        # 3. Report
        final_result = Reporter.generate_report(best_result, best_name, candidates, constraints.cost_per_sheet)
        final_result.runtime_seconds = time.time() - start_time
        
        # Overwrite engine name for UI output
        self.name = f"Intelligent ({best_name})"
        
        return final_result
