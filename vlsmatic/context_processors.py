from django.conf import settings


def static_asset_version(_request):
    """Append an automatic mtime query string to local static assets in DEBUG mode."""
    if not settings.DEBUG:
        return {"static_version_query": ""}
    static_dir = settings.BASE_DIR / "static"
    latest_mtime = 0
    for folder in ("css", "js"):
        target = static_dir / folder
        if target.is_dir():
            for path in target.iterdir():
                if path.is_file():
                    latest_mtime = max(latest_mtime, int(path.stat().st_mtime))
    return {"static_version_query": f"?v={latest_mtime}" if latest_mtime else ""}
