import argparse

def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=str, default="None", help="The name of command line")
    parser.add_argument("--start_line", type=int, default=None, help="The start line of freezer log")
    parser.add_argument("--perf_parent", type=bool, default=True, help="Perf record parent thread or not")
    parser.add_argument("--cmd_name", type=str, default="llama-cli", help="The name of app cmd")
    args = parser.parse_args()
    return args