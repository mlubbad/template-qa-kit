import argparse
import json

from .pipeline import process_folder


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tqk", description="Validate and consolidate Excel templates.")
    ap.add_argument("src", help="folder with country .xlsx templates")
    ap.add_argument("--out", default="out", help="output folder")
    a = ap.parse_args(argv)
    print(json.dumps(process_folder(a.src, a.out), indent=2))


if __name__ == "__main__":
    main()
