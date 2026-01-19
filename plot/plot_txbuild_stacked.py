import os
import json
import logging
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

# Internal imports
from .common import FIG_SIZE, FONT_SIZE, FONT_SIZE_LEGEND, FONT_SIZE_TITLE, convert_users_to_int, log_plot_creation, save_plot

def create_txbuild_stacked_plot(root_dir, output_dir):
    """
    Create stacked bar plot for TX-BUILD operations breakdown.
    
    Args:
        root_dir: Directory containing test results
        output_dir: Directory to save the plot
    """
    data = []
    queue_data = []

    # 1. Scan specific for TX tasks
    for root, dirs, files in os.walk(root_dir):
        # Look for out*.csv (out.csv, out_rep-1.csv, etc.)
        output_files = [f for f in files if f.startswith("out") and f.endswith(".csv")]
        
        if not output_files or "api-tx-build" not in root:
            continue

        # Metadata fetch
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
                        # Identify successful requests
                        success_requests = df[(df['task'] == 'TX-BLOCK') & (df['status'] == 'success')][['user_id', 'request']]
                        # Filter dataframe to only keep rows from successful requests
                        df_success = df.merge(success_requests, on=['user_id', 'request'])
                    else:
                        # Fallback for old data or if TX-BLOCK is missing status (shouldn't happen now)
                        df_success = df

                    if df_success.empty:
                        continue

                    # Basic tasks
                    for task in ['API-TX-BUILD', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']:
                        task_data = df_success[df_success['task'] == task]
                        if not task_data.empty:
                            data.append({
                                "erc": erc_type, "users": users, "task": task, "mean": task_data['duration'].mean()
                            })
                    
                    # QUEUE calculation (FULL - parts)
                    full_data = df_success[df_success['task'] == 'FULL']
                    api_data = df_success[df_success['task'] == 'API-TX-BUILD']
                    tx_build = df_success[df_success['task'] == 'TX-BUILD']
                    tx_sign = df_success[df_success['task'] == 'TX-SIGN']
                    tx_send = df_success[df_success['task'] == 'TX-SEND']
                    
                    if not full_data.empty and not api_data.empty and not tx_build.empty and not tx_send.empty:
                        # Group by user_id and request to calculate queue per transaction then average
                        # This is more accurate than subtracting global means
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

    # Combine regular tasks + calculated QUEUE
    df_main = pd.DataFrame(data)
    if queue_data:
        df_queue = pd.DataFrame(queue_data)
        if not df_main.empty:
            df = pd.concat([df_main, df_queue], ignore_index=True)
        else:
            df = df_queue
    else:
        df = df_main
    
    # Final aggregation: the above appends one mean per FILE. We need one mean per (erc, users, task)
    if not df.empty:
        df = df.groupby(['erc', 'users', 'task'])['mean'].mean().reset_index()

    if df.empty: return

    # Colors as defined in plot_txbuild_stacked.py (Green and Orange)
    task_colors_erc1155 = {
        'API-TX-BUILD': '#d4edda',
        'QUEUE': '#a3d9a5',
        'TX-BUILD': '#6ec071',
        'TX-SIGN': '#4caf50',
        'TX-SEND': '#2e7d32',
    }
    
    task_colors_erc721 = {
        'API-TX-BUILD': '#ffe0b2',
        'QUEUE': '#ffcc80',
        'TX-BUILD': '#ffb74d',
        'TX-SIGN': '#ff9800',
        'TX-SEND': '#f57c00',
    }

    all_users = sorted(df['users'].unique())
    task_order = ['API-TX-BUILD', 'QUEUE', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']
    
    plt.rcParams.update({'font.size': FONT_SIZE})
    fig, ax = plt.subplots(figsize=FIG_SIZE)
    
    bar_width = 0.35
    x = np.arange(len(all_users))
    
    for erc_idx, erc in enumerate(['erc1155', 'erc721']):
        erc_data = df[df['erc'] == erc]
        task_colors = task_colors_erc1155 if erc == 'erc1155' else task_colors_erc721
        bottoms = np.zeros(len(all_users))
        
        for task in task_order:
            task_values = []
            for u in all_users:
                task_user_data = erc_data[(erc_data['task'] == task) & (erc_data['users'] == u)]
                val = task_user_data['mean'].mean() if not task_user_data.empty else 0
                task_values.append(max(0, val))
            
            offset = bar_width * erc_idx
            ax.bar(x + offset, task_values, bar_width, bottom=bottoms, 
                   color=task_colors.get(task, '#333333'), edgecolor='white', linewidth=0.5)
            bottoms += task_values

    ax.set_title('Detalhamento de Latência por Etapa', fontsize=FONT_SIZE_TITLE)
    ax.set_xlabel('Quantidade de Usuários')
    ax.set_ylabel('Latência (s)')
    # ax.set_title('(a) Ambiente de testes', fontsize=FONT_SIZE_TITLE)
    ax.set_xticks(x + bar_width / 2)
    ax.set_xticklabels(all_users)
    ax.set_ylim(bottom=0)
    
    # Legend Logic
    operation_legend = [
        Patch(facecolor='#f5f5f5', edgecolor='black', label='API'),
        Patch(facecolor='#d9d9d9', edgecolor='black', label='QUEUE'),
        Patch(facecolor='#969696', edgecolor='black', label='BUILD'),
        Patch(facecolor='#636363', edgecolor='black', label='SIGN'),
        Patch(facecolor='#252525', edgecolor='black', label='SEND'),
    ]
    
    erc_legend = [
        Patch(facecolor='#4caf50', edgecolor='white', label='ERC1155'),
        Patch(facecolor='#ff9800', edgecolor='white', label='ERC721')
    ]

    # Combined Legend Outside
    combined_legend = operation_legend + [Patch(facecolor='white', alpha=0, label='')] + erc_legend
    ax.legend(handles=combined_legend, fontsize=FONT_SIZE_LEGEND, 
              loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0.)
    
    ax.grid(True, axis='y', alpha=0.3)
    
    ax2 = ax.twinx()
    ax2.set_yticks([])
    # ax2.legend(handles=erc_legend, fontsize=FONT_SIZE_LEGEND, loc='upper right')
    
    plt.xlim(-0.5, len(all_users) - 0.5 + bar_width*1.5)
    plt.tight_layout()
    
    save_plot(output_dir, "plot_txbuild_stacked", bbox_inches='tight', dpi=150)
    plt.close()
