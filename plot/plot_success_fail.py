import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging
from plot.common import log_plot_creation, FIG_SIZE, FONT_SIZE, FONT_SIZE_TITLE, FONT_SIZE_LEGEND, tab20, scan_global_stats, save_plot


def plot_success_fail(root_dir, output_dir):
    """
    Generates separate line charts for each phase.
    """
    df = scan_global_stats(root_dir)
    
    if df.empty:
        logging.warning("No data found for success/fail plot.")
        return

    # Check/Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    phases = ["api-tx-build", "api-read-only"]
    
    # Define styles
    # Colors for contracts
    colors = {
        "erc721": tab20[6],  # Red
        "erc1155": tab20[0]  # Blue
    }
    
    # Line styles for metrics
    styles = {
        "Total": {"linestyle": "-", "marker": "o"},
        "Success": {"linestyle": "--", "marker": "^"},
        "Fail": {"linestyle": ":", "marker": "x"}
    }
    
    # Calculate global max for Y-axis scaling (including error bars)
    max_val = (df["total_requests"] + df.get("total_requests_std", 0).fillna(0)).max()
    margin = max_val * 0.1 if max_val > 0 else 1
    y_max_limit = max_val + margin

    for phase in phases:
        subset = df[df["phase"] == phase]
        
        if subset.empty:
            continue
            
        plt.figure(figsize=FIG_SIZE)
            
        # Get unique contracts
        contracts = subset["contract"].unique()
        
        # Collect all user counts for x-axis
        all_users = sorted(subset["users"].unique())
        
        for contract in contracts:
            contract_data = subset[subset["contract"] == contract].sort_values("users")
            if contract_data.empty:
                continue
                
            users = contract_data["users"]
            
            # Plot Total
            plt.errorbar(
                users, contract_data["total_requests"], 
                yerr=contract_data.get("total_requests_std"),
                label=f"{contract} - Total", 
                color=colors.get(contract, "black"),
                capsize=3,
                **styles["Total"]
            )
            
            # Plot Success
            plt.errorbar(
                users, contract_data["total_success"], 
                yerr=contract_data.get("total_success_std"),
                label=f"{contract} - Success", 
                color=colors.get(contract, "black"),
                capsize=3,
                **styles["Success"]
            )
            
            # Plot Fail
            plt.errorbar(
                users, contract_data["total_fail"], 
                yerr=contract_data.get("total_fail_std"),
                label=f"{contract} - Fail", 
                color=colors.get(contract, "black"),
                capsize=3,
                **styles["Fail"]
            )

        if phase == "api-tx-build":
            op = "Escrita"
        elif phase == "api-read-only":
            op = "Leitura"
        plt.title(f"Quantidade de Requisições ({op})", fontsize=FONT_SIZE_TITLE)
        plt.xlabel("Quantidade de Usuários", fontsize=FONT_SIZE)
        plt.ylabel("Quantidade de Requisições", fontsize=FONT_SIZE)
        plt.ylim(0 - margin, y_max_limit)
        plt.xticks(all_users)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=FONT_SIZE_LEGEND)
        plt.tight_layout()
        
        save_plot(output_dir, f"plot_success_fail_{phase}")
        plt.close()
