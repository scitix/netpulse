import sys

from netpulse.worker import fifo, node

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Missing worker type. \nUsage: worker.py <node|fifo>")
        sys.exit(1)

    if sys.argv[1] == "node":
        node.main()
    elif sys.argv[1] == "fifo":
        fifo.main()
    else:
        print("Invalid worker type")
        sys.exit(1)
