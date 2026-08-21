from reprocheck.cli import main

raise SystemExit(main(["ml-calibrate", *__import__("sys").argv[1:]]))
