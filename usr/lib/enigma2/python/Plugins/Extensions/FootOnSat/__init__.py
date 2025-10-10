import os

log_path = '/tmp/FootOnSat.log'
if os.path.exists(log_path):
    os.remove(log_path)

__version__ = 3.0
