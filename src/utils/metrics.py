import time
from typing import List
from src.models.models import NestingResult

class MetricsCalculator:
    """Utility to track and compute performance metrics."""
    
    @staticmethod
    def start_timer():
        return time.time()
    
    @staticmethod
    def stop_timer(start_time: float) -> float:
        return time.time() - start_time

    @staticmethod
    def print_summary(result: NestingResult):
        print("\n" + "="*30)
        print("OPTIMIZATION SUMMARY")
        print("="*30)
        print(f"Algorithm Runtime: {result.runtime_seconds:.4f}s")
        print(f"Sheets Used:       {len(result.sheets)}")
        print(f"Parts Placed:      {result.total_parts_placed} / {result.total_parts_requested}")
        print(f"Overall Efficiency: {result.overall_efficiency:.2f}%")
        print(f"Total Waste Area:   {result.total_waste_area:.2f} mm²")
        print("="*30 + "\n")
