from unittest.mock import patch
from chrono_streamer.sync_manager import sync_to_remote_server


@patch("chrono_streamer.sync_manager.os.system")
def test_sync_to_remote_server(mock_system):
    # Mock `os.system` to prevent real rsync execution
    sync_to_remote_server()

    # Assert `os.system` was called with the correct command
    mock_system.assert_called_once_with("rsync -avz recordings/ /path/to/remote")
