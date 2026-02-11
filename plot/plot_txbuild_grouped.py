import os
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

# Internal imports
from .common import FIG_SIZE, FONT_SIZE, FONT_SIZE_LEGEND, FONT_SIZE_TITLE, convert_users_to_int, log_plot_creation, save_plot

def create_txbuild_grouped_plot(root_dir, output_dir, use_log_scale=False):
    """
    Creates a grouped bar plot (not stacked) with optional logarithmic Y axis.
    Displays components side-by-side for easier magnitude comparison.
    
    Args:
        root_dir: Directory containing test results
        output_dir: Directory to save the plot
        use_log_scale: If True, use logarithmic scale for Y axis
    """
    data = []
    queue_data = []

    # 1. Scan logic (Reused to ensure consistency)
    for root, dirs, files in os.walk(root_dir):
        # Look for out*.csv (out.csv, out_rep-1.csv, etc.)
        output_files = [f for f in files if f.startswith("out") and f.endswith(".csv")]

        if not output_files or "api-tx-build" not in root:
            continue

        parent_dir = os.path.dirname(root)
        args_path = os.path.join(parent_dir, "args_run.json")
        if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")
        
        if os.path.exists(args_path):
            try:
                with open(args_path, 'r') as f:
                    args_run = json.load(f)
                users = convert_users_to_int(args_run.get('users', 0))
                erc_type = args_run.get('contract', 'unknown')
                
                for out_file in output_files:
                    df = pd.read_csv(os.path.join(root, out_file))
                    
                    if df.empty:
                        continue

                    # Success Filtering: Only include requests where TX-BLOCK was successful
                    if 'status' in df.columns and 'task' in df.columns:
                        success_requests = df[(df['task'] == 'TX-BLOCK') & (df['status'] == 'success')][['user_id', 'request']]
                        df_success = df.merge(success_requests, on=['user_id', 'request'])
                    else:
                        df_success = df

                    if df_success.empty:
                        continue

                    for task in ['API-TX-BUILD', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']:
                        task_data = df_success[df_success['task'] == task]
                        if not task_data.empty:
                            data.append({
                                "erc": erc_type, "users": users, "task": task, "mean": task_data['duration'].mean()
                            })
                    
                    full_data = df_success[df_success['task'] == 'FULL']
                    api_data = df_success[df_success['task'] == 'API-TX-BUILD']
                    tx_build = df_success[df_success['task'] == 'TX-BUILD']
                    tx_sign = df_success[df_success['task'] == 'TX-SIGN']
                    tx_send = df_success[df_success['task'] == 'TX-SEND']
                    
                    if not full_data.empty and not api_data.empty and not tx_build.empty and not tx_send.empty:
                        merged = pd.merge(full_data[['user_id', 'request', 'duration']], 
                                        api_data[['user_id', 'request', 'duration']], on=['user_id', 'request'], suffixes=('_full', '_api'))
                        merged = pd.merge(merged, tx_build[['user_id', 'request', 'duration']], on=['user_id', 'request'])
                        merged = merged.rename(columns={'duration': 'duration_build'})
                        merged = pd.merge(merged, tx_sign[['user_id', 'request', 'duration']], on=['user_id', 'request'])
                        merged = merged.rename(columns={'duration': 'duration_sign'})
                        merged = pd.merge(merged, tx_send[['user_id', 'request', 'duration']], on=['user_id', 'request'])
                        merged = merged.rename(columns={'duration': 'duration_send'})

                        merged['queue'] = merged['duration_full'] - (merged['duration_api'] + merged['duration_build'] + merged['duration_sign'] + merged['duration_send'])
                        queue_mean = merged['queue'].mean()
                        
                        queue_data.append({
                            "erc": erc_type, "users": users, "task": "QUEUE", "mean": queue_mean
                        })
            except Exception as e:
                logging.error(f"Error processing {root}: {e}")
                pass

    df_main = pd.DataFrame(data)
    if queue_data:
        df_queue = pd.DataFrame(queue_data)
        if not df_main.empty:
            df = pd.concat([df_main, df_queue], ignore_index=True)
        else:
            df = df_queue
    else:
        df = df_main

    # Final aggregation: one mean per (erc, users, task)
    if not df.empty:
        df = df.groupby(['erc', 'users', 'task'])['mean'].mean().reset_index()

    if df.empty: return

    # Colors
    task_colors_erc1155 = { 'API-TX-BUILD': '#d4edda', 'QUEUE': '#a3d9a5', 'TX-BUILD': '#6ec071', 'TX-SIGN': '#4caf50', 'TX-SEND': '#2e7d32'}
    task_colors_erc721 = { 'API-TX-BUILD': '#ffe0b2', 'QUEUE': '#ffcc80', 'TX-BUILD': '#ffb74d', 'TX-SIGN': '#ff9800', 'TX-SEND': '#f57c00'}

    all_users = sorted(df['users'].unique())
    task_order = ['API-TX-BUILD', 'QUEUE', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']
    
    # plt.rcParams.update({'font.size': FONT_SIZE})
    plt.rcParams.update({'font.size': 18})
    fig, ax = plt.subplots(figsize=(12, 8))
    
    n_contracts = 2
    n_tasks = len(task_order)
    
    # Dimensions
    bar_width = 0.09
    gap_at_center = 0.0
    group_width = n_tasks * bar_width
    
    x = np.arange(len(all_users))
    
    for u_idx, users in enumerate(all_users):
        center = x[u_idx]
        
        # ERC1155 Group (Left of center)
        start_x_1155 = center - (gap_at_center / 2) - group_width
        
        # ERC721 Group (Right of center)
        start_x_721 = center + (gap_at_center / 2)
        
        for erc in ['erc1155', 'erc721']:
            erc_data = df[df['erc'] == erc]
            task_colors = task_colors_erc1155 if erc == 'erc1155' else task_colors_erc721
            
            # Determine starting X for this contract group
            if erc == 'erc1155':
                current_x = start_x_1155
            else:
                current_x = start_x_721
            
            for task in task_order:
                task_user_data = erc_data[(erc_data['task'] == task) & (erc_data['users'] == users)]
                val = task_user_data['mean'].mean() if not task_user_data.empty else 0
                val = max(1e-6, val)
                
                ax.bar(current_x, val, bar_width, 
                       color=task_colors.get(task, '#333333'), edgecolor='white', linewidth=0.5, align='edge')
                current_x += bar_width

    ax.set_xlabel('Quantidade de Usuários')
    ax.set_ylabel('Latência (s)')
    
    if use_log_scale:
        # ax.set_title('Detalhamento de Latência por Etapa (Escala Logarítmica)', fontsize=FONT_SIZE_TITLE)
        ax.set_yscale('log')
        ax.grid(True, axis='y', which="both", alpha=0.3)
    else:
        # ax.set_title('Detalhamento de Latência por Etapa', fontsize=FONT_SIZE_TITLE)
        ax.grid(True, axis='y', alpha=0.3)
    
    ax.set_xticks(x)
    ax.set_xticklabels(all_users)
    
    # Fixed padding for x-axis to be the same regardless of tick count
    # 0.6 covers the bar cluster width (0.45 per side) with a consistent margin
    padding = 0.6    
    ax.set_xlim(min(x) - padding, max(x) + padding)
    
    # Legend 1: Operations
    op_legend = [
        Patch(facecolor='#f5f5f5', edgecolor='black', label='API'),
        Patch(facecolor='#d9d9d9', edgecolor='black', label='QUEUE'),
        Patch(facecolor='#969696', edgecolor='black', label='BUILD'),
        Patch(facecolor='#636363', edgecolor='black', label='SIGN'),
        Patch(facecolor='#252525', edgecolor='black', label='SEND'),
    ]
    # legend1 = ax.legend(handles=op_legend, fontsize=FONT_SIZE_LEGEND, loc='upper left', bbox_to_anchor=(1.02, 1))
    legend1 = ax.legend(handles=op_legend, fontsize=15, loc='upper left', bbox_to_anchor=(1.02, 1))
    ax.add_artist(legend1)
    
    # Legend 2: Contracts
    erc_legend = [
        Patch(facecolor='#4caf50', edgecolor='white', label='ERC-1155'),
        Patch(facecolor='#ff9800', edgecolor='white', label='ERC-721')
    ]
    # ax.legend(handles=erc_legend, fontsize=FONT_SIZE_LEGEND, loc='upper left', bbox_to_anchor=(1.02, 0.7))
    ax.legend(handles=erc_legend, fontsize=15, loc='upper left', bbox_to_anchor=(1.02, 0.7))
    
    plt.tight_layout()
    # Save
    if use_log_scale:
        filename_base = "plot_txbuild_grouped_log"
    else:
        filename_base = "plot_txbuild_grouped"
    
    save_plot(output_dir, filename_base, bbox_inches='tight', dpi=150)
    plt.close()
