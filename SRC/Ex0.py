"""Command-line entry point for the 3D plane projection program."""

if __package__:
    from .cli import main
else:
    from cli import main


if __name__ == "__main__":
    raise SystemExit(main())
