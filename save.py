import os
import csv
import json
import logging
import pandas as pd
from datetime import datetime
from stats import Stats

# Internal imports
from log import SIZE
from config import RESULTS_DIR, ARGS_RUN_FILENAME, ARGS_FILENAME, RESUME_RUN_FILENAME

def _create_directory(directory_path: str):
    os.makedirs(directory_path, exist_ok=True)
    return directory_path


def create_results_directory(timestamp):
    """Create the main timestamped results directory."""
    directory_path = os.path.join(RESULTS_DIR, timestamp)
    directory = _create_directory(directory_path)
    # logging.info(f"[Utils] Created results directory: {directory}")
    return directory


def create_directory(current_directory, child_directory):
    """Create a subdirectory under the given path."""
    new_directory = os.path.join(current_directory, child_directory)
    directory = _create_directory(new_directory)
    # logging.debug(f"[Utils] Created subdirectory: {directory}")
    return directory


def save_run_args(run_directory, host, mode, contract, run, duration, users, step_users, interval_users, interval_requests, repeat):
    """
    Save run configuration parameters into a JSON file.

    Args:
        run_directory (str): Directory where ARGS_RUN_FILENAME will be saved.
    """
    args_file = os.path.join(run_directory, ARGS_RUN_FILENAME)

    args_data = {
        "host": host,
        "mode": mode,
        "contract": contract,
        "duration": duration,
        "run": run,
        "users": users,
        "step-users": step_users,
        "interval-users": interval_users,
        "interval-requests": interval_requests,
        "repeat": repeat,
    }

    with open(args_file, "w") as f:
        json.dump(args_data, f, indent=2)

    return args_file

def save_resume(run_directory, total_time):
    """Save a summary (resume) file with the total execution time."""

    resume_file = os.path.join(run_directory, RESUME_RUN_FILENAME)

    resume_data = {
        "total_time": total_time
    }

    with open(resume_file, "w") as f:
        json.dump(resume_data, f, indent=2)

    logging.info("")
    logging.info(f"[Save] Saved run resume : {resume_file}")
    logging.debug(f"[Save] Saved run resume : {json.dumps(resume_data, indent=2)}")


def save_results_args(results_directory, args):
    """Save the main argparse Namespace as a JSON file."""
    args_file = os.path.join(results_directory, ARGS_FILENAME)
    args_dict = vars(args)

    with open(args_file, "w") as f:
        json.dump(args_dict, f, indent=2)

    logging.info("")
    logging.info(f"[Save] Saved test session arguments : {args_file}")
    logging.debug(f"[Save] Saved test session arguments : {json.dumps(args_dict, indent=2)}")


def save_results(results, output_file: str):
    fieldnames = [
        "timestamp",
        "user_id",
        "request",
        "task",
        "endpoint",
        "duration",
        "status",
    ]

    filtered_rows = [
        {field: entry.get(field) for field in fieldnames}
        for entry in results
    ]

    with open(output_file, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(filtered_rows)


def save_global_performance_summary(
    path, users, duration, api_reqs, bc_reqs, total_reqs, rps, phase,
    api_success=0, api_fail=0, bc_success=0, bc_fail=0
):
    """Saves the global execution summary to a CSV file."""
    file_exists = os.path.isfile(path)
    fieldnames = [
        "phase", "users", "duration", "total_api", "total_bc", "total_requests", "rps",
        "api_success", "api_fail", "bc_success", "bc_fail"
    ]
    
    try:
        with open(path, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            
            writer.writerow({
                "phase": phase,
                "users": users,
                "duration": duration,
                "total_api": api_reqs,
                "total_bc": bc_reqs,
                "total_requests": total_reqs,
                "rps": f"{rps:.2f}",
                "api_success": api_success,
                "api_fail": api_fail,
                "bc_success": bc_success,
                "bc_fail": bc_fail
            })
    except Exception as e:
        print(f"[Save] Failed to save global summary: {e}")


def save_all_outputs(run_data, phase_name, output_file):
    """
    Saves all test outputs: raw results, global summary, and detailed statistics.
    """
    if not output_file:
        return

    logging.info(f"Saving raw outputs for phase: {phase_name}")
    results = run_data.get("results", [])
    save_results(results, output_file)
    logging.info(f"\t- Raw results saved: {output_file}")


def consolidate_stats(run_directory, phase_name):
    """
    Scans the phase directory for all 'out*.csv' files, aggregates them using Stats,
    and saves consolidated statistics files (averages/stats across all repetitions).
    """
    phase_dir = os.path.join(run_directory, phase_name)
    if not os.path.isdir(phase_dir):
        logging.warning(f"[Consolidate] Phase directory not found: {phase_dir}")
        return

    # Find all output files (out.csv, out_rep-1.csv, etc.)
    out_files = [
        os.path.join(phase_dir, f) 
        for f in os.listdir(phase_dir) 
        if f.startswith("out") and f.endswith(".csv")
    ]

    if not out_files:
        logging.warning(f"[Consolidate] No output files found in {phase_dir}")
        return

    logging.info(f"[Consolidate] Aggregating {len(out_files)} files in {phase_name}...")

    # Initialize lists to store metrics per repetition
    task_reps = []
    endpoint_reps = []
    task_endpoint_reps = []

    # 1. Collect Stats per repetition
    for of in sorted(out_files):
        try:
            s_rep = Stats(percentiles=[.5, .9, .99])
            s_rep.load_multiple_csv([(of, {phase_name})])
            
            task_reps.append(s_rep.stats_by_task())
            endpoint_reps.append(s_rep.stats_by_endpoint())
            task_endpoint_reps.append(s_rep.stats_by_task_and_endpoint())
        except Exception as e:
            logging.warning(f"[Consolidate] Failed to process repetition {of}: {e}")

    # 2. Meta-Aggregation (Average and Std across repetitions)
    def aggregate_reps(df_list, group_cols):
        if not df_list:
            return pd.DataFrame()
        
        all_df = pd.concat(df_list, ignore_index=True)
        
        # We aggregate specific columns: count, success_count, fail_count, and metrics
        # We use mean() and std() for some, and specific min/max for others
        agg_map = {
            "count": ["mean", "std"],
            "mean": ["mean", "std"],
            "std": ["mean"],
            "min": ["min"],
            "max": ["max"],
            "median": ["mean"]
        }
        
        # Add success/fail counts if they exist in the dataframe
        if "success_count" in all_df.columns:
            agg_map["success_count"] = ["mean", "std"]
        if "fail_count" in all_df.columns:
            agg_map["fail_count"] = ["mean", "std"]
        
        # Percentiles (if multiple reps, we just take the mean of the percentiles)
        percentile_cols = [c for c in all_df.columns if c.startswith("p") and c[1:].isdigit()]
        for p in percentile_cols:
            agg_map[p] = ["mean"]

        # Perform aggregation
        grouped = all_df.groupby(group_cols).agg(agg_map)
        
        # Flatten MultiIndex columns
        # Structure: (column, function) -> "column" if function in ['mean','min','max'] else "name_std"
        new_cols = []
        for col, func in grouped.columns:
            if func in ["mean", "min", "max"]:
                new_cols.append(col)
            elif func == "std":
                # Rename success_count_std -> success_std for plotter compatibility
                name = col.replace("_count", "")
                new_cols.append(f"{name}_std")
            else:
                new_cols.append(f"{col}_{func}")
        
        grouped.columns = new_cols
        return grouped.reset_index()

    # Save consolidated stats files
    path_stats_task = os.path.join(phase_dir, "stats_task.csv")
    df_task = aggregate_reps(task_reps, ["task"])
    if not df_task.empty:
        df_task.to_csv(path_stats_task, index=False)
        logging.info(f"\t- Consolidated Stats by task       : {path_stats_task}")

    path_stats_endpoint = os.path.join(phase_dir, "stats_endpoint.csv")
    df_endpoint = aggregate_reps(endpoint_reps, ["endpoint"])
    if not df_endpoint.empty:
        df_endpoint.to_csv(path_stats_endpoint, index=False)
        logging.info(f"\t- Consolidated Stats by endpoint   : {path_stats_endpoint}")

    path_stats_task_endpoint = os.path.join(phase_dir, "stats_task_endpoint.csv")
    df_task_endpoint = aggregate_reps(task_endpoint_reps, ["task", "endpoint"])
    if not df_task_endpoint.empty:
        df_task_endpoint.to_csv(path_stats_task_endpoint, index=False)
        logging.info(f"\t- Consolidated Stats task/endpoint : {path_stats_task_endpoint}")
    
    # 3. Generate Global Summary (stats_global.csv)
    if out_files:
        logging.info(f"[Consolidate] Generating global performance summary...")
        path_stats_global = os.path.join(phase_dir, "stats_global.csv")
        
        # Fresh file for global summary
        if os.path.exists(path_stats_global):
            os.remove(path_stats_global)
            
        for of in sorted(out_files):
            try:
                # We use a fresh Stats object per file to generate individual global metrics
                s = Stats(percentiles=[.5, .9])
                s.load_multiple_csv([(of, {phase_name})])
                
                # --- Global Performance Entry ---
                # We let Stats calculate the duration from timestamps
                gs = s.global_stats(phase=phase_name)
                
                if not gs.empty:
                    row = gs.iloc[0]
                    duration = row.get("total_time", 0)
                    
                    if phase_name == "api-tx-build":
                        save_global_performance_summary(
                            path_stats_global,
                            users=s.df["user_id"].nunique(),
                            duration=duration,
                            api_reqs=row.get("total_requests_api", 0),
                            bc_reqs=row.get("total_requests_blockchain", 0),
                            total_reqs=row.get("total_requests_api", 0) + row.get("total_requests_blockchain", 0),
                            rps=row.get("rps_api", 0) + row.get("rps_blockchain", 0),
                            phase=phase_name,
                            api_success=row.get("success_api", 0),
                            api_fail=row.get("fails_api", 0),
                            bc_success=row.get("success_blockchain", 0),
                            bc_fail=row.get("fails_blockchain", 0)
                        )
                    else: # api-read-only
                        save_global_performance_summary(
                            path_stats_global,
                            users=s.df["user_id"].nunique(),
                            duration=duration,
                            api_reqs=row.get("total_requests_api", 0),
                            bc_reqs=0,
                            total_reqs=row.get("total_requests_api", 0),
                            rps=row.get("rps_api", 0),
                            phase=phase_name,
                            api_success=row.get("success", 0),
                            api_fail=row.get("fails", 0)
                        )
            except Exception as e:
                logging.warning(f"Failed to process global metrics for {of}: {e}")
                
        logging.info(f"\t- Consolidated Global Stats saved  : {path_stats_global}")


