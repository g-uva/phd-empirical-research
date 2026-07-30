import subprocess
import argparse
import os


def get_pids_from_name(name):
    try:
        res = subprocess.run(["pgrep", "-f", name], stdout=subprocess.PIPE, text=True)
        pids = [int(pid) for pid in res.stdout.split()]
        this_pid = os.getpid()
        if this_pid in pids:
            pids.remove(this_pid)
        return pids
    except subprocess.CalledProcessError:
        print(f"Not found this cmd {name}")
        return []


def get_children_pids(parent_pid: int):
    children_threads_ids = []
    try:
        cmd = ["ps", "-T", "-p", str(parent_pid)]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
        ctx = res.stdout.splitlines()
        # print(ctx)
        for line in ctx[1:]:
            row = line.split()
            children_threads_ids.append(int(row[1]))
    except subprocess.CalledProcessError:
        print(f"No such pid {parent_pid}")
        return []
    return children_threads_ids


def get_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        dest="cmd", metavar="C", default="None", help="The name of command line"
    )
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    cmd_name = args.cmd
    pids = get_pids_from_name(cmd_name)
    print(f"The pid of cmd {cmd_name} is {pids[0]}")
    spids = get_children_pids(pids[0])
    print(spids)


if __name__ == "__main__":
    main()
