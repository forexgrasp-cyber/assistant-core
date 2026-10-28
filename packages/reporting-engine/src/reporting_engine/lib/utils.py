"""
Utility Functions for Reporting Engine
"""

def format_number(value: float | str, format: str = 'number') -> str:
    """Format number based on type."""
    num = float(value) if isinstance(value, str) else value
    if num != num:  # NaN check
        return '—'
    
    if format == 'currency':
        return f"${num:,.2f}"
    elif format == 'number':
        return f"{num:,.0f}"
    elif format == 'percent':
        return f"{num:.1f}%"
    elif format == 'ratio':
        return f"{num:.1f}x"
    return str(num)


def format_date(date_str: str, options: dict | None = None) -> str:
    """Format date string."""
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%b %d, %Y')
    except (ValueError, AttributeError):
        return date_str


def format_relative_time(date_str: str) -> str:
    """Format relative time (e.g., '2h ago')."""
    from datetime import datetime, timezone
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        diff = now - dt.replace(tzinfo=timezone.utc)
        
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return 'just now'
        elif seconds < 3600:
            return f'{seconds // 60}m ago'
        elif seconds < 86400:
            return f'{seconds // 3600}h ago'
        elif seconds < 604800:
            return f'{seconds // 86400}d ago'
        return dt.strftime('%b %d, %Y')
    except (ValueError, AttributeError):
        return date_str


def truncate(text: str, length: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= length:
        return text
    return text[:length - 3] + '...'


def class_names(*classes: str | bool | None) -> str:
    """Join class names, filtering out falsy values."""
    return ' '.join(filter(None, classes))


def generate_id(prefix: str = 'id') -> str:
    """Generate a unique ID."""
    import random
    import string
    return f"{prefix}_{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"


def debounce(func, wait: int):
    """Debounce function."""
    import threading
    timeout = None
    def debounced(*args, **kwargs):
        nonlocal timeout
        if timeout:
            timeout.cancel()
        timeout = threading.Timer(wait / 1000, lambda: func(*args, **kwargs))
        timeout.start()
    return debounced


def throttle(func, limit: int):
    """Throttle function."""
    import time
    last_call = 0
    def throttled(*args, **kwargs):
        nonlocal last_call
        now = time.time() * 1000
        if now - last_call >= limit:
            last_call = now
            return func(*args, **kwargs)
    return throttled


def parse_query_string(query: str) -> dict:
    """Parse query string into dict."""
    from urllib.parse import parse_qs
    parsed = parse_qs(query.lstrip('?'))
    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}


def build_query_string(params: dict) -> str:
    """Build query string from dict."""
    from urllib.parse import urlencode
    return urlencode({k: v for k, v in params.items() if v is not None and v != ''})


def download_file(content: str, filename: str, mime_type: str):
    """Trigger file download in browser."""
    import base64
    # In browser environment, this would create a download link
    # For server-side, this is a no-op
    pass


def copy_to_clipboard(text: str):
    """Copy text to clipboard."""
    # In browser environment, would use navigator.clipboard.writeText
    pass


def get_initials(name: str) -> str:
    """Get initials from name."""
    return ''.join(part[0] for part in name.split() if part).upper()[:2]


def get_color_for_index(index: int) -> str:
    """Get color from palette for index."""
    colors = [
        '#3b82f6', '#10b981', '#f59e0b', '#ef4444',
        '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16',
        '#f97316', '#6366f1', '#14b8a6', '#eab308',
    ]
    return colors[index % len(colors)]


async def sleep(ms: int):
    """Async sleep."""
    import asyncio
    await asyncio.sleep(ms / 1000)


async def retry(fn, retries: int = 3, delay: int = 1000):
    """Retry async function with exponential backoff."""
    import asyncio
    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as e:
            if attempt == retries:
                raise
            await sleep(delay * (2 ** attempt))