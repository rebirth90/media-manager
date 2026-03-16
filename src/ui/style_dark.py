# Dark Theme Design Tokens
COLORS = {
    # Backgrounds
    "bg_app": "#0A0B0E",           # Main application background
    "bg_sidebar": "#0F1115",       # Hardware sidebar/header background
    "bg_card_start": "#13151A",    # Card gradient start
    "bg_card_end": "#1A1C23",      # Card gradient end
    "bg_card_hover": "#1A1C23",

    # Accents
    "primary": "#3b82f6",          # Primary blue action
    "primary_hover": "#2563eb",
    "primary_bg": "rgba(59, 130, 246, 0.1)",  # Blue tinted background

    # Borders
    "border_subtle": "rgba(255, 255, 255, 0.05)",
    "border_hover": "rgba(255, 255, 255, 0.10)",

    # Texts
    "text_primary": "#ffffff",
    "text_secondary": "#9ca3af",   # Gray-400
    "text_muted": "#6b7280",       # Gray-500
    "text_dark": "#4b5563",        # Gray-600

    # Status Pills
    "status_completed_bg": "rgba(34, 197, 94, 0.1)",
    "status_completed_text": "#4ade80",
    "status_downloading_bg": "rgba(59, 130, 246, 0.1)",
    "status_downloading_text": "#60a5fa",
    "status_seeding_bg": "rgba(168, 85, 247, 0.1)",
    "status_seeding_text": "#c084fc",
    "status_error_bg": "rgba(239, 68, 68, 0.1)",
    "status_error_text": "#f87171",
    "status_default_bg": "rgba(107, 114, 128, 0.1)",
    "status_default_text": "#9ca3af",
}

def get_status_style(status_type: str) -> str:
    """Returns QSS for status pills based on status type ('completed', 'downloading', 'seeding', 'in_progress', 'default')."""
    type_map = {
        "completed": ("status_completed_bg", "status_completed_text", "rgba(34,197,94,0.3)"),
        "downloading": ("status_downloading_bg", "status_downloading_text", "rgba(59,130,246,0.3)"),
        "in progress": ("status_downloading_bg", "status_downloading_text", "rgba(59,130,246,0.3)"),
        "seeding": ("status_seeding_bg", "status_seeding_text", "rgba(168,85,247,0.3)"),
        "error": ("status_error_bg", "status_error_text", "rgba(239,68,68,0.3)"),
    }
    
    key = status_type.lower()
    bg_key, text_key, border_color = type_map.get(key, ("status_default_bg", "status_default_text", "rgba(107,114,128,0.3)"))

    return f"""
        QLabel {{
            background-color: {COLORS[bg_key]};
            color: {COLORS[text_key]};
            border: 1px solid {border_color};
            border-radius: 6px;
            padding: 4px 10px;
            font-weight: 600;
            font-size: 11px;
        }}
    """
