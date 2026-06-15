import traceback
import sys

try:
    import benchmark_cores
    benchmark_cores.main()
except Exception as e:
    with open("traceback.txt", "w") as f:
        f.write(f"Exception: {e}\n\n")
        traceback.print_exc(file=f)
    print("Crashed! Traceback written to traceback.txt")
    sys.exit(1)
