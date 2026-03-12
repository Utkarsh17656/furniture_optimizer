import matplotlib.pyplot as plt
import os

def plot_scalability_results():
    # Data from Phase 6 experiments
    sizes = [20, 50, 100, 200]
    shelf_util = [57.87, 66.80, 74.46, 82.63]
    maxrects_util = [86.81, 80.16, 82.74, 86.98]
    
    plt.figure(figsize=(10, 6))
    plt.plot(sizes, shelf_util, marker='o', linestyle='-', color='blue', label='Shelf Engine', linewidth=2)
    plt.plot(sizes, maxrects_util, marker='s', linestyle='-', color='green', label='MaxRects Engine', linewidth=2)
    
    plt.title('Algorithm Scalability: Material Utilization vs. Part Count', fontsize=14, fontweight='bold')
    plt.xlabel('Number of Parts', fontsize=12)
    plt.ylabel('Overall Efficiency (%)', fontsize=12)
    plt.xticks(sizes)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    artifact_dir = r"C:\Users\Utkarsh Yadav\.gemini\antigravity\brain\540781f6-e5ad-47f1-b1cd-b95e67aa3ca7"
    save_path = os.path.join(artifact_dir, "scalability_benchmark.png")
    
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Benchmark chart saved to {save_path}")

if __name__ == "__main__":
    plot_scalability_results()
