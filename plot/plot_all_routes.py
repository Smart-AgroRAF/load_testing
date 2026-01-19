# import os
# import math
# import numpy as np
# import pandas as pd
# import matplotlib.pyplot as plt
# import logging
# from plot.common import log_plot_creation, FIG_SIZE, FONT_SIZE, FONT_SIZE_TITLE, FONT_SIZE_LEGEND, scan_stats_endpoint_files

# def plot_all_routes_quantity(root_dir, output_dir):
#     """
#     Generates a consolidated image with two subplots (ERC721 and ERC1155).
#     Each subplot shows the AGGREGATED quantity for Read vs Write routes.
#     """
#     df = scan_stats_endpoint_files(root_dir, phase_filter=None)
    
#     if df.empty:
#         logging.warning("No data found for all routes quantity plot.")
#         return

#     os.makedirs(output_dir, exist_ok=True)
    
#     # Aggregating: Group by contract, users, and phase
#     # Then sum the counts
#     agg_df = df.groupby(["contract", "users", "phase"]).agg({
#         "total_requests": "sum",
#         "total_success": "sum",
#         "total_fail": "sum",
#         "total_requests_std": lambda x: np.sqrt((x**2).sum()) # Propagation of error (sum of variances)
#     }).reset_index()

#     # Calculate global max for Y-axis scaling
#     max_val = (agg_df["total_requests"] + agg_df["total_requests_std"].fillna(0)).max()
#     margin = max_val * 0.1 if max_val > 0 else 1
#     y_max_limit = max_val + margin
#     y_min_limit = 0 - margin

#     styles = {
#         "api-read-only": {"label_prefix": "Leitura", "color_total": "blue", "marker": "o"},
#         "api-tx-build": {"label_prefix": "Escrita", "color_total": "orange", "marker": "s"}
#     }

#     contracts = sorted(agg_df["contract"].unique())
#     fig, axes = plt.subplots(1, len(contracts), figsize=(16, 6), sharey=True)
#     if len(contracts) == 1: axes = [axes]

#     for i, contract in enumerate(contracts):
#         ax = axes[i]
#         c_data = agg_df[agg_df["contract"] == contract]
        
#         for phase in ["api-read-only", "api-tx-build"]:
#             p_data = c_data[c_data["phase"] == phase].sort_values("users")
#             if not p_data.empty:
#                 style = styles.get(phase, {"label_prefix": phase, "color_total": "grey", "marker": "x"})
#                 ax.errorbar(p_data["users"], p_data["total_requests"], yerr=p_data["total_requests_std"], 
#                             label=f"Total {style['label_prefix']}", color=style["color_total"], 
#                             marker=style["marker"], capsize=5)
#                 # Success/Fail as dashed/dotted
#                 ax.plot(p_data["users"], p_data["total_success"], linestyle="--", alpha=0.6, color=style["color_total"])
#                 ax.plot(p_data["users"], p_data["total_fail"], linestyle=":", alpha=0.6, color=style["color_total"])

#         ax.set_title(contract.upper(), fontsize=FONT_SIZE_TITLE - 2)
#         ax.set_xlabel("Usuários", fontsize=FONT_SIZE)
#         if i == 0: ax.set_ylabel("Requisições", fontsize=FONT_SIZE)
#         ax.set_ylim(y_min_limit, y_max_limit)
#         ax.grid(True, linestyle='--', alpha=0.7)
#         ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
#         ax.set_xticks(sorted(agg_df["users"].unique()))

#     plt.suptitle("Quantidade de Requisições - Média das Rotas", fontsize=FONT_SIZE_TITLE, y=1.05)
#     plt.tight_layout()
#     filename = "plot_all_routes_quantity_all.png"
#     filepath = os.path.join(output_dir, filename)
#     plt.savefig(filepath, bbox_inches="tight")
#     plt.close()
#     log_plot_creation(filepath)

# def plot_all_routes_latency(root_dir, output_dir):
#     """
#     Generates a consolidated image with two subplots (ERC721 and ERC1155).
#     Each subplot shows the MEAN latency for all Read vs Write routes.
#     """
#     df = scan_stats_endpoint_files(root_dir, phase_filter=None)
    
#     if df.empty:
#         logging.warning("No data found for all routes latency plot.")
#         return

#     os.makedirs(output_dir, exist_ok=True)
    
#     # Aggregating: Group by contract, users, and phase
#     # Then average the mean durations
#     agg_df = df.groupby(["contract", "users", "phase"]).agg({
#         "mean_duration": "mean",
#         "duration_std": "mean" # Simplification: mean of standard deviations
#     }).reset_index()

#     # Calculate global max for Y-axis scaling
#     max_val = (agg_df["mean_duration"] + agg_df["duration_std"].fillna(0)).max()
#     margin = max_val * 0.1 if max_val > 0 else 0.1
#     y_max_limit = max_val + margin
#     y_min_limit = 0 - margin

#     styles = {
#         "api-read-only": {"label": "Média Leitura", "color": "blue", "marker": "o"},
#         "api-tx-build": {"label": "Média Escrita", "color": "orange", "marker": "s"}
#     }

#     contracts = sorted(agg_df["contract"].unique())
#     fig, axes = plt.subplots(1, len(contracts), figsize=(16, 6), sharey=True)
#     if len(contracts) == 1: axes = [axes]

#     for i, contract in enumerate(contracts):
#         ax = axes[i]
#         c_data = agg_df[agg_df["contract"] == contract]
        
#         for phase in ["api-read-only", "api-tx-build"]:
#             p_data = c_data[c_data["phase"] == phase].sort_values("users")
#             if not p_data.empty:
#                 style = styles.get(phase, {"label": phase, "color": "grey", "marker": "x"})
#                 ax.errorbar(p_data["users"], p_data["mean_duration"], yerr=p_data["duration_std"], 
#                             label=style["label"], color=style["color"], marker=style["marker"], capsize=5)

#         ax.set_title(contract.upper(), fontsize=FONT_SIZE_TITLE - 2)
#         ax.set_xlabel("Usuários", fontsize=FONT_SIZE)
#         if i == 0: ax.set_ylabel("Latência (s)", fontsize=FONT_SIZE)
#         ax.set_ylim(y_min_limit, y_max_limit)
#         ax.grid(True, linestyle='--', alpha=0.7)
#         ax.legend(fontsize=FONT_SIZE_LEGEND - 2)
#         ax.set_xticks(sorted(agg_df["users"].unique()))

#     plt.suptitle("Latência - Média de Todas as Rotas", fontsize=FONT_SIZE_TITLE, y=1.05)
#     plt.tight_layout()
#     filename = "plot_all_routes_latency_all.png"
#     filepath = os.path.join(output_dir, filename)
#     plt.savefig(filepath, bbox_inches="tight")
#     plt.close()
#     log_plot_creation(filepath)
