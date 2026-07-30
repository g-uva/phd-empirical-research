import importlib
import utils.parse
import utils.plot

importlib.reload(utils.parse)
from utils.parse import *
from utils.plot import *

target_dir = "exp_kv_cache"
csv_file = "exp_kv_cache/2025-10-23-01-23-52_kv_cache_anl_LLaMA3.2-1B/l3d_cache_refill/trace_LLaMA3.2-1B_f16_t2_p5.csv"
df = create_perf_df_from_trace(csv_file)
df_diff = compute_type10_15_diff(df)
df_iter = parse_ops_all_iters(df)

df_kq = compute_sum_elapsed_by_name(df_iter, "kq-")

df_kqv = compute_sum_elapsed_by_name(df_iter, "kqv-")

plot_combined_graph(df_diff, df_kq, df_kqv, save_path="figures/kv_cache_anl.pdf")
