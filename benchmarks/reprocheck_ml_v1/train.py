from reprocheck.cli import main

raise SystemExit(main(["ml-train", *__import__("sys").argv[1:]]))
