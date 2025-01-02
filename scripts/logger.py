import logging, logging.config
import os
from pathlib import Path
import functions
import sys

conf = functions.read_yaml('config.yml')


def setup_logging():
    format = "[%(asctime)s:%(funcName)s] <%(levelname)s> %(message)s"
    Path(conf['logs']['logs_dir']).mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO,
                        filename=f"{conf['logs']['logs_dir']}/{conf['logs']['logs_file']}",
                        format=format)
