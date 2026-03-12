import matplotlib
matplotlib.use('Agg') # Force non-interactive backend for web stability
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
from typing import Optional
from src.models.models import NestingResult, SheetResult, ManufacturingConstraints

class Visualizer:
    """Visualization tool for sheet layouts using Matplotlib."""

    def __init__(self, figsize=(12, 8)):
        self.figsize = figsize

    def _get_random_color(self):
        return (random.random(), random.random(), random.random(), 0.6)

    def plot_result(self, result: NestingResult, constraints: Optional[ManufacturingConstraints] = None, save_path: str = None):
        """Plots all sheets in the result."""
        num_sheets = len(result.sheets)
        if num_sheets == 0:
            print("No sheets to visualize.")
            return

        fig, axes = plt.subplots(num_sheets, 1, figsize=(self.figsize[0], self.figsize[1] * num_sheets))
        if num_sheets == 1:
            axes = [axes]

        for i, sheet_result in enumerate(result.sheets):
            self._plot_single_sheet(axes[i], sheet_result, i+1, constraints)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            print(f"Visualization saved to {save_path}")
            plt.close(fig) # Avoid popping windows in CLI mode
        else:
            plt.show()

    def _plot_single_sheet(self, ax, sheet_result: SheetResult, sheet_idx: int, constraints: Optional[ManufacturingConstraints] = None):
        sheet = sheet_result.sheet
        
        # Draw Sheet Boundary
        rect = patches.Rectangle((0, 0), sheet.width, sheet.height, linewidth=2, edgecolor='black', facecolor='none', label='Sheet boundary')
        ax.add_patch(rect)
        
        # Draw Margins
        if constraints and constraints.margin > 0:
            margin = constraints.margin
            margin_rect = patches.Rectangle(
                (margin, margin), sheet.width - 2*margin, sheet.height - 2*margin, 
                linewidth=1, edgecolor='red', facecolor='none', linestyle='--', alpha=0.5, label='Margin'
            )
            ax.add_patch(margin_rect)

        # Set Plot Limits
        ax.set_xlim(-50, sheet.width + 50)
        ax.set_ylim(-50, sheet.height + 50)
        ax.set_aspect('equal')
        ax.set_title(f"Sheet {sheet_idx}: {sheet.id} ({sheet.width}x{sheet.height}) - Efficiency: {sheet_result.efficiency:.2f}%")

        # Plot Placed Parts
        for p in sheet_result.placed_parts:
            part_color = self._get_random_color()
            part_rect = patches.Rectangle(
                (p.x, p.y), p.width, p.height, 
                linewidth=1, edgecolor='blue', facecolor=part_color
            )
            ax.add_patch(part_rect)
            
            # Label
            rotation_tag = " (R)" if p.is_rotated else ""
            label_text = f"{p.part.id}{rotation_tag}\n{int(p.width)}x{int(p.height)}"
            ax.text(
                p.x + p.width/2, p.y + p.height/2, 
                label_text, 
                horizontalalignment='center', verticalalignment='center',
                fontsize=8, fontweight='bold', color='black', clip_on=True
            )

        ax.grid(True, linestyle='--', alpha=0.5)
        ax.set_xlabel("Width (mm)")
        ax.set_ylabel("Height (mm)")
