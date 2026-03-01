import os
import time

def tail_log(path, lines=200):
    with open(path, "rb") as f:
        f.seek(0, 2)
        end = f.tell()
        size = 1024
        data = b""
        while len(data.splitlines()) <= lines and f.tell() > 0:
            step = min(size, f.tell())
            f.seek(-step, 1)
            data = f.read(step) + data
            f.seek(-step, 1)
        return data.decode(errors="replace").splitlines()[-lines:]

def xstream_log(path):
    """Stream log lines safely for SSE with heartbeat."""
    if not os.path.exists(path):
        yield "data: Log file not found\n\n"
        return

    with open(path, "r") as f:
        f.seek(0, 2)  # go to end of file

        while True:
            # read all new lines available
            lines = f.readlines()
            if lines:
                for line in lines:
                    yield f"data: {line.rstrip()}\n\n"
            else:
                # heartbeat to keep connection alive
                yield ": ping\n\n"
                time.sleep(0.5)

def stream_log(path):
    """Stream log lines for SSE, non-blocking and real-time."""
    if not os.path.exists(path):
        yield "data: Log file not found\n\n"
        return

    with open(path, "r") as f:
        f.seek(0, 2)  # start at end

        last_size = os.stat(path).st_size

        while True:
            current_size = os.stat(path).st_size
            if current_size > last_size:
                # read the new bytes
                new_lines = f.read(current_size - last_size)
                for line in new_lines.splitlines():
                    yield f"data: {line.rstrip()}\n\n"
                last_size = current_size
            else:
                # heartbeat
                yield ": ping\n\n"
                time.sleep(0.5)

