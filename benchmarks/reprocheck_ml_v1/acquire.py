"""Validate a completed provenance corpus after an independently logged acquisition."""

from reprocheck.cli import main

raise SystemExit(main(["ml-corpus-validate", *__import__("sys").argv[1:]]))
