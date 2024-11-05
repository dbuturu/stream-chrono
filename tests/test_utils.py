from chronostreamer.utils import load_config


def test_load_config(tmp_path):
    # Create a temporary config file for testing
    config_file = tmp_path / "test_config.ini"
    config_file.write_text("[Icecast]\nURL = http://localhost\n")

    config = load_config(config_file)

    # Verify the configuration was loaded correctly
    assert config.get("Icecast", "URL") == "http://localhost"
