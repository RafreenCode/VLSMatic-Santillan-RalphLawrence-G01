"""Recognize expected uniqueness conflicts without hiding other database errors."""


def is_unique_conflict(error):
    cause = error.__cause__
    return (
        getattr(cause, "sqlstate", None) == "23505"
        or getattr(cause, "sqlite_errorcode", None) in {1555, 2067}
    )
