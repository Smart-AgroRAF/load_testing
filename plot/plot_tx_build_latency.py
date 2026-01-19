import os
import math
import matplotlib.pyplot as plt
import logging
from plot.common import log_plot_creation, FIG_SIZE, FONT_SIZE, FONT_SIZE_TITLE, FONT_SIZE_LEGEND, scan_stats_endpoint_files, save_plot

def plot_tx_build_latency(root_dir, output_dir):
    """
    Generates:
    1. Separate line charts for each tx-build endpoint latency (individual files).
    2. Consolidated latency subplot images separated by contract (ERC721 and ERC1155).
    """
    df = scan_stats_endpoint_files(root_dir, phase_filter="api-tx-build")
    
    if df.empty:
        logging.warning("No data found for tx-build routes latency plot.")
        return

    # Check/Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    endpoints = sorted(df["endpoint"].unique())
    
    # Calculate global max for Y-axis scaling (including error bars)
    max_val = (df["mean_duration"] + df["duration_std"].fillna(0)).max()
    margin = max_val * 0.1 if max_val > 0 else 0.1
    y_max_limit = max_val + margin
    y_min_limit = 0 - margin

    # ---------------------------------------------------------
    # 1. Generate INDIVIDUAL plots for each endpoint
    # ---------------------------------------------------------
    
    style = {"linestyle": "-", "marker": "o", "color": "blue"}

    for endpoint in endpoints:
        subset = df[df["endpoint"] == endpoint].sort_values("users")
        
        if subset.empty:
            continue
            
        safe_name = endpoint.strip("/").replace("/", "_")
        
        plt.figure(figsize=FIG_SIZE)
        
        plt.errorbar(
            subset["users"], subset["mean_duration"], yerr=subset["duration_std"],
            label="Latência Média", capsize=5, **style
        )
        
        contract_name = subset["contract"].iloc[0].upper() if not subset.empty else ""
        plt.suptitle(f"Rota de Escrita - {contract_name}", fontsize=FONT_SIZE_TITLE)
        plt.title(endpoint, fontsize=FONT_SIZE_TITLE - 6)
        plt.xlabel("Quantidade de Usuários", fontsize=FONT_SIZE)
        plt.ylabel("Latência (s)", fontsize=FONT_SIZE)
        plt.ylim(y_min_limit, y_max_limit)
        
        all_users = sorted(subset["users"].unique())
        plt.xticks(all_users)
        
        plt.grid(True, linestyle='--', alpha=0.7)
        # plt.legend(fontsize=FONT_SIZE_LEGEND)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        
        save_plot(output_dir, f"plot_tx_build_latency_route_{safe_name}")
        plt.close()

    # ---------------------------------------------------------
    # 2. Generate CONSOLIDATED plots per contract
    # ---------------------------------------------------------
    
    contracts = ["erc721", "erc1155"]
    
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

        # Grid configuration
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
                
            ax.errorbar(ep_data["users"], ep_data["mean_duration"], yerr=ep_data["duration_std"], label="Latência Média", capsize=3, **style)
            
            ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
            ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
            ax.set_ylabel("Latência (s)", fontsize=FONT_SIZE - 2)
            ax.set_ylim(y_min_limit, y_max_limit)
            ax.grid(True, linestyle='--', alpha=0.7)
            # ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
            
            all_users = sorted(ep_data["users"].unique())
            ax.set_xticks(all_users)

        # Hide unused subplots
        for j in range(i + 1, len(axes)):
            fig.delaxes(axes[j])

        plt.suptitle(f"Latência das Rotas de Escrita - {contract.upper()}", fontsize=FONT_SIZE_TITLE, y=1.02)
        plt.tight_layout()
        
        save_plot(output_dir, f"plot_tx_build_latency_{contract}_all", bbox_inches="tight")
        plt.close()

    # ---------------------------------------------------------
    # 3. Generate CONSOLIDATED plot for ALL endpoints (Combined)
    # ---------------------------------------------------------
    
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
    
    num_rows = max(len(erc721_eps), len(erc1155_eps))
    
    if num_rows > 0:
        figsize = (16, 5 * num_rows)
        fig, axes = plt.subplots(num_rows, 2, figsize=figsize, sharex=False, sharey=False)
        
        if num_rows == 1:
            axes = axes.reshape(1, 2)

        # Plot ERC721
        for i, endpoint in enumerate(erc721_eps):
            ax = axes[i, 0]
            ep_data = df[df["endpoint"] == endpoint].sort_values("users")
            
            if not ep_data.empty:
                ax.errorbar(ep_data["users"], ep_data["mean_duration"], yerr=ep_data["duration_std"], label="Latência Média", capsize=3, **style)
                ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
                ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
                ax.set_ylabel("Latência (s)", fontsize=FONT_SIZE - 2)
                ax.set_ylim(y_min_limit, y_max_limit)
                ax.grid(True, linestyle='--', alpha=0.7)
                # ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
                all_users = sorted(ep_data["users"].unique())
                ax.set_xticks(all_users)
        
        # Plot ERC1155
        for i, endpoint in enumerate(erc1155_eps):
            ax = axes[i, 1]
            ep_data = df[df["endpoint"] == endpoint].sort_values("users")
            
            if not ep_data.empty:
                ax.errorbar(ep_data["users"], ep_data["mean_duration"], yerr=ep_data["duration_std"], label="Latência Média", capsize=3, **style)
                ax.set_title(endpoint, fontsize=FONT_SIZE_TITLE - 4)
                ax.set_xlabel("Quantidade de Usuários", fontsize=FONT_SIZE - 2)
                ax.set_ylabel("Latência (s)", fontsize=FONT_SIZE - 2)
                ax.set_ylim(y_min_limit, y_max_limit)
                ax.grid(True, linestyle='--', alpha=0.7)
                # ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
                all_users = sorted(ep_data["users"].unique())
                ax.set_xticks(all_users)

        if len(erc721_eps) < num_rows:
            for r in range(len(erc721_eps), num_rows):
                fig.delaxes(axes[r, 0])
        
        if len(erc1155_eps) < num_rows:
            for r in range(len(erc1155_eps), num_rows):
                fig.delaxes(axes[r, 1])

        plt.suptitle(f"Latência das Rotas de Escrita (Esquerda: ERC721, Direita: ERC1155)", fontsize=FONT_SIZE_TITLE, y=1.02)
        plt.tight_layout()
        
        save_plot(output_dir, "plot_tx_build_latency_all", bbox_inches="tight")
        plt.close()
