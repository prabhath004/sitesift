"""Error responses.

A database failure is reported as a 500 with a short, fixed sentence. The
exception itself is never rendered into the response: driver errors carry table
names, SQL fragments, and sometimes connection strings, and none of that belongs
in something a browser can read.
"""

from fastapi import HTTPException, status


def database_error(action: str) -> HTTPException:
    """A 500 that says what failed without saying anything about how."""
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=(
            f"A database error prevented SiteSift from completing this request: could not {action}."
        ),
    )
