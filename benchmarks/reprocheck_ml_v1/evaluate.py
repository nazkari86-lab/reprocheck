from reprocheck.cli import main

raise SystemExit(main(["ml-evaluate", *__import__("sys").argv[1:]]))
