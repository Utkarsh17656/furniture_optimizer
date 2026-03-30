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
        # 0.8 alpha or 1.0 to avoid heavy blending, keeping colors bright but distinct from red/green
        return (random.uniform(0.3, 0.9), random.uniform(0.3, 0.9), random.uniform(0.7, 1.0), 1.0)

    def plot_result(self, result: NestingResult, constraints: Optional[ManufacturingConstraints] = None, save_path: str = None, show_scrap_labels: bool = True):
        """Plots all sheets in the result."""
        num_sheets = len(result.sheets)
        if num_sheets == 0:
            print("No sheets to visualize.")
            return

        fig, axes = plt.subplots(num_sheets, 1, figsize=(self.figsize[0], self.figsize[1] * num_sheets))
        if num_sheets == 1:
            axes = [axes]

        for i, sheet_result in enumerate(result.sheets):
            self._plot_single_sheet(axes[i], sheet_result, i+1, constraints, show_scrap_labels)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            print(f"Visualization saved to {save_path}")
            plt.close(fig) # Avoid popping windows in CLI mode
        else:
            plt.show()

    def _plot_single_sheet(self, ax, sheet_result: SheetResult, sheet_idx: int, constraints: Optional[ManufacturingConstraints] = None, show_scrap_labels: bool = True):
        sheet = sheet_result.sheet
        
        # Draw entire sheet as Scrap Waste (Layer 1)
        scrap_bg = patches.Rectangle(
            (0, 0), sheet.width, sheet.height,
            linewidth=0, facecolor='#fff1f2', zorder=1 # Very Light Pink/Red
        )
        ax.add_patch(scrap_bg)

        # Draw Sheet Boundary
        rect = patches.Rectangle((0, 0), sheet.width, sheet.height, linewidth=2, edgecolor='black', facecolor='none', zorder=2)
        ax.add_patch(rect)
        
        # Draw Margins
        if constraints and constraints.margin > 0:
            margin = constraints.margin
            margin_rect = patches.Rectangle(
                (margin, margin), sheet.width - 2*margin, sheet.height - 2*margin, 
                linewidth=1, edgecolor='red', facecolor='none', linestyle='--', alpha=0.5, zorder=2
            )
            ax.add_patch(margin_rect)

        # Draw Reusable Waste Scraps (Layer 2)
        for scrap in getattr(sheet_result, 'reusable_scraps', []):
            sx = scrap.get('x', 0)
            sy = scrap.get('y', 0)
            sw = scrap.get('width', 0)
            sh = scrap.get('height', 0)
            stype = scrap.get('type', 'RECT')
            if stype == 'RIGHT_TRIANGLE' and scrap.get('is_offcut'):
                variant = scrap.get("offcut_variant", "STANDARD")
                if variant == "TOP_LEFT":
                    pts = [[sx, sy], [sx, sy + sh], [sx + sw, sy + sh]]
                elif variant == "TOP_RIGHT":
                    pts = [[sx, sy + sh], [sx + sw, sy + sh], [sx + sw, sy]]
                else: 
                    is_rot = scrap.get('offcut_orientation', False)
                    if not is_rot:
                        pts = [[sx + sw, sy], [sx + sw, sy + sh], [sx, sy + sh]]
                    else:
                        pts = [[sx, sy + sh], [sx + sw, sy], [sx + sw, sy + sh]]
                        
                reusable_rect = patches.Polygon(
                    pts, linewidth=1, edgecolor='#16a34a', facecolor='#bbf7d0', zorder=3 
                )
            else:
                reusable_rect = patches.Rectangle(
                    (sx, sy), sw, sh,
                    linewidth=1, edgecolor='#16a34a', facecolor='#bbf7d0', zorder=3 # Light Green
                )

            ax.add_patch(reusable_rect)
            
            # Label
            label_id = scrap.get("label_id")
            if show_scrap_labels and label_id:
                label_text = f"{label_id}\n{int(sw)}x{int(sh)}"
                font_size = 6
            else:
                label_text = "Reusable"
                font_size = 8
                
            ax.text(
                sx + sw/2, sy + sh/2, 
                label_text, 
                horizontalalignment='center', verticalalignment='center',
                fontsize=font_size, fontweight='bold', color='#14532d', zorder=4, clip_on=True
            )

        # Set Plot Limits
        ax.set_xlim(-50, sheet.width + 50)
        ax.set_ylim(-50, sheet.height + 50)
        ax.set_aspect('equal')
        ax.set_title(f"Sheet {sheet_idx}: {sheet.id} ({sheet.width}x{sheet.height}) - Efficiency: {sheet_result.efficiency:.2f}%")

        # Plot Placed Parts (Layer 3)
        for p in sheet_result.placed_parts:
            part_color = self._get_random_color()
            # Shape-specific drawing
            metadata = getattr(p.part, 'metadata', {})
            shape_type = metadata.get('shape', 'RECT')
            
            # Setup bounding box style based on shape
            if shape_type == 'RECT':
                bbox_facecolor = part_color
                bbox_edgecolor = 'blue'
                bbox_alpha = 1.0
                bbox_ls = '-'
            else:
                bbox_facecolor = 'none'
                bbox_edgecolor = 'gray'
                bbox_alpha = 0.5
                bbox_ls = '--'
                
            part_rect = patches.Rectangle(
                (p.x, p.y), p.width, p.height, 
                linewidth=1, edgecolor=bbox_edgecolor, facecolor=bbox_facecolor, 
                linestyle=bbox_ls, alpha=bbox_alpha, zorder=5
            )
            ax.add_patch(part_rect)
            
            if shape_type == 'CIRCLE':
                dia = metadata.get('diameter', metadata.get('radius', min(p.width, p.height)/2) * 2)
                circle = patches.Circle(
                    (p.x + p.width/2, p.y + p.height/2), dia/2,
                    linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6
                )
                ax.add_patch(circle)
            elif shape_type in ['TRIANGLE', 'ISOSCELES_TRIANGLE']:
                base = metadata.get('breadth', metadata.get('base', p.width))
                height = metadata.get('height', p.height)
                # Isosceles: point at top center
                pts = [[p.x, p.y], [p.x + p.width, p.y], [p.x + p.width/2, p.y + p.height]]
                triangle = patches.Polygon(pts, linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6)
                ax.add_patch(triangle)
            elif shape_type == 'RIGHT_TRIANGLE':
                # Right Triangle: point at (left, bottom), (right, bottom), (left, top)
                if not p.is_rotated:
                    pts = [[p.x, p.y], [p.x + p.width, p.y], [p.x, p.y + p.height]]
                else:
                    pts = [[p.x, p.y], [p.x, p.y + p.height], [p.x + p.width, p.y]] # rotated interpretation
                triangle = patches.Polygon(pts, linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6)
                ax.add_patch(triangle)
            elif shape_type == 'SCALENE_TRIANGLE':
                # Scalene: arbitrary top point, e.g., 20% along width
                pts = [[p.x, p.y], [p.x + p.width, p.y], [p.x + p.width * 0.2, p.y + p.height]]
                triangle = patches.Polygon(pts, linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6)
                ax.add_patch(triangle)
            elif shape_type == 'SEMI_CIRCLE':
                dia = metadata.get('diameter', p.width)
                # Semi-circle resting on the bottom edge of the bounding box
                # Center is middle of the bottom edge, radius is dia/2
                semi_circle = patches.Wedge(
                    (p.x + p.width/2, p.y), dia/2, 0, 180,
                    linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6
                )
                ax.add_patch(semi_circle)
            elif shape_type == 'QUARTER_CIRCLE':
                radius = metadata.get('radius', p.width)
                # Quarter-circle resting in the bottom-left corner
                # Center is bottom-left corner, radius is radius
                quarter_circle = patches.Wedge(
                    (p.x, p.y), radius, 0, 90,
                    linewidth=1, edgecolor='blue', facecolor=part_color, zorder=6
                )
                ax.add_patch(quarter_circle)

            # Label
            rotation_tag = " (R)" if p.is_rotated else ""
            
            if shape_type == 'CIRCLE':
                dim_str = f"Ø{int(metadata.get('diameter', p.width))}"
                label_prefix = "CIRCLE"
            elif shape_type in ['TRIANGLE', 'ISOSCELES_TRIANGLE']:
                dim_str = f"{int(p.width)}x{int(p.height)}"
                label_prefix = "ISO_TRI" if shape_type == 'ISOSCELES_TRIANGLE' else "TRIANGLE"
            elif shape_type == 'RIGHT_TRIANGLE':
                dim_str = f"{int(p.width)}x{int(p.height)}"
                label_prefix = "RT_TRI"
            elif shape_type == 'SCALENE_TRIANGLE':
                dim_str = f"{int(p.width)}x{int(p.height)}"
                label_prefix = "SCAL_TRI"
            elif shape_type == 'SEMI_CIRCLE':
                dim_str = f"Ø{int(metadata.get('diameter', p.width))}"
                label_prefix = "SEMI_CIRCLE"
            elif shape_type == 'QUARTER_CIRCLE':
                dim_str = f"R{int(metadata.get('radius', p.width))}"
                label_prefix = "QUARTER_C"
            else:
                dim_str = f"{int(p.width)}x{int(p.height)}"
                label_prefix = "RECT"

            label_text = f"{label_prefix}_{p.part.id}{rotation_tag}\n({dim_str})"
            
            ax.text(
                p.x + p.width/2, p.y + p.height/2, 
                label_text, 
                horizontalalignment='center', verticalalignment='center',
                fontsize=7, fontweight='bold', color='black', clip_on=True, zorder=10
            )

        ax.grid(True, linestyle='--', alpha=0.5, zorder=0)
        ax.set_xlabel("Width (mm)")
        ax.set_ylabel("Height (mm)")
        
        # Custom Legend
        import matplotlib.patches as mpatches
        legend_elements = [
            mpatches.Patch(facecolor='none', edgecolor='black', linewidth=2, label='Sheet boundary'),
            mpatches.Patch(facecolor='none', edgecolor='blue', linewidth=1, label='Placed Part'),
            mpatches.Patch(facecolor='#bbf7d0', edgecolor='#16a34a', linewidth=1, label='Reusable Waste'),
            mpatches.Patch(facecolor='#fecaca', edgecolor='none', label='Scrap Waste')
        ]
        if constraints and constraints.margin > 0:
            legend_elements.append(mpatches.Patch(facecolor='none', edgecolor='red', linestyle='--', label='Margin'))
            
        ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.25, 1.0))
