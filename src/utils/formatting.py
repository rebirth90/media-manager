import math

def format_size(size_bytes: int) -> str:
    """Safely format byte integer to human readable sizes."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_speed(speed_bytes: int) -> str:
    """Format speed to human readable kb/s."""
    if speed_bytes == 0:
        return "0 kB/s"
    return f"{round(speed_bytes / 1024, 1)} kB/s"
