import math

def format_size(size_in_bytes: int) -> str:
    """Converts raw bytes to human-readable size exactly like qBittorrent."""
    try:
        size = float(size_in_bytes)
    except (ValueError, TypeError):
        return "0 B"

    if size <= 0:
        return "0 B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = 0
    while size >= 1024 and i < len(size_name) - 1:
        size /= 1024.0
        i += 1

    if i == 0:
        return f"{int(size)} {size_name[i]}"
    return f"{size:.1f} {size_name[i]}"

def format_speed(speed_in_bytes_per_sec: int) -> str:
    """Converts raw bytes/sec to human-readable speed exactly like qBittorrent."""
    try:
        speed = float(speed_in_bytes_per_sec)
    except (ValueError, TypeError):
        return "0 B/s"

    if speed <= 0:
        return "0 B/s"

    speed_name = ("B/s", "KB/s", "MB/s", "GB/s", "TB/s")
    i = 0
    while speed >= 1024 and i < len(speed_name) - 1:
        speed /= 1024.0
        i += 1

    if i == 0:
        return f"{int(speed)} {speed_name[i]}"
    return f"{speed:.1f} {speed_name[i]}"

def format_time(seconds: int) -> str:
    """Formats seconds into HH:MM:SS."""
    if not seconds or seconds < 0:
        return "00:00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"