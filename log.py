import sys
import logging
from logging.handlers import RotatingFileHandler

SIZE=80

# def print_summary(results_directory, args):
#     logging.info("-" * SIZE)
#     logging.info("Starting load test:")
#     logging.info("")
#     logging.info(f"\tResults directory : {results_directory}")
#     logging.info(f"\tMode              : {args.mode}")
#     logging.info(f"\tCombination type  : {args.type}")
#     logging.info(f"\tContract(s)       : {args.contract}")
#     logging.info(f"\tHost              : {args.host}")
#     logging.info(f"\tUsers             : {args.users}")
#     logging.info(f"\tSpawn rate(s)     : {args.spawn_rate}")
#     logging.info(f"\tRun time(s)       : {args.run_time}")


# def print_run(contract, users, spawn_rate, run_time):    
#     logging.info(f"\t\tContract          : {contract}")
#     logging.info(f"\t\tUsers             : {users}")
#     logging.info(f"\t\tSpawn rate        : {spawn_rate}/s")
#     logging.info(f"\t\tRun time          : {run_time}s")


# def print_resume(run_directory, total_time):
#     logging.info("-" * SIZE)
#     logging.info("Test completed:")
#     logging.info("")
#     logging.info(f"\tTotal duration    : {total_time:.2f}s")
#     logging.info(f"\tResults saved to  : {run_directory}")



# def print_executions(combos):
#     logging.info("-" * SIZE)
#     logging.info(f"Total combinations to execute: {len(combos)}")
#     logging.info("")
#     for i, (u, r, t) in enumerate(combos, start=1):
#         logging.info(f"\tExecution {i:02d} : users={u}, spawn_rate={r}, run_time={t}")


def setup_logging(results_directory, verbosity):

    logging_filename = f"{results_directory}/log.log"

    log_format = "%(asctime)s\t---\t%(message)s"
    if verbosity == logging.DEBUG:
        log_format = "%(asctime)s\t---\t%(levelname)s {%(module)s} [%(funcName)s] %(message)s"

    # Garante que não existam handlers antigos (Locust e gevent registram alguns)
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.setLevel(verbosity)

    # Handler para o terminal
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(verbosity)
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)

    # Handler para arquivo com rotação
    file_handler = RotatingFileHandler(logging_filename, maxBytes=100000, backupCount=5)
    file_handler.setLevel(verbosity)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)

    logging.info(f"Initialized Logging:")
    logging.info(f"\tLevel    : {logging.getLevelName(verbosity)}")
    logging.info(f"\tLog file : {logging_filename}")
    logging.info("=" * SIZE)


def print_global_run_plan_summary(
    mode, 
    run_types, 
    contracts_to_run, 
    combos, 
    interval_requests,
    total_runs_all
):
    logging.info("=== Global Run Plan Summary ===")
    logging.info("")
    logging.info(f"- Mode                : {mode}")
    logging.info(f"- Run Types           : {run_types}")
    logging.info(f"- Contracts           : {contracts_to_run}")
    logging.info(f"- Users               : {[u for (u, _, _, _) in combos]}")
    logging.info(f"- Step Users          : {[s for (_, s, _, _) in combos]}")
    logging.info(f"- Interval Users(s)   : {[r for (_, _, r, _) in combos]}")
    logging.info(f"- Duration(s)         : {[d for (_, _, _, d) in combos]}")
    logging.info(f"- Interval Request(s) : {interval_requests}")
    logging.info(f"- Total runs          : {total_runs_all}")
    logging.info("")

    _print_runs(
        total_runs_all=total_runs_all,
        mode=mode,
        run_types=run_types,    
        contracts_to_run=contracts_to_run,
        combos=combos,
        interval_requests=interval_requests,
    )

def _print_runs(
    total_runs_all,
    mode, 
    run_types,
    contracts_to_run,
    combos,
    interval_requests
):
    run_number = 0
    for contract in contracts_to_run:
        for idx, (users, step_users, interval_users, duration) in enumerate(combos, start=1):
            for run_idx, run_type in enumerate(run_types):
                run_number += 1
                logging.info(f"- Run {run_number}/{total_runs_all}:")
                print_args_run(mode, run_type, contract, users, step_users, interval_users, duration, interval_requests)
                if not (run_number == total_runs_all):
                    logging.info("")
    logging.info("=" * SIZE)

def print_args_run(mode, run_type, contract, users, step_users, interval_users, duration, interval_requests):

    if run_type == "static":
        logging.info(f"   - Mode             : {mode}")
        logging.info(f"   - Run Type         : {run_type}")
        logging.info(f"   - Contract         : {contract}")
        logging.info(f"   - Users            : {users}")
        logging.info(f"   - Duration         : {duration}s")
        logging.info(f"   - Request Interval : {interval_requests}s")
    elif run_type == "ramp-up":
        logging.info(f"   - Mode             : {mode}")
        logging.info(f"   - Run Type         : {run_type}")
        logging.info(f"   - Contract         : {contract}")
        logging.info(f"   - Users            : {users}")
        logging.info(f"   - Step Users       : {step_users}")
        logging.info(f"   - Interval Users   : {interval_users}s")
        logging.info(f"   - Duration         : {duration}s")
        logging.info(f"   - Request Interval : {interval_requests}s")


def print_end_summary(
    total_requests,
    total_tasks,
    success,
    fails,
    total_time,
    rps,
    output_file,
    mode,
    contract,
    run_type: str,
    users: int,
    duration: float,
    interval_requests: float,
    step_users: int = None,
    interval_users: float = None,
):
    """Displays a summary of the execution with detailed metadata."""

    # total = len(results)
    # success = sum(1 for r in results if r["result"].startswith("success"))
    # fails = total - success

    # total = len(results)
    # success = sum(1 for r in results if r["result"].startswith("Success"))
    # fails = sum(1 for r in results if r["result"].startswith("Fail"))

    logging.info("=" * 60)
    logging.info("SUMMARY:")
    print_args_run(
        mode=mode, 
        run_type=run_type,
        contract=contract,
        users=users,
        step_users=step_users,
        interval_users=interval_users,
        duration=duration,
        interval_requests=interval_requests,
    )

    logging.info("-" * SIZE)
    logging.info(f"  - Total tasks      : {total_tasks}")
    logging.info(f"  - Total requests   : {total_requests}")
    logging.info(f"  - Successes        : {success}")
    logging.info(f"  - Failures         : {fails}")
    logging.info(f"  - Requests/seconds : {rps}")
    logging.info(f"  - Results save in  : {output_file}")
    
    if run_type == "static":
        logging.info(f"  - Static load test completed in {total_time}s")
    elif run_type == "ramp-up":
        logging.info(f"  - Ramp-up load test completed in {total_time}s")

    logging.info("=" * SIZE)
    

def print_global_summary(phase_label, workers, duration, global_api, global_bc, global_total, global_rps):
    logging.info("=" * 60)
    logging.info(f"GLOBAL SUMMARY ({phase_label.upper()}):")
    logging.info(f"  - Workers        : {workers}")
    logging.info(f"  - Duration       : {duration:.2f}s")
    logging.info(f"  - Total API      : {global_api}")
    logging.info(f"  - Total BC       : {global_bc}")
    logging.info(f"  - Total Requests : {global_total}")
    logging.info(f"  - Global RPS     : {global_rps:.2f}")
    logging.info("=" * 60)

    
# ==========================================================
# Warm-up Logging Utilities
# ==========================================================
class _WarmupFormatter(logging.Formatter):
    """Formatter que adiciona prefixo [Warm-up] nas mensagens."""
    def format(self, record):
        record.msg = f"[Warm-up] {record.msg}"
        return super().format(record)


def begin_warmup_logging():
    """
    Aplica prefixo [Warm-up] temporariamente, mantendo o mesmo formato
    e nível de detalhe do log principal.
    """
    root_logger = logging.getLogger()
    original_formatters = [h.formatter for h in root_logger.handlers]

    # Usa o mesmo formato da configuração principal
    log_format = "%(asctime)s\t---\t%(message)s"
    # if verbosity == logging.DEBUG:
        # log_format = "%(asctime)s\t---\t%(levelname)s {%(module)s} [%(funcName)s] %(message)s"

    warmup_formatter = _WarmupFormatter(log_format)

    for handler in root_logger.handlers:
        handler.setFormatter(warmup_formatter)

    return original_formatters


def end_warmup_logging(original_formatters):
    """Restaura os formatters originais."""
    root_logger = logging.getLogger()
    for handler, fmt in zip(root_logger.handlers, original_formatters):
        handler.setFormatter(fmt)
