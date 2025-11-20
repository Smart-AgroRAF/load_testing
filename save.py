import os
import json
import logging
from datetime import datetime

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
