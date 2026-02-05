import os
import datetime
import argparse
import itertools
import logging

# Internal imports
import log
import save
from stats import Stats
from load_tester import LoadTester
from users.user_erc721 import UserERC721
from users.user_erc1155 import UserERC1155
from config import (
    TYPE,
    CONTRACT,
    RUN,
    USERS, 
    RESULTS_DIR, 
    MODES, 
    HOST, 
    DURATION, 
    STEP_USERS, 
    INTERVAL_USERS, 
    INTERVAL_REQUEST, 
    REPEAT,
    WARMUP_USERS,
    WARMUP_DURATION,
    WARMUP_STEP_USERS,
    WARMUP_INTERVAL_USERS,
    WARMUP_INTERVAL_REQUESTS,
)
from plot.plot import generate_plots

def execute(run, phase, run_directory, repetition_index=None):

    phase_dir = f"{run_directory}/{phase}"
    os.makedirs(phase_dir, exist_ok=True)
    
    # Determine output filename based on repetition
    if repetition_index is not None:
        filename = f"out_rep-{repetition_index + 1}.csv"
    else:
        filename = "out.csv"
        
    output_file = f"{phase_dir}/{filename}"
    
    run_data = run(phase, output_file)
    
    save.save_all_outputs(run_data, phase, output_file)


def run_load_tester(
    run,
    current_run,
    total_runs,
    repeat,
    output_dir, 
    host,
    contract,
    mode,
    duration,
    users, 
    interval_requests,
    step_users=None, 
    interval_users=None,
    repetition_index=None
):

    run_label = run.upper()
    
    if run == "static":
        run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_interval-requests-{interval_requests}"
    elif run == "ramp-up":
        run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_step_users-{step_users}_interval_users-{interval_users}_interval-requests-{interval_requests}"
    else:
        logging.error(f"Invalid run type: {run}")
        return

    run_directory = save.create_directory(output_dir, run_directory_name)

    args_file = save.save_run_args(
        run_directory=run_directory,
        host=host,
        mode=mode,
        contract=contract,
        run=run,
        duration=duration,
        users=users,
        step_users=step_users,
        interval_users=interval_users,
        interval_requests=interval_requests,
        repeat=repeat,
    )

    log.print_args_run(
        host=host,
        mode=mode,
        repeat=repeat,
        contract=contract, 
        run=run, 
        duration=duration,
        users=users, 
        step_users=step_users, 
        interval_users=interval_users, 
        interval_requests=interval_requests,
        args_file=args_file,
    )

    if contract == "erc721":
        user_class = UserERC721  
    elif contract == "erc1155": 
        user_class = UserERC1155
    else:
        logging.error(f"Invalid contract type: {contract}")
        return

    logging.info("-" * log.SIZE)
    logging.info(f"[{run_label}] Starting users configuration (Run {current_run}/{total_runs})...")
    logging.info("")

    tester = LoadTester(
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

    logging.info("")
    logging.info(f"[{run_label}] Finished users configurations (Run {current_run}/{total_runs}).")
    logging.info("-" * log.SIZE)
    logging.info(f"[{run_label}] Starting load test (Run {current_run}/{total_runs})...")
    logging.info("")

    if run == "static":
        execute(
            run=tester.run_static_load,
            phase="api-tx-build", 
            run_directory=run_directory, 
            repetition_index=repetition_index
        )
        execute(
            run=tester.run_static_load,
            phase="api-read-only", 
            run_directory=run_directory,
            repetition_index=repetition_index
        )
    elif run == "ramp-up":
        execute(
            run=tester.run_ramp_up_load, 
            phase="api-tx-build",
            run_directory=run_directory,
            repetition_index=repetition_index
        )
        execute(
            run=tester.run_ramp_up_load,
            phase="api-read-only",
            run_directory=run_directory,
            repetition_index=repetition_index
        )

    logging.info("")
    logging.info(f"[{run_label}] Finished load test (Run {current_run}/{total_runs}).")
    logging.info("=" * log.SIZE)
    
    return run_directory

def run_warmup(
    run, 
    host,
    contract,
    mode,
    duration,
    users, 
    interval_requests,
    step_users=None, 
    interval_users=None
):
    run_label = f"WARM-UP][{run.upper()}"
    
    if contract == "erc721":
        user_class = UserERC721  
    elif contract == "erc1155": 
        user_class = UserERC1155
    else:
        logging.error(f"Invalid contract type: {contract}")
        return
    
    logging.info(f"[{run_label}] Starting users configuration...")
    logging.info("")

    tester = LoadTester(
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

    logging.info("")
    logging.info(f"[{run_label}] Finished users configurations.")
    logging.info("-" * log.SIZE)
    logging.info(f"[{run_label}] Starting load test...")
    logging.info("")

    if run == "static":
        tester.run_static_load(phase="api-tx-build")
        tester.run_static_load(phase="api-read-only")
    elif run == "ramp-up":
        tester.run_ramp_up_load(phase="api-tx-build")
        tester.run_ramp_up_load(phase="api-read-only")
    
    logging.info("")
    logging.info(f"[{run_label}] Finished load test.")
    logging.info("=" * log.SIZE)
    
def pad_list(lst, target_len):
    if len(lst) == 1:
        return lst * target_len
    return lst

def main():
    parser = argparse.ArgumentParser(description="Load testing")

    help_msg = "verbosity logging level (INFO=%d DEBUG=%d)" % (logging.INFO, logging.DEBUG)
    parser.add_argument("--verbosity", "-v", help=help_msg, default=logging.INFO, type=int)

    parser.add_argument("--plot", type=str, help="Gera gráficos a partir dos arquivos CSV de resultados existentes (caminho do diretório).")

    # Configuration arguments
    parser.add_argument("--mode", type=str, choices=MODES, default=MODES[0], help=f"Modo de execução (default: {MODES[0]})")
    parser.add_argument("--type", choices=TYPE, default=TYPE[1], help=f"Define o modo de combinação dos parâmetros (default: {TYPE[1]})")
    parser.add_argument("--contract", choices=CONTRACT, default=CONTRACT[2], help=f"Padrão de contrato (default: {CONTRACT[2]})")
    parser.add_argument("--run", choices=RUN, default=RUN[2], help=f"Tipo de execução (default: {RUN[2]})")
    parser.add_argument("--host", default=HOST, help=f"Host alvo (default: {HOST})")
    # parser.add_argument("--tx-build-weight", default=TX_BUILD_WEIGHT, help=f"Peso das rotas (default: {TX_BUILD_WEIGHT})")
    # parser.add_argument("--read-only-weight", default=READ_ONLY_WEIGHT, help=f"Peso das rotas (default: {READ_ONLY_WEIGHT})")

    # Main arguments
    parser.add_argument("--duration", type=float, nargs="+", default=DURATION, help=f"Duração do teste (segundos) (default: {DURATION})") 
    parser.add_argument("--users", type=int, nargs="+", default=USERS, help=f"Número de usuários simultâneos (default: {USERS})")
    parser.add_argument("--step-users", type=int, nargs="+", default=STEP_USERS, help=f"Número de usuários adicionados a cada incremento (apenas no ramp-up) (default: {STEP_USERS})")
    parser.add_argument("--interval-users", type=float, nargs="+", default=INTERVAL_USERS, help=f"Tempo entre incrementos de usuários (segundos) (apenas no ramp-up) (default: {INTERVAL_USERS})")
    parser.add_argument("--interval-requests", type=float, default=INTERVAL_REQUEST, help=f"Pausa entre requisições consecutivas (segundos) (default: {INTERVAL_REQUEST})")
    
    # Repetition
    parser.add_argument("--repeat", type=int, default=REPEAT, help=f"Número de vezes para repetir cada configuração de execução (default: {REPEAT})")

    # Warm-up
    parser.add_argument("--warmup-duration", type=float, default=WARMUP_DURATION, help=f"Duração do warm-up (default: {WARMUP_DURATION})")
    parser.add_argument("--warmup-users", type=int, default=WARMUP_USERS, help=f"Usuários no warm-up (default: {WARMUP_USERS})")    
    parser.add_argument("--warmup-step-users", type=int, default=WARMUP_STEP_USERS, help=f"Incremento de usuários no warm-up (default: {WARMUP_STEP_USERS})")
    parser.add_argument("--warmup-interval-users", type=float, default=WARMUP_INTERVAL_USERS, help=f"Tempo entre incrementos no warm-up (segundos) (default: {WARMUP_INTERVAL_USERS})")
    parser.add_argument("--warmup-interval-requests", type=float, default=WARMUP_INTERVAL_REQUESTS, help=f"Pausa entre requisições no warm-up (segundos) (default: {WARMUP_INTERVAL_REQUESTS})")

    args = parser.parse_args()

    # If --plot is provided, only generate plots and exit
    if args.plot:
        if not os.path.exists(args.plot):
            print(f"Error: Directory '{args.plot}' not found.")
            return
        
        try:
            # First, reconsolidate statistics from existing out_rep-*.csv files
            print("=" * 80)
            print("Reconsolidating statistics from existing test results...")
            print("")
            
            # Walk through the results directory to find all test run directories
            for root, dirs, files in os.walk(args.plot):
                # Check if this directory contains args_run.json (indicates a test run directory)
                if "args_run.json" in files:
                    # Check for api-tx-build and api-read-only subdirectories
                    for phase in ["api-tx-build", "api-read-only"]:
                        phase_dir = os.path.join(root, phase)
                        if os.path.isdir(phase_dir):
                            # Check if there are out_rep-*.csv files
                            out_files = [f for f in os.listdir(phase_dir) 
                                       if f.startswith("out") and f.endswith(".csv")]
                            if out_files:
                                print(f"Consolidating {phase} in {root}")
                                save.consolidate_stats(root, phase)
            
            print("")
            print("Statistics reconsolidation complete.")
            print("=" * 80)
            print("")
            
            # Now generate plots
            generate_plots(args.plot)
        except Exception as e:
            print(f"Error generated plots: {e}")
            import traceback
            traceback.print_exc()
        return

    timestamp = datetime.datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    results_directory = save.create_results_directory(timestamp=timestamp)
    log.setup_logging(results_directory=results_directory, verbosity=args.verbosity)

    # Combinations
    if args.type == "cartesian":
        combos = list(itertools.product(args.users, args.step_users, args.interval_users, args.duration))
    elif args.type == "paired":
        max_len = max(len(args.users), len(args.step_users), len(args.interval_users), len(args.duration))

        users           = pad_list(args.users, max_len)
        step_users      = pad_list(args.step_users, max_len)
        interval_users  = pad_list(args.interval_users, max_len)
        duration        = pad_list(args.duration, max_len)

        combos = list(zip(users, step_users, interval_users, duration))

    contracts_to_run = ["erc721", "erc1155"] if args.contract == "both" else [args.contract]

    runs = ["static", "ramp-up"] if args.run == "both" else [args.run]


    total_runs = len(combos) * len(runs) * len(contracts_to_run)
    total_runs_all = total_runs * args.repeat


    log.print_global_run_plan_summary(
        host=args.host,
        mode=args.mode,
        repeat=args.repeat,
        runs=runs,
        contracts=contracts_to_run,
        combos=combos,
        interval_requests=args.interval_requests,
        total_runs=total_runs,
        total_runs_all=total_runs_all
    )

    # Warm-up execution
    if args.warmup_duration:
        contract =  contracts_to_run[0]
        run = runs[0]
        
        run_warmup(
            run=run,
            host=args.host,
            contract=contract,
            mode=args.mode,
            duration=args.warmup_duration,
            users=args.warmup_users,
            interval_requests=args.warmup_interval_requests,
            step_users=args.warmup_step_users if run == "ramp-up" else None,
            interval_users=args.warmup_interval_users if run == "ramp-up" else None,
        )


    # Main execution loop (per contract)
    current_run = 0
    for contract in contracts_to_run:
        for idx, (users, step_users, interval_users, duration) in enumerate(combos, start=1):
            for run in runs:
                current_run += 1
                run_dir = None
                for rep in range(0, args.repeat):
                    logging.info(f"Run {current_run}/{total_runs} (Repetition {rep+1}/{args.repeat})")
                    
                    run_dir = run_load_tester(
                        run=run,
                        current_run=current_run,
                        total_runs=total_runs,
                        repeat=args.repeat,
                        output_dir=results_directory,
                        host=args.host,
                        contract=contract,
                        mode=args.mode,
                        duration=duration,
                        users=users,
                        interval_requests=args.interval_requests,
                        step_users=step_users if run == "ramp-up" else None,
                        interval_users=interval_users if run == "ramp-up" else None,
                        repetition_index=rep
                    )

                # After all repetitions for this config, consolidate stats
                if run_dir:
                    save.consolidate_stats(run_dir, "api-tx-build")
                    save.consolidate_stats(run_dir, "api-read-only")

    # Generate analysis plots
    try:
        generate_plots(results_directory)
    except Exception as e:
        logging.error(f"Error generating plots: {e}")


if __name__ == "__main__":
    main()
