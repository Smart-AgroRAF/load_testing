import os
import numpy as np
import logging
import matplotlib.pyplot as plt

# Internal imports
from plot.common import FIG_SIZE, FONT_SIZE, FONT_SIZE_LEGEND, FONT_SIZE_TITLE, styles, log_plot_creation

def plot_throughput(df, output_dir):
    """
    Generate throughput/RPS vs users plot with error bars.
    
    Args:
        df: DataFrame with columns: erc, users, experiment_type, mean_throughput, std_throughput, count
        output_dir: Directory to save the plot
    """
    if df.empty: return
    plt.rcParams.update({'font.size': FONT_SIZE})
    plt.figure(figsize=FIG_SIZE)
    
    grouped = df.groupby(["erc", "experiment_type"])
    all_users = sorted(df["users"].unique())
    
    for (erc, exp_type), group in grouped:
        style = styles.get((erc, exp_type))
        if not style: continue
        
        subset = group.sort_values("users")
        subset["std_throughput"] = subset["std_throughput"].fillna(0)
        subset["ci"] = 1.96 * subset["std_throughput"] / np.sqrt(subset["count"])
        
        plt.errorbar(
            subset["users"], subset["mean_throughput"], yerr=subset["ci"],
            label=style["label"], color=style["color"], marker=style["marker"], capsize=5
        )
        
    plt.title("Impacto do Número de Usuários na Vazão", fontsize=FONT_SIZE_TITLE)
    plt.xlabel("Quantidade de Usuários")
    plt.ylabel("Vazão (req/s) de Requisições Atendidas com Sucesso")
    plt.xticks(all_users)
    plt.legend(fontsize=FONT_SIZE_LEGEND)
    
    # Calculate balanced padding
    if len(all_users) > 1:
        spread = max(all_users) - min(all_users)
        padding = spread * 0.1
    else:
        padding = max(all_users) * 0.1
        
    plt.xlim(min(all_users) - padding, max(all_users) + padding)
    plt.grid(True)
    plt.tight_layout()
    filename = os.path.join(output_dir, "plot_throughput.png")
    plt.savefig(filename, bbox_inches='tight')
    plt.close()
    log_plot_creation(filename)
