import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import logging

# Constants from plot_experiments.py
FIG_SIZE = (12, 8)
FONT_SIZE = 32
FONT_SIZE_LEGEND = 28
FONT_SIZE_TITLE = 22
X_LIMIT = 100 

# Get tab20 colormap
tab20 = plt.get_cmap("tab20").colors

# Define styles from plot_experiments.py
styles = {
    ("erc1155", "api-tx-build"): {"color": tab20[1], "label": "ERC-1155 - Escrita (Produtor)", "marker": "o"}, # Light Blue
    ("erc721", "api-tx-build"): {"color": tab20[0], "label": "ERC-721 - Escrita (Produtor)", "marker": "^"},  # Dark Blue
    ("erc1155", "api-read-only"): {"color": tab20[7], "label": "ERC-1155 - Leitura (Consumidor)", "marker": "o"}, # Light Red
    ("erc721", "api-read-only"): {"color": tab20[6], "label": "ERC-721 - Leitura (Consumidor)", "marker": "^"},  # Dark Red
}


# --- Helper Functions ---

def format_endpoint_name(endpoint_str):
    """
    Formats the endpoint string to 'CONTRACT - Function'.
    Example: /api/erc721/mintRootBatchTx -> ERC-721 - mintRootBatchTx
    """
    if not endpoint_str:
        return ""
    
    parts = endpoint_str.strip("/").split("/")
    
    contract = ""
    function_name = parts[-1] if parts else ""
    
    # Try to find contract in parts
    for part in parts:
        if "erc721" in part.lower():
            contract = "ERC-721"
            break
        elif "erc1155" in part.lower():
            contract = "ERC-1155"
            break
            
    if contract:
        return f"{contract} - {function_name}"
    
    return function_name


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
    Scans for stats_task.csv files (consolidated stats) instead of out*.csv.
    Returns DataFrame compatible with plot_experiments.py logic.
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "stats_task.csv" in files:
            # Check for args_run.json
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): 
                args_path = os.path.join(root, "args_run.json")

            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    exp_type = os.path.basename(root)
                    
                    # Read stats_task.csv
                    stats_file = os.path.join(root, "stats_task.csv")
                    df = pd.read_csv(stats_file)
                    
                    if df.empty:
                        continue
                    
                    # stats_task.csv has columns: task, count, mean, median, std, min, max, p50, p60, etc.
                    
                    # Filter for 'TX-BLOCK' if this is a write experiment (api-tx-build)
                    # to avoid summing up API + BUILD + SIGN + SEND + BLOCK counts.
                    if exp_type == "api-tx-build":
                        # User requested "SEND" (meaning the confirmed write on blockchain). 
                        # TX-BLOCK represents the confirmed block receipt.
                        df = df[df["task"] == "TX-BLOCK"]

                    if df.empty:
                        continue
                    
                    # We need to aggregate across all tasks (now filtered) for this experiment
                    # Calculate weighted mean and total count
                    
                    # If we simply want "Success Count" for the plot, we should ideally use 'success_count' 
                    # column if it exists, otherwise 'count'.
                    # For plot_latency, we want the mean duration.
                    
                    count_col = 'success_count' if 'success_count' in df.columns else 'count'
                    
                    total_count = df[count_col].sum() if count_col in df.columns else df['count'].sum()
                    
                    if total_count > 0:
                        weighted_mean = (df['mean'] * df['count']).sum() / df['count'].sum() # Weight by total occurrences
                        
                        # Incorporate both internal noise (std) and between-run noise (mean_std)
                        internal_var = (df['std']**2 * df['count']).sum() / df['count'].sum()
                        between_run_var = (df.get('mean_std', 0)**2 * df['count']).sum() / df['count'].sum()
                        weighted_std = np.sqrt(internal_var + between_run_var)
                    else:
                        weighted_mean = 0
                        weighted_std = 0
                    
                    data.append({
                        'erc': erc_type,
                        'users': users,
                        'experiment_type': exp_type,
                        'mean': weighted_mean,
                        'std': weighted_std,
                        'count': int(total_count)
                    })

                except Exception as e:
                    logging.warning(f"Error reading stats_task.csv in {root}: {e}")
    
    return pd.DataFrame(data)

def scan_results_throughput(root_dir, window_size=10):
    """
    Scans for stats_global.csv files to get RPS (throughput) data.
    Returns DataFrame with throughput metrics.
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "stats_global.csv" in files:
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): 
                args_path = os.path.join(root, "args_run.json")

            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    
                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    exp_type = os.path.basename(root)
                    
                    # Read stats_global.csv
                    stats_file = os.path.join(root, "stats_global.csv")
                    df = pd.read_csv(stats_file)
                    
                    if df.empty:
                        continue
                    
                    # stats_global.csv has 'rps' column which might be (API_RPS + BC_RPS).
                    # For api-tx-build, we only want BC_RPS (Throughput of confirmed transactions).
                    
                    row = df.iloc[0] # Usually only one row per global stats file? Or multiple for phases?
                    # scan_global_stats handles multi-row. Here we need to check.
                    # Usually stats_global.csv from save.py has 1 row/repetition, but Consolidate logic might keep multiple?
                    # Consolidate logic overwrites stats_global.csv (Line 274 in save.py creates stats_global).
                    # But if we have multiple repetitions, we might have multiple stats_global in subfolders?
                    # 'scan_results_throughput' iterates recursively.
                    
                    # For api-tx-build, calculate RPS = bc_success / duration
                    if exp_type == "api-tx-build":
                        bc_success = df.get('bc_success', df.get('total_bc', 0)).sum() # Sum if multiple rows/phases?
                        duration = df['duration'].sum() 
                        # Averaging RPS is tricky if duration varies.
                        # Best is Total Success / Total Duration if we aggregate?
                        # But here we are processing ONE stats_global.csv file (one repetition/experiment).
                        
                        total_rps = 0
                        for _, r in df.iterrows():
                             dur = r.get('duration', 1)
                             succ = r.get('bc_success', 0)
                             if dur > 0:
                                 total_rps += succ / dur
                                 
                        # If df has multiple rows (e.g. phases), we sum? usually only 1 row of interest.
                        if len(df) > 1:
                            # average or sum? If phases are sequential, avg RPS? 
                            # But usually we only have 1 phase per folder.
                            pass
                            
                    else:
                        # For read-only, rps is correct (api_rps)
                        total_rps = df['rps'].sum()
                    
                    data.append({
                        'erc': erc_type,
                        'users': users,
                        'experiment_type': exp_type,
                        'mean_throughput': total_rps,
                        'std_throughput': 0,  # Not available in stats_global
                        'count': 1
                    })

                except Exception as e:
                    logging.warning(f"Error reading stats_global.csv in {root}: {e}")
    
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
                    if phase == "api-tx-build":
                        # For write experiments, we ONLY count blockchain transactions (SEND/BLOCK)
                        total_requests = row.get("total_bc", 0)
                        total_success = row.get("bc_success", 0)
                        total_fail = row.get("bc_fail", 0)
                        
                        # Recalculate RPS based on BC success
                        duration = row.get("duration", 1)
                        if duration > 0:
                            rps = total_success / duration
                        else:
                            rps = 0
                    else:
                        # For read-only
                        total_requests = row.get("total_requests", 0) # total_api
                        total_success = row.get("api_success", 0) + row.get("bc_success", 0)
                        total_fail = row.get("api_fail", 0) + row.get("bc_fail", 0)
                        rps = row.get("rps", 0.0)
                    
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
    
    # Aggregate by (contract, phase, users) to calculate mean and std across repetitions
    result_df = pd.DataFrame(data)
    if not result_df.empty:
        # We want mean and std for each metric
        agg_map = {
            'total_requests': ['mean', 'std'],
            'total_success': ['mean', 'std'],
            'total_fail': ['mean', 'std'],
            'rps': ['mean', 'std']
        }
        
        result_df = result_df.groupby(['contract', 'phase', 'users'], as_index=False).agg(agg_map)
        
        # Flatten MultiIndex
        # 'rps' -> 'rps', 'rps' -> 'rps_std'
        new_cols = []
        for col, func in result_df.columns:
            if col in ['contract', 'phase', 'users']:
                new_cols.append(col)
            elif func == 'mean':
                new_cols.append(col)
            else:
                new_cols.append(f"{col}_std")
        
        result_df.columns = new_cols
    
    return result_df

def log_plot_creation(filepath):
    """
    Log the creation of a plot file in a standardized format.
    
    Args:
        filepath: relative path to the created plot file.
    """
    logging.info(f"\t- Generated plot: {filepath}")

def save_plot(output_dir, filename_base, **kwargs):
    """
    Save the current figure in both PNG and PDF formats in separate subdirectories.
    
    Args:
        output_dir: The base 'plots' directory.
        filename_base: The filename without extension.
        **kwargs: Additional arguments for plt.savefig (e.g., bbox_inches, dpi).
    """
    formats = ["png", "pdf"]
    for fmt in formats:
        subdir = os.path.join(output_dir, fmt)
        os.makedirs(subdir, exist_ok=True)
        
        filepath = os.path.join(subdir, f"{filename_base}.{fmt}")
        plt.savefig(filepath, **kwargs)
        log_plot_creation(filepath)

def scan_endpoint_stats(root_dir, phase_filter="api-read-only"):
    """
    Scans for out*.csv files and aggregates statistics per endpoint for experiments matching phase_filter.
    Returns a DataFrame with columns: 
    ['contract', 'users', 'endpoint', 'total_requests', 'total_success', 'total_fail', 'mean_duration']
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        # Find all matching output files (out.csv, out_rep-1.csv, ...)
        out_files = [f for f in files if f.startswith("out") and f.endswith(".csv")]
        
        if not out_files:
            continue

        # Check for args_run.json
        parent_dir = os.path.dirname(root)
        args_path = os.path.join(parent_dir, "args_run.json")
        if not os.path.exists(args_path): args_path = os.path.join(root, "args_run.json")

        if os.path.exists(args_path):
            try:
                with open(args_path, 'r') as f:
                    args_run = json.load(f)
                
                # Check experiment type
                exp_type = os.path.basename(root)
                if exp_type != phase_filter:
                        continue

                users = convert_users_to_int(args_run.get('users', 0))
                erc_type = args_run.get('contract', 'unknown')
                
                # Iterate over all found output files (repetitions)
                for out_file in out_files:
                    try:
                        df = pd.read_csv(os.path.join(root, out_file))
                        
                        if df.empty:
                            continue
                            
                        if "endpoint" not in df.columns:
                            continue
                            
                        grouped = df.groupby("endpoint")
                        
                        for endpoint, group in grouped:
                            total = len(group)
                            success = (group["status"] == "success").sum()
                            fail = total - success
                            mean_dur = pd.to_numeric(group["duration"], errors='coerce').mean()
                            
                            data.append({
                                "contract": erc_type,
                                "users": users,
                                "endpoint": endpoint,
                                "total_requests": total,
                                "total_success": success,
                                "total_fail": fail,
                                "mean_duration": mean_dur
                            })
                    except Exception as e_file:
                        logging.warning(f"Error reading {out_file} in {root}: {e_file}")

            except Exception as e:
                logging.warning(f"Error scanning endpoint stats in {root}: {e}")
                    
    return pd.DataFrame(data)


def scan_stats_endpoint_files(root_dir, phase_filter="api-read-only"):
    """
    Scans for stats_endpoint.csv files (consolidated stats) and extracts data for plotting.
    This avoids reading individual out*.csv files which would create duplicate points.
    
    Returns a DataFrame with columns: 
    ['contract', 'users', 'endpoint', 'total_requests', 'total_success', 'total_fail', 'mean_duration']
    
    Note: stats_endpoint.csv contains aggregated statistics (count, mean, etc.) but not
    success/fail breakdown. We'll use 'count' as total_requests.
    """
    data = []
    
    for root, dirs, files in os.walk(root_dir):
        if "stats_endpoint.csv" in files:
            # Check for args_run.json
            parent_dir = os.path.dirname(root)
            args_path = os.path.join(parent_dir, "args_run.json")
            if not os.path.exists(args_path): 
                args_path = os.path.join(root, "args_run.json")

            if os.path.exists(args_path):
                try:
                    with open(args_path, 'r') as f:
                        args_run = json.load(f)
                    
                    # Check experiment type
                    exp_type = os.path.basename(root)
                    if phase_filter and exp_type != phase_filter:
                        continue

                    users = convert_users_to_int(args_run.get('users', 0))
                    erc_type = args_run.get('contract', 'unknown')
                    
                    # Read stats_endpoint.csv
                    stats_file = os.path.join(root, "stats_endpoint.csv")
                    df = pd.read_csv(stats_file)
                    
                    if df.empty:
                        continue
                    
                    # stats_endpoint.csv has columns: endpoint, count, mean, median, std, min, max, p50, p60, etc.
                    # We use count as total_requests
                    for _, row in df.iterrows():
                        data.append({
                            "contract": erc_type,
                            "users": users,
                            "endpoint": row.get('endpoint', ''),
                            "total_requests": row.get('count'),
                            "total_requests_std": row.get('count_std', float('nan')),
                            "total_success": row.get('success_count'),
                            "total_success_std": row.get('success_std', float('nan')),
                            "total_fail": row.get('fail_count'),
                            "total_fail_std": row.get('fail_std', float('nan')),
                            "mean_duration": row.get('mean'),
                            "duration_std": row.get('mean_std', float('nan')),
                            "phase": exp_type
                        })

                except Exception as e:
                    logging.warning(f"Error reading stats_endpoint.csv in {root}: {e}")
                    
    return pd.DataFrame(data)

