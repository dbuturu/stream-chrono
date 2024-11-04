import os
from chrono_streamer.utils import retry_on_failure


@retry_on_failure()
def sync_to_remote_server(remote_path):
    os.system(f"rsync -avz recordings/ {remote_path}")
