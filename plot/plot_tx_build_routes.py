import os
import math
import numpy as np
import matplotlib.pyplot as plt
import logging
from plot.common import log_plot_creation, FIG_SIZE, FONT_SIZE, FONT_SIZE_TITLE, FONT_SIZE_LEGEND, scan_stats_endpoint_files

def plot_tx_build_routes(root_dir, output_dir):
    """
    Generates:
    1. Separate line charts for each tx-build endpoint (individual files).
    2. Consolidated subplot images separated by contract (ERC721 and ERC1155).
    3. Consolidated subplot image for all contracts combined.
    """
    # Use scan_stats_endpoint_files to read consolidated stats (avoids duplicate points from repetitions)
    df = scan_stats_endpoint_files(root_dir, phase_filter="api-tx-build")
    
    if df.empty:
        logging.warning("No data found for tx-build routes plot.")
        return

    # Check/Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Calculate global max for Y-axis scaling
    max_requests = df["total_requests"].max()
    margin = max_requests * 0.1 if max_requests > 0 else 1
    y_max_limit = max_requests + margin
    y_min_limit = 0 - margin
    
    endpoints = sorted(df["endpoint"].unique())
    
    # ---------------------------------------------------------
    # 1. Generate INDIVIDUAL plots for each endpoint
    # ---------------------------------------------------------
    
    metric_colors = {
        "Total": "blue",
        "Success": "green",
        "Fail": "red"
    }
    
    steps_styles = {
        "Total": {"linestyle": "-", "marker": "o"},
        "Success": {"linestyle": "--", "marker": "^"},
        "Fail": {"linestyle": ":", "marker": "x"}
    }

    for endpoint in endpoints:
        subset = df[df["endpoint"] == endpoint].sort_values("users")
        
        if subset.empty:
            continue
            
        safe_name = endpoint.strip("/").replace("/", "_")
        
        plt.figure(figsize=FIG_SIZE)
        
        plt.errorbar(
            subset["users"], subset["total_requests"], yerr=subset["total_requests_std"],
            label="Total", color=metric_colors["Total"], capsize=5, **steps_styles["Total"]
        )
        plt.errorbar(
            subset["users"], subset["total_success"], yerr=subset["total_success_std"],
            label="Success", color=metric_colors["Success"], capsize=5, **steps_styles["Success"]
        )
        plt.errorbar(
            subset["users"], subset["total_fail"], yerr=subset["total_fail_std"],
            label="Fail", color=metric_colors["Fail"], capsize=5, **steps_styles["Fail"]
        )
        
        plt.title(f"Rotas de Escrita: {endpoint}", fontsize=FONT_SIZE_TITLE)
        plt.xlabel("Quantidade de Usuários", fontsize=FONT_SIZE)
        plt.ylabel("Quantidade de Requisições", fontsize=FONT_SIZE)
        plt.ylim(y_min_limit, y_max_limit)
        
        all_users = sorted(subset["users"].unique())
        plt.xticks(all_users)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend(fontsize=FONT_SIZE_LEGEND)
        plt.tight_layout()
        
        filename = f"plot_tx_build_route_{safe_name}.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath)
        plt.close()
        
        log_plot_creation(filepath)

    # ---------------------------------------------------------
    # 2. Generate CONSOLIDATED plots per contract
    # ---------------------------------------------------------
    
    contracts = ["erc721", "erc1155"]
    
    # Common subplot styles
    subplot_styles = {
        "Total": {"linestyle": "-", "marker": "o", "color": "blue"},
        "Success": {"linestyle": "--", "marker": "^", "color": "green"},
        "Fail": {"linestyle": ":", "marker": "x", "color": "red"}
    }
    
    for contract in contracts:
        subset_df = df[df["contract"].str.lower() == contract]
        
        if subset_df.empty:
             subset_df = df[df["endpoint"].str.contains(contract, case=False)]

        if subset_df.empty:
            continue
            
        contract_endpoints = sorted(subset_df["endpoint"].unique())
        num_endpoints = len(contract_endpoints)
        
        if num_endpoints == 0:
            continue

        cols = 2
        rows = math.ceil(num_endpoints / cols)
        figsize = (16, 5 * rows)
        
        fig, axes = plt.subplots(rows, cols, figsize=figsize, sharex=False, sharey=False)
        
        if num_endpoints == 1:
            axes = [axes]
        else:
            axes = axes.flatten()

        for i, endpoint in enumerate(contract_endpoints):
            ax = axes[i]
            ep_data = subset_df[subset_df["endpoint"] == endpoint].sort_values("users")
            
            if ep_data.empty:
                continue
                
            ax.errorbar(ep_data["users"], ep_data["total_requests"], yerr=ep_data["total_requests_std"], label="Total", capsize=3, **subplot_styles["Total"])
            ax.errorbar(ep_data["users"], ep_data["total_success"], yerr=ep_data["total_success_std"], label="Success", capsize=3, **subplot_styles["Success"])
            ax.errorbar(ep_data["users"], ep_data["total_fail"], yerr=ep_data["total_fail_std"], label="Fail", capsize=3, **subplot_styles["Fail"])
            
            ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
            ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
            ax.set_ylabel("Quantidade de Requisições", fontsize=FONT_SIZE - 2)
            ax.set_ylim(y_min_limit, y_max_limit)
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
            
            all_users = sorted(ep_data["users"].unique())
            ax.set_xticks(all_users)

        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        plt.suptitle(f"Routas de Escrita - {contract.upper()}", fontsize=FONT_SIZE_TITLE, y=1.02)
        plt.tight_layout()
        
        filename = f"plot_tx_build_routes_{contract}_all.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        
        log_plot_creation(filepath)

    # ---------------------------------------------------------
    # 3. Generate CONSOLIDATED plot for ALL endpoints (Combined)
    #    Column 0: ERC721, Column 1: ERC1155
    # ---------------------------------------------------------
    
    # Separate endpoints by contract type
    erc721_eps = []
    erc1155_eps = []
    
    all_endpoints = sorted(df["endpoint"].unique())
    
    for ep in all_endpoints:
        if "erc721" in ep.lower():
            erc721_eps.append(ep)
        elif "erc1155" in ep.lower():
            erc1155_eps.append(ep)
    
    erc721_eps.sort()
    erc1155_eps.sort()
    
    # Determine grid size
    num_rows = max(len(erc721_eps), len(erc1155_eps))
    
    if num_rows > 0:
        figsize = (16, 5 * num_rows)
        # Always 2 columns
        fig, axes = plt.subplots(num_rows, 2, figsize=figsize, sharex=False, sharey=False)
        
        # Ensure axes is 2D array even if num_rows=1
        if num_rows == 1:
            axes = np.array(axes).reshape(1, 2)

        # Plot ERC721 (Left Column, index 0)
        for i, endpoint in enumerate(erc721_eps):
            ax = axes[i, 0]
            ep_data = df[df["endpoint"] == endpoint].sort_values("users")
            
            if not ep_data.empty:
                ax.errorbar(ep_data["users"], ep_data["total_requests"], yerr=ep_data["total_requests_std"], label="Total", capsize=3, **subplot_styles["Total"])
                ax.errorbar(ep_data["users"], ep_data["total_success"], yerr=ep_data["total_success_std"], label="Success", capsize=3, **subplot_styles["Success"])
                ax.errorbar(ep_data["users"], ep_data["total_fail"], yerr=ep_data["total_fail_std"], label="Fail", capsize=3, **subplot_styles["Fail"])
                
                ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
                ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
                ax.set_ylabel("Quantidade de Requisições", fontsize=FONT_SIZE - 2)
                ax.set_ylim(y_min_limit, y_max_limit)
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
                
                all_users = sorted(ep_data["users"].unique())
                ax.set_xticks(all_users)
        
        # Plot ERC1155 (Right Column, index 1)
        for i, endpoint in enumerate(erc1155_eps):
            ax = axes[i, 1]
            ep_data = df[df["endpoint"] == endpoint].sort_values("users")
            
            if not ep_data.empty:
                ax.errorbar(ep_data["users"], ep_data["total_requests"], yerr=ep_data["total_requests_std"], label="Total", capsize=3, **subplot_styles["Total"])
                ax.errorbar(ep_data["users"], ep_data["total_success"], yerr=ep_data["total_success_std"], label="Success", capsize=3, **subplot_styles["Success"])
                ax.errorbar(ep_data["users"], ep_data["total_fail"], yerr=ep_data["total_fail_std"], label="Fail", capsize=3, **subplot_styles["Fail"])
                
                ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
                ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
                ax.set_ylabel("Quantidade de Requisições", fontsize=FONT_SIZE - 2)
                ax.set_ylim(y_min_limit, y_max_limit)
                ax.grid(True, linestyle='--', alpha=0.7)
                ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
                
                all_users = sorted(ep_data["users"].unique())
                ax.set_xticks(all_users)

        # Hide empty subplots
        if len(erc721_eps) < num_rows:
            for r in range(len(erc721_eps), num_rows):
                fig.delaxes(axes[r, 0])
        
        if len(erc1155_eps) < num_rows:
            for r in range(len(erc1155_eps), num_rows):
                fig.delaxes(axes[r, 1])

        plt.suptitle(f"Routas de Escrita (Esquerda: ERC721, Direita: ERC1155)", fontsize=FONT_SIZE_TITLE, y=1.02)
        plt.tight_layout()
        
        filename = "plot_tx_build_routes_all.png"
        filepath = os.path.join(output_dir, filename)
        plt.savefig(filepath, bbox_inches="tight")
        plt.close()
        
        log_plot_creation(filepath)
