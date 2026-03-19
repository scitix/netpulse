import sys

from netpulse.worker import archiver, fifo, node

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Missing worker type. \nUsage: worker.py <node|fifo|archiver>")
        sys.exit(1)

    if sys.argv[1] == "node":
        node.main()
    elif sys.argv[1] == "fifo":
        fifo.main()
    elif sys.argv[1] == "archiver":
        archiver.main()
    else:
        print("Invalid worker type")
        sys.exit(1)
