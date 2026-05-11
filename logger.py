def section(title):

    print("\n" + "="*70)
    print(title)
    print("="*70)


def sys_log(msg):

    print(f"[SYS] {msg}")


def proof_log(msg):

    print(f"[PROOF] {msg}")


def benchmark_log(msg):

    print(f"[BENCHMARK] {msg}")


def stage_log(stage, msg):

    print(f"[{stage}] {msg}")