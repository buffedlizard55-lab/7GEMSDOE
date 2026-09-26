"""Compatibility entry point requested in the brief: verify, then extract CPU features."""
from verify_data import main as verify
from extract_features import main as extract

if __name__ == "__main__":
    if verify():
        raise SystemExit(1)
    extract()
