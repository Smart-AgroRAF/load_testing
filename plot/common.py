import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging

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


# --- Helper Functions ---

def convert_users_to_int(val):
    """Convert users value to integer, handling lists/tuples."""
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
    """
    Scans results and calculates throughput using sliding time window.
    """
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

def scan_global_stats(root_dir):
    """
    Scans for stats_global.csv files in the directory tree.
    Returns a DataFrame with aggregated stats including contract type and RPS.
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "stats_global.csv" in files:
            file_path = os.path.join(root, "stats_global.csv")
            try:
                # Attempt to find args_run.json to get contract type
                contract = "unknown"
                # Check current dir
                args_path = os.path.join(root, "args_run.json")
                if not os.path.exists(args_path):
                    # Check parent dir
                    parent_dir = os.path.dirname(root)
                    args_path = os.path.join(parent_dir, "args_run.json")
                
                if os.path.exists(args_path):
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                        contract = args_run.get('contract', 'unknown')

                # Read the CSV
                df = pd.read_csv(file_path)
                
                required_cols = ["phase", "users", "total_requests"]
                if not all(col in df.columns for col in required_cols):
                    continue

                for _, row in df.iterrows():
                    phase = row["phase"]
                    if phase not in ["api-tx-build", "api-read-only"]:
                        continue

                    users = row["users"]
                    total_requests = row.get("total_requests", 0)
                    api_success = row.get("api_success", 0)
                    bc_success = row.get("bc_success", 0)
                    api_fail = row.get("api_fail", 0)
                    bc_fail = row.get("bc_fail", 0)
                    rps = row.get("rps", 0.0)
                    
                    total_success = api_success + bc_success
                    total_fail = api_fail + bc_fail
                    
                    data.append({
                        "contract": contract,
                        "phase": phase,
                        "users": users,
                        "total_requests": total_requests,
                        "total_success": total_success,
                        "total_fail": total_fail,
                        "rps": rps
                    })

            except Exception as e:
                logging.warning(f"Error reading {file_path}: {e}")
                
    return pd.DataFrame(data)

def log_plot_creation(filepath):
    """
    Log the creation of a plot file in a standardized format.
    
    Args:
        filepath: relative path to the created plot file.
    """
    logging.info(f"\tGenerated plot: {filepath}")
