from reprocheck.cli import main

raise SystemExit(main(["ml-split", *__import__("sys").argv[1:]]))
