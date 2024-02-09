from typing import Optional

from pysonnet.cli import main


def run(prog: Optional[str] = None) -> None:
    main(prog=prog)


if __name__ == "__main__":
    run(prog="pysonnet")
