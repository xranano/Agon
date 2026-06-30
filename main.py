from pathlib import Path

from config import DATA_DIR, RESULTS_DIR


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    problems_path = DATA_DIR / "problems.json"
    print(f"existentiAIsm pipeline scaffold ready.")
    print(f"Problems file: {problems_path}")
    print(f"Results directory: {RESULTS_DIR}")


if __name__ == "__main__":
    main()

