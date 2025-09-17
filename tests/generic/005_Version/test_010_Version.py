"""
    test SSD
"""

def test_01_version():
    from molass import get_version
    version = get_version(toml_only=True)     # to ensure that the current repository is used
    print(type(version), version)
    assert version >= '0.0.2', f"Version {version} is not valid, expected at least 0.0.2"