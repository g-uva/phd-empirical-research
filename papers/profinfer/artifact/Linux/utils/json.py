import json
import time
import numpy as np
from .dirs import create_dirs


def write_to_json(json_dict: dict, json_file: str, include_np: bool = False):
    if include_np:
        for key, val in json_dict.items():
            if isinstance(val, np.ndarray):
                json_dict[key] = val.tolist()
    with open(json_file, "w") as f:
        json.dump(json_dict, f, indent=4)


def read_from_json(config_file: str, cat: str = "None", create_dir: bool = False):
    with open(config_file, "r") as json_file:
        config = json.load(json_file)
    if create_dir:
        exp_name = config["exp"]["name"]
        current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
        exp_dir = f"{config['exp']['dir']}/{current_time}_{exp_name}"
        config_dir = f"{exp_dir}/config"
        create_dirs([config_dir])
        write_to_json(config, f"{config_dir}/{config_file.split('/')[-1]}")
        config["exp_dir"] = exp_dir
    if cat != "None" and cat in config.keys():
        config = config[cat]
    return config
