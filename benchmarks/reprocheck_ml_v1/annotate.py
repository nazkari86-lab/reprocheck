"""Validate source-bound annotations; annotation itself remains a blinded human task."""

from reprocheck.cli import main

raise SystemExit(main(["ml-corpus-validate", *__import__("sys").argv[1:]]))
