import math

def format_size(size_in_bytes: int) -> str:
    """Converts raw bytes to human-readable size."""
    if size_in_bytes <= 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_in_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_in_bytes / p, 2)
    return f"{s} {size_name[i]}"

def format_speed(speed_in_bytes_per_sec: int) -> str:
    """Converts raw bytes/sec to human-readable speed."""
    if not speed_in_bytes_per_sec or speed_in_bytes_per_sec <= 0:
        return "0.0 MB/s"
    
    speed_name = ("B/s", "KB/s", "MB/s", "GB/s")
    i = int(math.floor(math.log(speed_in_bytes_per_sec, 1024)))
    p = math.pow(1024, i)
    s = round(speed_in_bytes_per_sec / p, 1)
    
    if i < 2 and speed_in_bytes_per_sec > 0:
         return f"{round(speed_in_bytes_per_sec / (1024*1024), 2)} MB/s"
         
    return f"{s} {speed_name[i]}"

def format_time(seconds: int) -> str:
    """Formats seconds into HH:MM:SS."""
    if not seconds or seconds < 0:
        return "00:00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"