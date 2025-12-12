import os
import time
import datetime
import argparse
import itertools
import logging
import pandas as pd
from datetime import datetime

# Internal imports
import log
import save
from stats import Stats
import plot as plot_module
from load_tester import LoadTester
from users.user_erc721 import UserERC721
from users.user_erc1155 import UserERC1155

from config import USERS, RESULTS_DIR, MODES, HOST, RUN_TIME, SPAWN_RATE


def execute_and_generate_stats(run, phase_name, run_directory):

    phase_dir = f"{run_directory}/{phase_name}"
    os.makedirs(phase_dir, exist_ok=True)
    
    output_file = f"{phase_dir}/out.csv"
    
    run_data = run(phase_name, output_file)
    
    save.save_all_outputs(run_data, phase_name, output_file)

    logging.info(f"Finished stats generation.\n")


def run_load_tester(
    run,
    current_run,
    total_runs_all,
    output_dir, 
    host,
    contract,
    mode,
    duration,
    users, 
    interval_requests,
    step_users=None, 
    interval_users=None,
):
  
    if run == "static":
        run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_interval-requests-{interval_requests}"
    elif run == "ramp-up":
        run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_step_users-{step_users}_interval_users-{interval_users}_interval-requests-{interval_requests}"
    else:
        logging.error(f"Invalid run type: {run}")
        return

    run_directory = save.create_directory(output_dir, run_directory_name)
    output_file = f"{run_directory}/out.csv"

    save.save_run_args(
        run_directory=run_directory,
        users=users,
        spawn_rate=interval_users if run == "ramp-up" else 0, # Assuming interval_users as spawn_rate for simplicity
        run_time=duration,
        host=host,
        contract=contract,
        mode=mode
    )

    if contract == "erc721":
        user_class = UserERC721  
    elif contract == "erc1155": 
        user_class = UserERC1155
    else:
        logging.error(f"Invalid contract type: {contract}")
        return

    logging.info("-" * log.SIZE)
    logging.info(f"[{run.upper()}] Starting users configuration (Run {current_run}/{total_runs_all})...")
    logging.info("")

    tester = LoadTester(
        # output_file=output_file,
        host=host,
        mode=mode,
        contract=contract,
        duration=duration,
        user_cls=user_class,
        users=users,
        step_users=step_users,
        interval_users=interval_users,
        interval_requests=interval_requests
    )

    logging.info(f"[{run.upper()}] Finished users configurations (Run {current_run}/{total_runs_all}).")

    logging.info("-" * log.SIZE)
    logging.info(f"[{run.upper()}] Starting load test (Run {current_run}/{total_runs_all})...")
    logging.info("")

    if run == "static":
        execute_and_generate_stats(tester.run_static_load, "api-tx-build", run_directory)
        execute_and_generate_stats(tester.run_static_load, "api-read-only", run_directory)
    elif run == "ramp-up":
        execute_and_generate_stats(tester.run_ramp_up_load, "api-tx-build", run_directory)
        execute_and_generate_stats(tester.run_ramp_up_load, "api-read-only", run_directory)
    
    logging.info(f"[{run.upper()}] Finished load test (Run {current_run}/{total_runs_all}).")
    logging.info("")


def warm_up_load_tester(
    run,
    host,
    contract,
    mode,
    duration,
    users, 
    interval_requests,
    step_users=None, 
    interval_users=None,
):
    if contract == "erc721":
        user_class = UserERC721  
    elif contract == "erc1155": 
        user_class = UserERC1155
    else:
        logging.error(f"Invalid contract type: {contract}")
        return

    logging.info("-" * log.SIZE)
    logging.info(f"[WARM-UP][{run.upper()}] Starting users configuration...")
    logging.info("")

    tester = LoadTester(
        # output_file=None,
        host=host,
        mode=mode,
        contract=contract,
        duration=duration,
        user_cls=user_class,
        users=users,
        step_users=step_users,
        interval_users=interval_users,
        interval_requests=interval_requests
    )

    logging.info(f"[WARM-UP][{run.upper()}] Finished users configurations.")

    logging.info("-" * log.SIZE)
    logging.info(f"[WARM-UP][{run.upper()}] Starting load test...")
    logging.info("")

    if run == "static":
        tester.run_static_load(phase="api-tx-build")
        tester.run_static_load(phase="api-read-only")
    elif run == "ramp-up":
        tester.run_ramp_up_load(phase="api-tx-build")
        tester.run_ramp_up_load(phase="api-read-only")

    logging.info(f"[WARM-UP][{run.upper()}] Finished load test.")
    logging.info("")

def pad_list(lst, target_len):
    if len(lst) == 1:
        return lst * target_len
    return lst

def main():
    parser = argparse.ArgumentParser(description="Load testing")

    help_msg = "verbosity logging level (INFO=%d DEBUG=%d)" % (logging.INFO, logging.DEBUG)
    parser.add_argument("--verbosity", "-v", help=help_msg, default=logging.INFO, type=int)

    parser.add_argument("--plot", type=str, help="Gera gráficos a partir dos arquivos CSV de resultados existentes.")

    # Configuration arguments
    parser.add_argument("--mode", type=str, default=MODES[0], choices=MODES, help=f"Modo de execução (default: {MODES[0]})")
    parser.add_argument("--type", choices=["cartesian", "paired"], default="paired", help="Define o modo de combinação dos parâmetros.")
    parser.add_argument("--contract", choices=["erc721", "erc1155", "both"], default="both", help="Padrão de contrato (default: both)")
    parser.add_argument("--run", choices=["static", "ramp-up", "both"], default="both", help="Tipo de execução (default: both)")
    parser.add_argument("--host", default=HOST, help=f"Host alvo (default: {HOST})")
    # parser.add_argument("--tx-build-weight", default=TX_BUILD_WEIGHT, help=f"Peso das rotas (default: {TX_BUILD_WEIGHT})")
    # parser.add_argument("--read-only-weight", default=READ_ONLY_WEIGHT, help=f"Peso das rotas (default: {READ_ONLY_WEIGHT})")

    # Main arguments
    parser.add_argument("--duration", type=float, nargs="+", default=[RUN_TIME], help=f"Duração do teste (default: {RUN_TIME})") 
    parser.add_argument("--users", type=int, nargs="+", default=[USERS], help=f"Número de usuários simultâneos (default: {USERS})")
    parser.add_argument("--step-users", type=int, nargs="+", default=[1], help="Número de usuários adicionados a cada incremento (ramp-up)")
    parser.add_argument("--interval-users", type=float, nargs="+", default=[1.0], help="Tempo entre incrementos de usuários (em segundos)")
    parser.add_argument("--interval-requests", type=float, default=1.0, help="Pausa entre requisições consecutivas (em segundos)")

    # Warm-up
    parser.add_argument("--warmup-users", type=int, default=1, help="Usuários no warm-up (default=1)")
    parser.add_argument("--warmup-duration", type=float, default=0, help="Duração do warm-up (default=15s)")
    parser.add_argument("--warmup-step-users", type=int, default=1, help="Incremento de usuários no warm-up (default=1)")
    parser.add_argument("--warmup-interval-users", type=float, default=1.0, help="Tempo entre incrementos no warm-up (default=1.0s)")
    parser.add_argument("--warmup-interval-requests", type=float, default=1.0, help="Pausa entre requisições no warm-up (default=1.0s)")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    results_directory = save.create_results_directory(timestamp=timestamp)
    log.setup_logging(results_directory=results_directory, verbosity=args.verbosity)

    # Combinations
    if args.type == "cartesian":
        combos = list(itertools.product(args.users, args.step_users, args.interval_users, args.duration))
    elif args.type == "paired":
        # combos = list(zip(args.users, args.step_users, args.interval_users, args.duration))
        max_len = max(len(args.users), len(args.step_users), len(args.interval_users), len(args.duration))

        users           = pad_list(args.users, max_len)
        step_users      = pad_list(args.step_users, max_len)
        interval_users  = pad_list(args.interval_users, max_len)
        duration        = pad_list(args.duration, max_len)

        combos = list(zip(users, step_users, interval_users, duration))

    
    contracts_to_run = ["erc721", "erc1155"] if args.contract == "both" else [args.contract]

    types_to_run = ["static", "ramp-up"] if args.run == "both" else [args.run]


    run_types = []
    if args.run in ("static", "both"):
        run_types.append("static")
    if args.run in ("ramp-up", "both"):
        run_types.append("ramp-up")

    total_runs_all = len(combos) * len(run_types) * len(contracts_to_run)


    log.print_global_run_plan_summary(
        mode=args.mode, 
        run_types=run_types, 
        contracts_to_run=contracts_to_run, 
        combos=combos, 
        interval_requests=args.interval_requests,
        total_runs_all=total_runs_all
    )

    # Warm-up execution
    if args.warmup_duration:
        contract =  contracts_to_run[0]
        run_type = types_to_run[0]
        
        logging.info(f"[WARM-UP] Run...")

        log.print_args_run(
            run_type=run_type,
            contract=contract,
            mode=args.mode,
            duration=args.warmup_duration,
            users=args.warmup_users,
            interval_requests=args.warmup_interval_requests,
            step_users=args.warmup_step_users if run_type == "ramp-up" else None,
            interval_users=args.warmup_interval_users if run_type == "ramp-up" else None,
        )

        warm_up_load_tester(
            run=run_type,
            host=args.host,
            contract=contract,
            mode=args.mode,
            duration=args.warmup_duration,
            users=args.warmup_users,
            interval_requests=args.warmup_interval_requests,
            step_users=args.warmup_step_users if run_type == "ramp-up" else None,
            interval_users=args.warmup_interval_users if run_type == "ramp-up" else None,
        )


    # Main execution loop (per contract)
    current_run = 0
    for contract in contracts_to_run:
        for idx, (users, step_users, interval_users, duration) in enumerate(combos, start=1):
            for run_type in run_types:
                current_run += 1
                logging.info(f"Run {current_run}/{total_runs_all}")

                log.print_args_run(
                    mode=args.mode, 
                    run_type=run_type, 
                    contract=contract, 
                    users=users, 
                    step_users=step_users, 
                    interval_users=interval_users, 
                    duration=duration, 
                    interval_requests=args.interval_requests
                )
                
                run_load_tester(
                    run=run_type,
                    current_run=current_run,
                    total_runs_all=total_runs_all,
                    output_dir=results_directory,
                    host=args.host,
                    contract=contract,
                    mode=args.mode,
                    duration=duration,
                    users=users,
                    interval_requests=args.interval_requests,
                    step_users=step_users if run_type == "ramp-up" else None,
                    interval_users=interval_users if run_type == "ramp-up" else None,
                )

    # Generate analysis plots
    try:
        plot_module.generate_plots(results_directory)
    except Exception as e:
        logging.error(f"Error generating plots: {e}")


if __name__ == "__main__":
    main()
