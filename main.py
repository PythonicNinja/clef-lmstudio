from clef_mlx import ClefFlash


def main() -> None:
    clef = ClefFlash()

    print("== single call ==")
    print(clef.chat("Say hello in one short sentence.", temperature=0.7))

    print("\n== streaming ==")
    for token in clef.stream("Count from 1 to 5.", system="Be concise."):
        print(token, end="", flush=True)
    print()


if __name__ == "__main__":
    main()
