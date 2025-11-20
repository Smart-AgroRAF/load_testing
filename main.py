import os
import datetime
import argparse
import itertools
import logging
from datetime import datetime

# Internal imports
import log
import save
from users.user_erc721 import UserERC721
from users.user_erc1155 import UserERC1155
from load_tester import LoadTester
from config import USERS, RESULTS_DIR, MODES, HOST, RUN_TIME, SPAWN_RATE


def run_static_load(
    current_run,
    total_runs_all,
    output_dir, 
    host,
    contract,
    mode, 
    duration, 
    users,
    interval_requests
):
    run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_interval-requests-{interval_requests}"
    run_directory = save.create_directory(output_dir, run_directory_name)
    output_file = f"{run_directory}/out.csv"

    user_class = UserERC721 if contract == "erc721" else UserERC1155

    logging.info("-" * log.SIZE)
    logging.info(f"[STATIC] Starting users configuration (Run {current_run}/{total_runs_all})...")
    logging.info("")

    tester = LoadTester(
        output_file=output_file,
        host=host,
        mode=mode,
        contract=contract,
        duration=duration,
        user_cls=user_class, 
        users=users,        
        interval_requests=interval_requests,
    )
    
    logging.info(f"[STATIC] Finished users configuration (Run {current_run}/{total_runs_all}).")

    logging.info("-" * log.SIZE)
    logging.info(f"[STATIC] Starting load test (Run {current_run}/{total_runs_all})...")
    logging.info("")
    
    tester.run_static_load()

    logging.info(f"[STATIC] Finished load test (Run {current_run}/{total_runs_all}).")

def run_ramp_up_load(
    current_run,
    total_runs_all,
    output_dir, 
    host,
    contract,
    mode,
    duration,
    users, 
    step_users, 
    interval_users, 
    interval_requests
):
    run_directory_name = f"{contract}/mode-{mode}_duration-{duration}_users-{users}_step_users-{step_users}intervalp_users-{interval_users}_interval-requests-{interval_requests}"
    run_directory = save.create_directory(output_dir, run_directory_name)
    output_file = f"{run_directory}/out.csv"

    user_class = UserERC721 if contract == "erc721" else UserERC1155


    logging.info("-" * log.SIZE)
    logging.info(f"[RAMP-UP] Starting users configuration (Run {current_run}/{total_runs_all})...")
    logging.info("")

    tester = LoadTester(
        output_file=output_file,
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

    logging.info(f"[RAMP-UP] Finished users configurations (Run {current_run}/{total_runs_all}).")


    logging.info("-" * log.SIZE)
    logging.info(f"[RAMP-UP] Starting load test (Run {current_run}/{total_runs_all})...")
    logging.info("")

    tester.run_ramp_up_load()

    logging.info(f"[RAMP-UP] Finished load test (Run {current_run}/{total_runs_all}).")

# def warm_up_static_load(
#     host,
#     contract,
#     mode, 
#     duration, 
#     users,
#     interval_requests
# ):
#     user_class = UserERC721 if contract == "erc721" else UserERC1155

#     tester = LoadTester(user_cls=user_class, host=host, mode=mode, contract=contract)
#     tester.run_static_load(
#         output_file=None,
#         users=users,
#         duration=duration,
#         interval_requests=interval_requests,
#     )


# def warm_up_ramp_up_load(
#     host,
#     contract,
#     mode,
#     duration,
#     users, 
#     step_users, 
#     interval_users, 
#     interval_requests
# ):
#     user_class = UserERC721 if contract == "erc721" else UserERC1155

#     tester = LoadTester(user_cls=user_class, host=host, mode=mode)

#     tester = LoadTester(user_cls=user_class, host=host, mode=mode, contract=contract)
#     tester.run_ramp_up_load(
#         output_file=None,
#         duration=duration,
#         users=users,
#         step_users=step_users,
#         interval_users=interval_users,        
#         interval_requests=interval_requests
#     )


def main():
    parser = argparse.ArgumentParser(description="Load testing")

    help_msg = "verbosity logging level (INFO=%d DEBUG=%d)" % (logging.INFO, logging.DEBUG)
    parser.add_argument("--verbosity", "-v", help=help_msg, default=logging.INFO, type=int)

    parser.add_argument("--plot", type=str, help="Gera gráficos a partir dos arquivos CSV de resultados existentes.")

    # Configuration arguments
    parser.add_argument("--mode", type=str, default=MODES[0], choices=MODES, help=f"Modo de execução (default: {MODES[0]})")
    parser.add_argument("--type", choices=["cartesian", "paired"], default="paired", help="Define o modo de combinação dos parâmetros.")
    parser.add_argument("--contract", choices=["erc721", "erc1155", "both"], default="both", help="Standards the contract")
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
    parser.add_argument("--warmup", action="store_true", help="Executa um warm-up antes dos testes principais")
    parser.add_argument("--warmup-users", type=int, default=2, help="Usuários no warm-up (default=2)")
    parser.add_argument("--warmup-duration", type=int, default=15, help="Duração do warm-up (default=15s)")
    parser.add_argument("--warmup-spawn-rate", type=float, default=1.0, help="Spawn rate no warm-up (default=1.0)")

    args = parser.parse_args()

    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    results_directory = save.create_results_directory(timestamp=timestamp)
    log.setup_logging(results_directory=results_directory, verbosity=args.verbosity)

    # Combinations
    if args.type == "cartesian":
        combos = list(itertools.product(args.users, args.step_users, args.interval_users, args.duration))
    elif args.type == "paired":
        combos = list(zip(args.users, args.step_users, args.interval_users, args.duration))

    # Corrige caso alguma lista tenha só um elemento
    # if len(combos) == 0:
        # combos = [(args.users[0], args.step_users[0], args.interval_users[0], args.run_time[0])]

    contracts_to_run = ["erc721", "erc1155"] if args.contract == "both" else [args.contract]

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

    # Main execution loop (per contract)
    for contract in contracts_to_run:
        current_run = 0
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

                if run_type == "static":
                    run_static_load(
                        current_run=current_run,
                        total_runs_all=total_runs_all,
                        output_dir=results_directory,
                        host=args.host,
                        contract=contract,
                        mode=args.mode,
                        duration=duration,
                        users=users,
                        interval_requests=args.interval_requests,
                    )

                elif run_type == "ramp-up":
                    run_ramp_up_load(
                        current_run=current_run,
                        total_runs_all=total_runs_all,
                        output_dir=results_directory,
                        host=args.host,
                        contract=contract,
                        mode=args.mode,
                        duration=duration,
                        users=users,
                        step_users=step_users,
                        interval_users=interval_users,
                        interval_requests=args.interval_requests,
                    )


if __name__ == "__main__":
    main()
