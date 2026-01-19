import os
import matplotlib.pyplot as plt
import logging
from .common import scan_global_stats, log_plot_creation, styles, FONT_SIZE, FONT_SIZE_LEGEND, FONT_SIZE_TITLE, save_plot

def plot_rps_comparison(root_dir, output_dir):
    """
    Generate Global RPS comparison plot (RPS vs Users).
    
    Args:
        root_dir: Directory containing test results
        output_dir: Directory to save the plot
    """
    df = scan_global_stats(root_dir)
    
    if df.empty:
        logging.warning("No data found for RPS comparison plot.")
        return

    plt.figure(figsize=(10, 8))
    
    # Iterate over defined styles to ensure order and consistency
    # styles keys are (contract, phase)
    # We might have data that matches these keys
    
    # We can also iterate over unique combinations in DF, 
    # but using 'styles' ensures we use the predefined colors/labels.
    
    plotted_any = False
    
    for (contract, phase), style in styles.items():
        subset = df[(df["contract"] == contract) & (df["phase"] == phase)]
        
        if subset.empty:
            continue
            
        subset = subset.sort_values("users")
        
        # Plot
        plt.errorbar(
            subset["users"], 
            subset["rps"], 
            yerr=subset.get("rps_std"), # Use std if available
            label=style["label"], 
            color=style["color"], 
            marker=style["marker"],
            linestyle='-', 
            linewidth=2,
            markersize=8,
            capsize=5
        )
        plotted_any = True

    if not plotted_any:
        logging.warning("No matching data found for RPS plot styles.")
        return

    plt.xlabel("Quantidade de Usuários", fontsize=FONT_SIZE)
    plt.ylabel("Global RPS", fontsize=FONT_SIZE)
    plt.title("RPS Comparison by User Load", fontsize=FONT_SIZE_TITLE)
    plt.legend(fontsize=FONT_SIZE_LEGEND)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Ensure x-axis integers
    all_users = sorted(df["users"].unique())
    plt.xticks(all_users, fontsize=FONT_SIZE)
    plt.yticks(fontsize=FONT_SIZE)

    plt.tight_layout()
    
    save_plot(output_dir, "global_rps_comparison")
    plt.close()
