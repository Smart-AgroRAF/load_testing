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
from config import USERS, RESULTS_DIR, MODES, HOST, RUN_TIME, SPAWN_RATE
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
    is_warmup=False,
):
  
    if is_warmup:
        run_label = f"WARM-UP][{run.upper()}"
        logging.info("-" * log.SIZE)
        logging.info(f"[{run_label}] Starting users configuration...")
        logging.info("")
    else:
        run_label = run.upper()
        
        if run == "static":
            run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_interval-requests-{interval_requests}"
        elif run == "ramp-up":
            run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_step_users-{step_users}_interval_users-{interval_users}_interval-requests-{interval_requests}"
        else:
            logging.error(f"Invalid run type: {run}")
            return

        run_directory = save.create_directory(output_dir, run_directory_name)
        output_file = f"{run_directory}/out.csv"

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
        )

        log.print_args_run(
            host=host,
            mode=mode, 
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

    if not is_warmup:
        logging.info("-" * log.SIZE)
        logging.info(f"[{run_label}] Starting users configuration (Run {current_run}/{total_runs_all})...")
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

    if is_warmup:
        logging.info("")
        logging.info(f"[{run_label}] Finished users configurations.")
        logging.info("-" * log.SIZE)
        logging.info(f"[{run_label}] Starting load test...")
        logging.info("")
    else:
        logging.info("")
        logging.info(f"[{run_label}] Finished users configurations (Run {current_run}/{total_runs_all}).")
        logging.info("-" * log.SIZE)
        logging.info(f"[{run_label}] Starting load test (Run {current_run}/{total_runs_all})...")
        logging.info("")

    if not is_warmup:
        if run == "static":
            execute_and_generate_stats(tester.run_static_load, "api-tx-build", run_directory)
            execute_and_generate_stats(tester.run_static_load, "api-read-only", run_directory)
        elif run == "ramp-up":
            execute_and_generate_stats(tester.run_ramp_up_load, "api-tx-build", run_directory)
            execute_and_generate_stats(tester.run_ramp_up_load, "api-read-only", run_directory)
    else:
         if run == "static":
            tester.run_static_load(phase="api-tx-build")
            tester.run_static_load(phase="api-read-only")
         elif run == "ramp-up":
            tester.run_ramp_up_load(phase="api-tx-build")
            tester.run_ramp_up_load(phase="api-read-only")
    
    if is_warmup:
        logging.info(f"[{run_label}] Finished load test.")
    else:
        logging.info(f"[{run_label}] Finished load test (Run {current_run}/{total_runs_all}).")
    logging.info("")




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
    
    # Repetition
    parser.add_argument("--repeat", type=int, default=1, help="Número de vezes para repetir cada configuração de execução (default: 1)")

    # Warm-up
    parser.add_argument("--warmup-users", type=int, default=1, help="Usuários no warm-up (default=1)")
    parser.add_argument("--warmup-duration", type=float, default=0, help="Duração do warm-up (default=15s)")
    parser.add_argument("--warmup-step-users", type=int, default=1, help="Incremento de usuários no warm-up (default=1)")
    parser.add_argument("--warmup-interval-users", type=float, default=1.0, help="Tempo entre incrementos no warm-up (default=1.0s)")
    parser.add_argument("--warmup-interval-requests", type=float, default=1.0, help="Pausa entre requisições no warm-up (default=1.0s)")

    args = parser.parse_args()

    # If --plot is provided, only generate plots and exit
    if args.plot:
        if not os.path.exists(args.plot):
            logging.info(f"Error: Directory '{args.plot}' not found.")
            return
        
        try:
            generate_plots(args.plot)
        except Exception as e:
            logging.info(f"Error generated plots: {e}")
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
        
        logging.info(f"[WARM-UP] Run...")

        # log.print_args_run(
        #     run_type=run_type,
        #     contract=contract,
        #     mode=args.mode,
        #     duration=args.warmup_duration,
        #     users=args.warmup_users,
        #     interval_requests=args.warmup_interval_requests,
        #     step_users=args.warmup_step_users if run_type == "ramp-up" else None,
        #     interval_users=args.warmup_interval_users if run_type == "ramp-up" else None,
        # )

        run_load_tester(
            run=run,
            current_run=None,
            total_runs_all=None,
            output_dir=None,
            host=args.host,
            contract=contract,
            mode=args.mode,
            duration=args.warmup_duration,
            users=args.warmup_users,
            interval_requests=args.warmup_interval_requests,
            step_users=args.warmup_step_users if run == "ramp-up" else None,
            interval_users=args.warmup_interval_users if run == "ramp-up" else None,
            is_warmup=True
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
