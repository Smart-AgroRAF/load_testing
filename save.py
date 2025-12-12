import os
import csv
import json
import logging
from datetime import datetime
from stats import Stats

# Internal imports
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


def save_run_args(run_directory, users, spawn_rate, run_time, host, contract, mode):
    """
    Save run configuration parameters into a JSON file.

    Args:
        run_directory (str): Directory where ARGS_RUN_FILENAME will be saved.
    """
    args_file = os.path.join(run_directory, ARGS_RUN_FILENAME)

    args_data = {
        "users": users,
        "spawn_rate": spawn_rate,
        "run_time": run_time,
        "host": host,
        "contract": contract,
        "mode": mode,
    }

    with open(args_file, "w") as f:
        json.dump(args_data, f, indent=2)

    logging.info(f"[Save] Saved run arguments : {args_file}")
    logging.debug(f"[Save] Saved run arguments : {json.dumps(args_data, indent=2)}")


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


def save_global_performance_summary(path, users, duration, api_reqs, bc_reqs, total_reqs, rps, phase):
    """Saves the global execution summary to a CSV file."""
    file_exists = os.path.isfile(path)
    fieldnames = ["phase", "users", "duration", "total_api", "total_bc", "total_requests", "rps"]
    
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
                "rps": f"{rps:.2f}"
            })
    except Exception as e:
        print(f"[Save] Failed to save global summary: {e}")





def save_all_outputs(run_data, phase_name, output_file):
    """
    Saves all test outputs: raw results, global summary, and detailed statistics.
    """
    if not output_file:
        return

    # Unpack run_data
    results = run_data.get("results", [])
    users = run_data.get("users", 0) # run_data uses "users" key for worker count
    workers = run_data.get("users", 0) # run_data uses "users" key for worker count
    total_time = run_data.get("total_time", 0)
    global_stats = run_data.get("global_stats", {})

    # 1. Save Raw Results (out.csv)
    save_results(results, output_file)
    
    # 2. Save Global Summary (stats_global.csv)
    # display_path = os.path.join(os.path.dirname(output_file), "stats_global.csv")
    summary_path = os.path.join(os.path.dirname(output_file), "stats_global.csv")
    save_global_performance_summary(
        summary_path, 
        workers, 
        total_time, 
        global_stats.get("api", 0), 
        global_stats.get("bc", 0), 
        global_stats.get("total", 0), 
        global_stats.get("rps", 0),
        phase=phase_name
    )

    # 3. Generate and Save Detailed Statistics
    # Re-use the logic from main.py to generate stats by task/endpoint
    phase_dir = os.path.dirname(output_file)
    percentiles = [.5, .6, .7, .8, .9, .99]
    stats = Stats(percentiles=percentiles)

    # Load the results we just saved
    stats.load_multiple_csv([
        (output_file, {phase_name}),
    ])

    path_stats_task = os.path.join(phase_dir, "stats_task.csv")
    stats.stats_by_task().to_csv(path_stats_task, index=False)
    logging.info(f"Stats by task saved: {path_stats_task}")

    path_stats_endpoint = os.path.join(phase_dir, "stats_endpoint.csv")
    stats.stats_by_endpoint().to_csv(path_stats_endpoint, index=False)
    logging.info(f"Stats by endpoint saved: {path_stats_endpoint}")

    path_stats_task_endpoint = os.path.join(phase_dir, "stats_task_endpoint.csv")
    stats.stats_by_task_and_endpoint().to_csv(path_stats_task_endpoint, index=False)
    logging.info(f"Stats by task and endpoint saved: {path_stats_task_endpoint}")


