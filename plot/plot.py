
import logging

# Internal imports
from log import SIZE
from plot.common import scan_results, scan_results_throughput
from plot.plot_latency import plot_latency
from plot.plot_throughput import plot_throughput
from plot.plot_success_count import plot_success_count
from plot.plot_txbuild_stacked import create_txbuild_stacked_plot
from plot.plot_txbuild_grouped import create_txbuild_grouped_plot
from plot.plot_rps_comparison import plot_rps_comparison
from plot.plot_success_fail import plot_success_fail
from plot.plot_read_routes import plot_read_routes
from plot.plot_tx_build_routes import plot_tx_build_routes

def generate_plots(root_dir):
    """
    Generate all plots for a load testing session.
    
    This is the main entry point for plot generation. It orchestrates
    the creation of all visualization types.
    
    Args:
        root_dir: Root directory containing test results
    """
    logging.info("=" * SIZE)
    logging.info(f"Generating plots: ")
    # logging.info(f"Generating plots for: {args.plot}")
    logging.info("")
    
    # 1. Aggregated Standard Plots (latency, throughput, success count)
    df = scan_results(root_dir)
    if not df.empty and df['users'].nunique() > 1:
        plot_latency(df, root_dir)
        plot_success_count(df, root_dir)

    df_tp = scan_results_throughput(root_dir)
    if not df_tp.empty and df_tp['users'].nunique() > 1:
        plot_throughput(df_tp, root_dir)

    # 2. Stacked Plot (transaction breakdown)
    create_txbuild_stacked_plot(root_dir, root_dir)
    
    # 3. Grouped Plots (Linear and Log Scale)
    create_txbuild_grouped_plot(root_dir, root_dir, use_log_scale=False)  # Linear scale
    create_txbuild_grouped_plot(root_dir, root_dir, use_log_scale=True)   # Log scale

    # 4. RPS Comparison
    plot_rps_comparison(root_dir, root_dir)

    # 5. Success/Fail Plot
    plot_success_fail(root_dir, root_dir)

    # 6. Read Routes Plot
    plot_read_routes(root_dir, root_dir)

    # 7. Write Routes Plot (Tx-Build)
    plot_tx_build_routes(root_dir, root_dir)

    logging.info(f"Plots genareted success in: {root_dir}")

# Export main function
__all__ = ['generate_plots']
