import os
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
from plot.plot_read_latency import plot_read_latency
from plot.plot_tx_build_latency import plot_tx_build_latency
# from plot.plot_all_routes import plot_all_routes_quantity, plot_all_routes_latency

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
    
    # Define and create output directory for plots
    output_dir = os.path.join(root_dir, "plots")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Aggregated Standard Plots (latency, throughput, success count)
    df = scan_results(root_dir)
    if not df.empty and df['users'].nunique() > 1:
        plot_latency(df, output_dir)
        plot_success_count(df, output_dir)

    df_tp = scan_results_throughput(root_dir)
    if not df_tp.empty and df_tp['users'].nunique() > 1:
        plot_throughput(df_tp, output_dir)

    # 2. Stacked Plot (transaction breakdown)
    create_txbuild_stacked_plot(root_dir, output_dir)
    
    # 3. Grouped Plots (Linear and Log Scale)
    create_txbuild_grouped_plot(root_dir, output_dir, use_log_scale=False)  # Linear scale
    create_txbuild_grouped_plot(root_dir, output_dir, use_log_scale=True)   # Log scale

    # 4. RPS Comparison
    plot_rps_comparison(root_dir, output_dir)

    # 5. Success/Fail Plot
    plot_success_fail(root_dir, output_dir)

    # 6. Read Routes Plot
    plot_read_routes(root_dir, output_dir)

    # 7. Write Routes Plot (Tx-Build)
    plot_tx_build_routes(root_dir, output_dir)

    # 8. Read Routes Latency Plot
    plot_read_latency(root_dir, output_dir)

    # 9. Write Routes Latency Plot (Tx-Build)
    plot_tx_build_latency(root_dir, output_dir)

    # # 10. Summary All Routes Quantity
    # plot_all_routes_quantity(root_dir, output_dir)

    # # 11. Summary All Routes Latency
    # plot_all_routes_latency(root_dir, output_dir)

    logging.info(f"Plots generated success in: {output_dir}")

# Export main function
__all__ = ['generate_plots']
