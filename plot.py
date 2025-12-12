import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging
import re

# Constants from plot_experiments.py
FIG_SIZE = (9, 8)
FONT_SIZE = 18
FONT_SIZE_LEGEND = 15
FONT_SIZE_TITLE = 22
X_LIMIT = 100 

# Get tab20 colormap
tab20 = plt.get_cmap("tab20").colors

# Define styles from plot_experiments.py
styles = {
    ("erc1155", "api-tx-build"): {"color": tab20[1], "label": "ERC1155 - Escrita (Produtor)", "marker": "o"}, # Light Blue
    ("erc721", "api-tx-build"): {"color": tab20[0], "label": "ERC721 - Escrita (Produtor)", "marker": "^"},  # Dark Blue
    ("erc1155", "api-read-only"): {"color": tab20[7], "label": "ERC1155 - Leitura (Consumidor)", "marker": "o"}, # Light Red
    ("erc721", "api-read-only"): {"color": tab20[6], "label": "ERC721 - Leitura (Consumidor)", "marker": "^"},  # Dark Red
}

# --- Helper Logic for Scanning (Adapted to use args_run.json) ---

def convert_users_to_int(val):
    try:
        if isinstance(val, (list, tuple)):
            return int(val[0])
        return int(val)
    except:
        return 0

def scan_results(root_dir):
    """
    Scans for results using args_run.json for metadata.
    Returns DataFrame compatible with plot_experiments.py logic.
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "out.csv" in files:
            # Check for args_run.json
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")

            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    # Experiment type is directory name
                    exp_type = os.path.basename(root)
                    
                    df = pd.read_csv(os.path.join(root, "out.csv"))
                    
                    filtered_df = pd.DataFrame()
                    if exp_type == "api-read-only":
                        filtered_df = df[df["status"] == "success"].copy()
                    elif exp_type == "api-tx-build":
                        filtered_df = df[df["task"] == "FULL"].copy()
                    
                    if not filtered_df.empty:
                        mean_dur = filtered_df['duration'].mean()
                        std_dur = filtered_df['duration'].std()
                        count = len(filtered_df)
                        
                        data.append({
                            'erc': erc_type,
                            'users': users,
                            'experiment_type': exp_type,
                            'mean': mean_dur,
                            'std': std_dur,
                            'count': count
                        })
                except Exception as e:
                    logging.warning(f"Error scanning {root}: {e}")
    return pd.DataFrame(data)

def scan_results_throughput(root_dir, window_size=10):
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "out.csv" in files:
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")

            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    exp_type = os.path.basename(root)
                    
                    df = pd.read_csv(os.path.join(root, "out.csv"))
                    
                    filtered_df = pd.DataFrame()
                    if exp_type == "api-read-only":
                        filtered_df = df[df["status"] == "success"].copy()
                    elif exp_type == "api-tx-build":
                        filtered_df = df[df["task"] == "FULL"].copy()

                    if not filtered_df.empty and len(filtered_df) > 1:
                        filtered_df['timestamp'] = pd.to_numeric(filtered_df['timestamp'], errors='coerce')
                        filtered_df = filtered_df.dropna(subset=['timestamp'])
                        filtered_df = filtered_df.sort_values("timestamp")
                        
                        timestamps = filtered_df["timestamp"].values
                        if len(timestamps) == 0: continue

                        throughputs = []
                        min_ts = timestamps.min()
                        max_ts = timestamps.max()
                        
                        current_ts = min_ts
                        while current_ts <= max_ts:
                            window_end = current_ts + window_size
                            count_in_window = np.sum((timestamps >= current_ts) & (timestamps < window_end))
                            if count_in_window > 0:
                                throughputs.append(count_in_window / window_size)
                            current_ts += 1
                        
                        if throughputs:
                            data.append({
                                'erc': erc_type,
                                'users': users,
                                'experiment_type': exp_type,
                                'mean_throughput': np.mean(throughputs),
                                'std_throughput': np.std(throughputs),
                                'count': len(throughputs)
                            })
                except Exception as e:
                    logging.warning(f"Error throughput scanning {root}: {e}")
    return pd.DataFrame(data)

# --- Plotting Functions from plot_experiments.py ---

def plot_latency(df, output_dir):
    if df.empty: return
    plt.rcParams.update({'font.size': FONT_SIZE})
    plt.figure(figsize=FIG_SIZE)
    
    grouped = df.groupby(["erc", "experiment_type"])
    all_users = sorted(df["users"].unique())
    
    for (erc, exp_type), group in grouped:
        style = styles.get((erc, exp_type))
        if not style: continue
        
        subset = group.sort_values("users")
        subset["std"] = subset["std"].fillna(0)
        subset["ci"] = 1.96 * subset["std"] / np.sqrt(subset["count"])
        
        plt.errorbar(
            subset["users"], subset["mean"], yerr=subset["ci"],
            label=style["label"], color=style["color"], marker=style["marker"], capsize=5
        )
        
    plt.title("(b) Impacto do Número de Usuários na Latência", fontsize=FONT_SIZE_TITLE)
    plt.xlabel("Quantidade de Usuários")
    plt.ylabel("Latência (s) das Requisições Atendidas com Sucesso ⬅")
    plt.xticks(all_users)
    
    # Calculate balanced padding
    if len(all_users) > 1:
        spread = max(all_users) - min(all_users)
        padding = spread * 0.1 # 10% of the range
    else:
        padding = max(all_users) * 0.1

    plt.xlim(max(0, min(all_users) - padding), max(all_users) + padding)
    plt.legend(fontsize=FONT_SIZE_LEGEND)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "plot_latency.png"), bbox_inches='tight')
    plt.close()

def plot_throughput(df, output_dir):
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
        
    plt.title("(a) Impacto do Número de Usuários na Vazão", fontsize=FONT_SIZE_TITLE)
    plt.xlabel("Quantidade de Usuários")
    plt.ylabel("Vazão (req/s) de Requisições Atendidas com Sucesso ➡")
    plt.xticks(all_users)
    plt.legend(fontsize=FONT_SIZE_LEGEND)
    
    # Calculate balanced padding
    if len(all_users) > 1:
        spread = max(all_users) - min(all_users)
        padding = spread * 0.1
    else:
        padding = max(all_users) * 0.1
        
    plt.xlim(max(0, min(all_users) - padding), max(all_users) + padding)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "plot_throughput.png"), bbox_inches='tight')
    plt.close()

def plot_success_count(df, output_dir):
    if df.empty: return
    plt.rcParams.update({'font.size': FONT_SIZE})
    plt.figure(figsize=FIG_SIZE)
    
    grouped = df.groupby(["erc", "experiment_type"])
    all_users = sorted(df["users"].unique())
    
    for (erc, exp_type), group in grouped:
        style = styles.get((erc, exp_type))
        if not style: continue
        
        subset = group.sort_values("users")
        plt.plot(
            subset["users"], subset["count"],
            label=style["label"], color=style["color"], marker=style["marker"]
        )
        
    plt.title("(c) Impacto do Número de Usuários na Quantidade de Requisições", fontsize=FONT_SIZE_TITLE)
    plt.xlabel("Quantidade de Usuários")
    plt.ylabel("Quantidade de Requisições Atendidas com Sucesso ➡")
    plt.xticks(all_users)
    plt.legend(fontsize=FONT_SIZE_LEGEND)
    
    # Calculate balanced padding
    if len(all_users) > 1:
        spread = max(all_users) - min(all_users)
        padding = spread * 0.1
    else:
        padding = max(all_users) * 0.1
        
    plt.xlim(max(0, min(all_users) - padding), max(all_users) + padding)
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "plot_success_count.png"), bbox_inches='tight')
    plt.close()

# --- Stacked Plot Logic from plot_txbuild_stacked.py ---

def create_txbuild_stacked_plot(root_dir, output_dir):
    """
    Adapted from plot_txbuild_stacked.py.
    """
    data = []
    queue_data = []

    # 1. Scan specific for TX tasks
    for root, dirs, files in os.walk(root_dir):
        if "out.csv" in files and "api-tx-build" in root:
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
                    
                    df = pd.read_csv(os.path.join(root, "out.csv"))
                    
                    # Basic tasks
                    for task in ['API-TX-BUILD', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']:
                        task_data = df[df['task'] == task]
                        if not task_data.empty:
                            data.append({
                                "erc": erc_type, "users": users, "task": task, "mean": task_data['duration'].mean()
                            })
                    
                    # QUEUE calculation (FULL - parts)
                    full_data = df[df['task'] == 'FULL']
                    api_data = df[df['task'] == 'API-TX-BUILD']
                    tx_build = df[df['task'] == 'TX-BUILD']
                    tx_sign = df[df['task'] == 'TX-SIGN']
                    tx_send = df[df['task'] == 'TX-SEND']
                    
                    if not full_data.empty and not api_data.empty and not tx_build.empty and not tx_send.empty:
                            full_mean = full_data['duration'].mean()
                            sum_parts = api_data['duration'].mean() + tx_build['duration'].mean() + tx_sign['duration'].mean() + tx_send['duration'].mean()
                            queue_mean = full_mean - sum_parts
                            
                            queue_data.append({
                                "erc": erc_type, "users": users, "task": "QUEUE", "mean": queue_mean
                            })

                except Exception as e:
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

    if df.empty: return

    # Colors as defined in plot_txbuild_stacked.py (Green and Orange)
    task_colors_erc1155 = {
        'API-TX-BUILD': '#d4edda',  # Very light green
        'QUEUE': '#a3d9a5',         # Light green  
        'TX-BUILD': '#6ec071',      # Medium light green
        'TX-SIGN': '#4caf50',       # Medium green
        'TX-SEND': '#2e7d32',       # Dark green
    }
    
    task_colors_erc721 = {
        'API-TX-BUILD': '#ffe0b2',  # Very light orange
        'QUEUE': '#ffcc80',         # Light orange
        'TX-BUILD': '#ffb74d',      # Medium light orange
        'TX-SIGN': '#ff9800',       # Medium orange
        'TX-SEND': '#f57c00',       # Dark orange
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
                task_values.append(max(0, val)) # Avoid negative values from weird calcs
            
            offset = bar_width * erc_idx
            # Only label first time? Legend handles it separately
            ax.bar(x + offset, task_values, bar_width, bottom=bottoms, 
                   color=task_colors.get(task, '#333333'), edgecolor='white', linewidth=0.5)
            bottoms += task_values

    ax.set_xlabel('Quantidade de Usuários')
    ax.set_ylabel('Latência (s)')
    ax.set_title('(a) Ambiente de testes', fontsize=FONT_SIZE_TITLE) # Fixed title as per typical usage
    ax.set_xticks(x + bar_width / 2)
    ax.set_xticklabels(all_users)
    ax.set_ylim(bottom=0)
    
    # Legend Logic from original
    from matplotlib.patches import Patch
    operation_legend = [
        Patch(facecolor='#f5f5f5', edgecolor='black', label='API'),
        Patch(facecolor='#d9d9d9', edgecolor='black', label='QUEUE'),
        Patch(facecolor='#969696', edgecolor='black', label='BUILD'),
        Patch(facecolor='#636363', edgecolor='black', label='SIGN'),
        Patch(facecolor='#252525', edgecolor='black', label='SEND'),
    ]
    ax.legend(handles=operation_legend, fontsize=FONT_SIZE_LEGEND, loc='upper left')
    ax.grid(True, axis='y', alpha=0.3)
    
    erc_legend = [
        Patch(facecolor='#4caf50', edgecolor='white', label='ERC1155'),
        Patch(facecolor='#ff9800', edgecolor='white', label='ERC721')
    ]
    ax2 = ax.twinx()
    ax2.set_yticks([])
    ax2.legend(handles=erc_legend, fontsize=FONT_SIZE_LEGEND, loc='upper right')
    
    plt.xlim(-0.5, len(all_users) - 0.5 + bar_width*1.5)
    plt.tight_layout()
    filename = os.path.join(output_dir, "plot_txbuild_stacked.png")
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    print(f"Generated plot: {filename}")
    plt.close()

def create_txbuild_grouped_log_plot(root_dir, output_dir):
    """
    Creates a grouped bar plot (not stacked) with logarithmic Y axis.
    Displays components side-by-side for easier magnitude comparison.
    """
    data = []
    queue_data = []

    # 1. Scan logic (Reused to ensure consistency)
    for root, dirs, files in os.walk(root_dir):
        if "out.csv" in files and "api-tx-build" in root:
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")
            
            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    
                    df = pd.read_csv(os.path.join(root, "out.csv"))
                    
                    for task in ['API-TX-BUILD', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']:
                        task_data = df[df['task'] == task]
                        if not task_data.empty:
                            data.append({
                                "erc": erc_type, "users": users, "task": task, "mean": task_data['duration'].mean()
                            })
                    
                    full_data = df[df['task'] == 'FULL']
                    api_data = df[df['task'] == 'API-TX-BUILD']
                    tx_build = df[df['task'] == 'TX-BUILD']
                    tx_sign = df[df['task'] == 'TX-SIGN']
                    tx_send = df[df['task'] == 'TX-SEND']
                    
                    if not full_data.empty and not api_data.empty and not tx_build.empty and not tx_send.empty:
                            full_mean = full_data['duration'].mean()
                            sum_parts = api_data['duration'].mean() + tx_build['duration'].mean() + tx_sign['duration'].mean() + tx_send['duration'].mean()
                            queue_mean = full_mean - sum_parts
                            queue_data.append({
                                "erc": erc_type, "users": users, "task": "QUEUE", "mean": queue_mean
                            })
                except Exception as e:
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

    if df.empty: return

    # Colors
    task_colors_erc1155 = { 'API-TX-BUILD': '#d4edda', 'QUEUE': '#a3d9a5', 'TX-BUILD': '#6ec071', 'TX-SIGN': '#4caf50', 'TX-SEND': '#2e7d32'}
    task_colors_erc721 = { 'API-TX-BUILD': '#ffe0b2', 'QUEUE': '#ffcc80', 'TX-BUILD': '#ffb74d', 'TX-SIGN': '#ff9800', 'TX-SEND': '#f57c00'}

    all_users = sorted(df['users'].unique())
    task_order = ['API-TX-BUILD', 'QUEUE', 'TX-BUILD', 'TX-SIGN', 'TX-SEND']
    
    plt.rcParams.update({'font.size': FONT_SIZE})
    fig, ax = plt.subplots(figsize=(12, 8)) # Wider for grouped bars
    
    # Logic for grouping
    # For each user tick, we have 2 contracts * 5 tasks = 10 bars
    # This is crowded. We will arrange them:
    # Group by Contract first? Or interleave tasks?
    # Let's do: For each User: [ERC1155 Tasks] space [ERC721 Tasks]
    
    n_contracts = 2
    n_tasks = len(task_order)
    
    # Dimensions
    bar_width = 0.08 # Slightly thinner to fit
    gap_at_center = 0.0
    group_width = n_tasks * bar_width
    
    x = np.arange(len(all_users))
    
    for u_idx, users in enumerate(all_users):
        center = x[u_idx]
        
        # ERC1155 Group (Left of center)
        # Starts at center - gap/2 - group_width
        start_x_1155 = center - (gap_at_center / 2) - group_width
        
        # ERC721 Group (Right of center)
        # Starts at center + gap/2
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
    ax.set_ylabel('Latência (s) - Log Scale')
    ax.set_title('Detalhamento de Latência por Etapa (Log Scale)', fontsize=FONT_SIZE_TITLE)
    ax.set_xticks(x)
    ax.set_xticklabels(all_users)
    ax.set_yscale('log')
    ax.grid(True, axis='y', which="both", alpha=0.3)
    
    # Legend 1: Operations (Grayscale representation)
    from matplotlib.patches import Patch
    op_legend = [
        Patch(facecolor='#f5f5f5', edgecolor='black', label='API'),
        Patch(facecolor='#d9d9d9', edgecolor='black', label='QUEUE'),
        Patch(facecolor='#969696', edgecolor='black', label='BUILD'),
        Patch(facecolor='#636363', edgecolor='black', label='SIGN'),
        Patch(facecolor='#252525', edgecolor='black', label='SEND'),
    ]
    legend1 = ax.legend(handles=op_legend, fontsize=FONT_SIZE_LEGEND, loc='upper left', bbox_to_anchor=(1.02, 1))
    ax.add_artist(legend1) # Keep this legend when adding the next one
    
    # Legend 2: Contracts (Color Identity)
    erc_legend = [
        Patch(facecolor='#4caf50', edgecolor='white', label='ERC1155'),
        Patch(facecolor='#ff9800', edgecolor='white', label='ERC721')
    ]
    ax.legend(handles=erc_legend, fontsize=FONT_SIZE_LEGEND, loc='upper left', bbox_to_anchor=(1.02, 0.7))
    
    plt.tight_layout()
    # Save
    filename = os.path.join(output_dir, "plot_txbuild_grouped_log.png")
    plt.savefig(filename, bbox_inches='tight', dpi=150)
    print(f"Generated plot: {filename}")
    plt.close()

# --- Extra Analysis (Kept for added value) ---

def plot_single_run_analysis(phase_dir):
    # (Kept simple version)
    out_file = os.path.join(phase_dir, "out.csv")
    if not os.path.exists(out_file): return
    try:
        df = pd.read_csv(out_file)
        if df.empty or 'timestamp' not in df.columns: return
        df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])
        start_time = df['timestamp'].min()
        rel_time = df['timestamp'] - start_time
        
        # Duration Timeline
        plt.figure(figsize=(10, 6))
        colors = df['status'].map({'success': 'green', 'fail': 'red'}).fillna('blue')
        if 'duration' in df.columns:
            plt.scatter(rel_time, df['duration'], c=colors, alpha=0.5, s=10)
            plt.title(f"Duration Timeline") 
            plt.savefig(os.path.join(phase_dir, "analysis_duration_timeline.png"))
            plt.close()
    except: pass

def plot_rps_comparison(root_dir, output_dir):
    # (Simplified version of what I added before)
    try:
        data = []
        for root, dirs, files in os.walk(root_dir):
            if "out.csv" in files:
                parent_dir = os.path.dirname(root)
                args_path = os.path.join(parent_dir, "args_run.json")
                if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")
                if os.path.exists(args_path):
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc = args_run.get('contract', 'unknown')
                    exp = os.path.basename(root)
                    df = pd.read_csv(os.path.join(root, "out.csv"))
                    
                    filtered_df = pd.DataFrame()
                    if exp == "api-read-only": filtered_df = df[df["status"] == "success"].copy()
                    elif exp == "api-tx-build": filtered_df = df[df["task"] == "FULL"].copy()
                    
                    if not filtered_df.empty:
                        filtered_df['timestamp'] = pd.to_numeric(filtered_df['timestamp'], errors='coerce')
                        filtered_df = filtered_df.dropna(subset=['timestamp'])
                        rel_time = filtered_df['timestamp'] - filtered_df['timestamp'].min()
                        bins = range(0, int(rel_time.max()) + 2)
                        hist, edges = np.histogram(rel_time, bins=bins)
                        data.append({'time': edges[:-1], 'rps': hist, 'label': f"{erc}-{exp} ({users}u)", 'users':users, 'erc':erc, 'exp':exp})
        
        if data:
            data.sort(key=lambda x: (x['erc'], x['exp'], x['users']))
            plt.figure(figsize=(12, 8))
            for d in data:
                plt.plot(d['time'], d['rps'], label=d['label'], alpha=0.7)
            plt.title("RPS Evolution Comparison")
            plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, "global_rps_comparison.png"), bbox_inches='tight')
            plt.close()
    except: pass

def generate_plots(root_dir):
    logging.info(f"Generating plots for session: {root_dir}")
    
    # # 0. Single Usage
    # for root, dirs, files in os.walk(root_dir):
    #     if "out.csv" in files: plot_single_run_analysis(root)

    # 1. Aggregated Std Plots (from plot_experiments)
    df = scan_results(root_dir)
    if not df.empty and df['users'].nunique() > 1:
        plot_latency(df, root_dir)
        plot_success_count(df, root_dir)

    df_tp = scan_results_throughput(root_dir)
    if not df_tp.empty and df_tp['users'].nunique() > 1:
        plot_throughput(df_tp, root_dir)

    # 2. Stacked Plot (from plot_txbuild_stacked)
    create_txbuild_stacked_plot(root_dir, root_dir)
    
    # 3. New Grouped Log Plot
    create_txbuild_grouped_log_plot(root_dir, root_dir)

    # 4. New Helper
    plot_rps_comparison(root_dir, root_dir)
