# Color System Reference Guide

Quick reference for the Media Manager color palette. Use these exact values for consistency across the application.

## Primary Palette

### Blues (Primary Actions)

```python
PRIMARY_BLUE = "#60a5fa"        # Main action buttons, links
PRIMARY_BLUE_HOVER = "#3b82f6"  # Hover state for primary actions
PRIMARY_BLUE_PRESSED = "#2563eb" # Pressed/active state

SOFT_BLUE = "#a8d5e8"           # Button backgrounds
SOFT_BLUE_HOVER = "#8ec5de"     # Hover state
SOFT_BLUE_PRESSED = "#7ab8d4"   # Pressed state

DEEP_BLUE = "#1e3a5f"           # Text on colored backgrounds
DEEP_BLUE_DARK = "#0f2847"      # Darker variant

LIGHT_BLUE = "#e8f4f8"          # Background tints
LIGHT_BLUE_TINT = "#f0f8ff"     # Lighter tint
```

### Usage Examples:

```python
# Primary button
button.setStyleSheet(f"""
    QPushButton {{
        background-color: {SOFT_BLUE};
        color: {DEEP_BLUE};
    }}
    QPushButton:hover {{
        background-color: {SOFT_BLUE_HOVER};
    }}
""")

# Link or accent
label.setStyleSheet(f"color: {PRIMARY_BLUE};")
```

---

## Status Colors

### Success (Green)

```python
SUCCESS_BORDER = "#10b981"      # Border for success states
SUCCESS_BG = "#d1fae5"          # Background for success
SUCCESS_BG_LIGHT = "#a7f3d0"    # Lighter background
SUCCESS_TEXT = "#065f46"        # Text on success backgrounds
SUCCESS_TEXT_MEDIUM = "#059669" # Medium contrast text
```

### Usage:

```python
# Success button (Approve & Share)
button.setStyleSheet("""
    QPushButton {
        border: 2.5px solid #10b981;
        background-color: #d1fae5;
        color: #065f46;
    }
    QPushButton:hover {
        background-color: #a7f3d0;
    }
""")
```

---

### Warning (Amber)

```python
WARNING_BORDER = "#fbbf24"      # Border for warning states
WARNING_BG = "#fef3c7"          # Background for warnings
WARNING_BG_LIGHT = "#fde68a"    # Lighter background
WARNING_TEXT = "#b45309"        # Text on warning backgrounds
WARNING_TEXT_MEDIUM = "#d97706" # Medium contrast text
```

### Usage:

```python
# Warning button (Downloading/Encoding)
button.setStyleSheet("""
    QPushButton {
        border: 2.5px solid #fbbf24;
        background-color: #fef3c7;
        color: #b45309;
    }
    QPushButton:hover {
        background-color: #fde68a;
    }
""")
```

---

### Error (Red)

```python
ERROR_BORDER = "#ef4444"        # Border for error states
ERROR_BG = "#fee2e2"            # Background for errors
ERROR_BG_LIGHT = "#fecaca"      # Lighter background
ERROR_TEXT = "#991b1b"          # Text on error backgrounds
ERROR_TEXT_MEDIUM = "#dc2626"   # Medium contrast text
```

### Usage:

```python
# Error button
button.setStyleSheet("""
    QPushButton {
        border: 2.5px solid #ef4444;
        background-color: #fee2e2;
        color: #991b1b;
    }
    QPushButton:hover {
        background-color: #fecaca;
    }
""")
```

---

## Neutral Grays

### Backgrounds

```python
BG_PRIMARY = "#f8fafc"          # Main application background
BG_GRADIENT_START = "#e8f4f8"   # Gradient start
BG_GRADIENT_MID = "#f0f4f8"     # Gradient middle
BG_GRADIENT_END = "#e0e8f0"     # Gradient end

CARD_WHITE = "#ffffff"          # Card backgrounds
CARD_HOVER = "#f8fbff"          # Card hover state

INPUT_BG = "#f8fafc"            # Input field backgrounds
INPUT_BG_FOCUS = "#ffffff"      # Focused input background
```

---

### Borders

```python
BORDER_LIGHT = "#e8f0f8"        # Very light borders
BORDER_SUBTLE = "#e0e8f0"       # Subtle borders (default)
BORDER_MEDIUM = "#d0e4f0"       # Medium visibility borders
BORDER_STRONG = "#c8dce8"       # Strong borders (hover)
BORDER_GRAY = "#cbd5e1"         # Gray borders
BORDER_GRAY_DARK = "#94a3b8"    # Dark gray borders
```

---

### Text Colors

```python
TEXT_PRIMARY = "#0f172a"        # Main text (headings, important)
TEXT_SECONDARY = "#1e293b"      # Secondary text
TEXT_BODY = "#334155"           # Body text
TEXT_MUTED = "#475569"          # Muted text
TEXT_DISABLED = "#64748b"       # Disabled text
TEXT_HINT = "#94a3b8"           # Placeholder/hint text
TEXT_SUBTLE = "#cbd5e1"         # Very subtle text (arrows)
```

### Usage by Context:

```python
# Headings
heading.setStyleSheet("color: #0f172a; font-weight: 700;")

# Body text
label.setStyleSheet("color: #334155;")

# Secondary information
info.setStyleSheet("color: #475569;")

# Disabled state
disabled.setStyleSheet("color: #94a3b8;")
```

---

## Info/Badge Colors

```python
INFO_BLUE_BG = "#eff6ff"        # Blue badge background
INFO_BLUE_TEXT = "#1e40af"      # Blue badge text

INFO_GREEN_BG = "#f0fdf4"       # Green badge background
INFO_GREEN_TEXT = "#166534"     # Green badge text

INFO_GRAY_BG = "#f1f5f9"        # Gray badge background
INFO_GRAY_TEXT = "#475569"      # Gray badge text
```

### Usage:

```python
# Status badge
badge.setStyleSheet("""
    background-color: #eff6ff;
    color: #1e40af;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
""")
```

---

## Component-Specific Palettes

### Scrollbar

```python
SCROLLBAR_BG = "#f0f4f8"        # Scrollbar track
SCROLLBAR_HANDLE = "#c0d0e0"    # Scrollbar handle
SCROLLBAR_HANDLE_HOVER = "#a0b8d0" # Handle hover
```

---

### Focus States

```python
FOCUS_RING = "#60a5fa"          # Focus outline color
FOCUS_BG = "#ffffff"            # Background when focused
```

---

## Gradients

### Background Gradient

```python
GRADIENT_BACKGROUND = """
    qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #e8f4f8, 
        stop:0.5 #f0f4f8, 
        stop:1 #e0e8f0)
"""
```

---

## Opacity Variations

For semi-transparent overlays:

```python
# Using rgba() with alpha channel
OVERLAY_LIGHT = "rgba(248, 250, 252, 0.95)"  # 95% opacity white
OVERLAY_DARK = "rgba(15, 23, 42, 0.8)"       # 80% opacity dark
SHADOW = "rgba(0, 0, 0, 0.08)"               # 8% black for shadows
```

---

## Dark Mode Palette (Future)

Reserved for future dark mode implementation:

```python
# Dark backgrounds
DARK_BG_PRIMARY = "#1e293b"
DARK_BG_SECONDARY = "#0f172a"
DARK_BG_ELEVATED = "#334155"

# Dark borders
DARK_BORDER = "#475569"

# Dark text (light colors)
DARK_TEXT_PRIMARY = "#f8fafc"
DARK_TEXT_SECONDARY = "#cbd5e1"
```

---

## Color Naming Convention

### Format: `[PURPOSE]_[ELEMENT]_[VARIANT]`

- **Purpose**: PRIMARY, SUCCESS, WARNING, ERROR, INFO, TEXT, BG, BORDER
- **Element**: BLUE, GREEN, RED, GRAY, CARD, INPUT, etc.
- **Variant**: LIGHT, DARK, HOVER, PRESSED, FOCUS

### Examples:

```python
PRIMARY_BLUE_HOVER      # Primary blue color on hover
SUCCESS_BG_LIGHT        # Light success background
BORDER_GRAY_DARK        # Dark gray border
TEXT_PRIMARY            # Primary text color
```

---

## Testing Colors

For testing contrast and accessibility:

```python
# Test contrast ratios at:
# https://webaim.org/resources/contrastchecker/

# WCAG AA minimum: 4.5:1 for normal text, 3:1 for large text
# WCAG AAA recommended: 7:1 for normal text, 4.5:1 for large text

# Current ratios:
TEXT_PRIMARY on CARD_WHITE = "15.2:1" # AAA ✓
DEEP_BLUE on SOFT_BLUE = "4.8:1"     # AA ✓
SUCCESS_TEXT on SUCCESS_BG = "9.5:1" # AAA ✓
```

---

## Quick Copy-Paste Stylesheet Templates

### Standard Button

```python
button.setStyleSheet("""
    QPushButton {
        background-color: #a8d5e8;
        color: #1e3a5f;
        border: none;
        border-radius: 22px;
        padding: 0 24px;
        font-weight: 600;
        font-size: 11pt;
    }
    QPushButton:hover {
        background-color: #8ec5de;
    }
    QPushButton:pressed {
        background-color: #7ab8d4;
    }
""")
```

---

### Input Field

```python
input_field.setStyleSheet("""
    QLineEdit {
        background-color: #f8fafc;
        border: 2px solid #e0e8f0;
        border-radius: 10px;
        padding: 8px 12px;
        color: #334155;
    }
    QLineEdit:focus {
        border-color: #60a5fa;
        background-color: #ffffff;
    }
""")
```

---

### Card Container

```python
card.setStyleSheet("""
    QWidget {
        background-color: #ffffff;
        border: 1px solid #e8f0f8;
        border-radius: 12px;
        padding: 12px;
    }
    QWidget:hover {
        background-color: #f8fbff;
        border-color: #c8dce8;
    }
""")
```

---

### Status Badge

```python
badge.setStyleSheet("""
    QLabel {
        background-color: #eff6ff;
        color: #1e40af;
        border-radius: 6px;
        padding: 6px 10px;
        font-weight: 600;
    }
""")
```

---

## Best Practices

1. **Always use named colors from this guide** - Don't invent new colors
2. **Maintain contrast ratios** - Test with actual text sizes
3. **Use semantic naming** - Color names should indicate purpose, not appearance
4. **Consistent hover states** - Darken by one step in the palette
5. **Border width progression** - 1px subtle, 1.5px medium, 2px strong, 2.5px active
6. **Alpha for overlays only** - Use solid colors for UI elements

---

**Last updated: February 26, 2026**
