"""Utilities to handle DB session compatibility.

Some tests or legacy code may pass an async generator (the FastAPI dependency
`get_db()` when called directly) instead of an actual ``AsyncSession`` instance.
These helpers unwrap the async generator to obtain the real session so
compatibility shims can operate correctly in both test and runtime contexts.
"""
import inspect
from typing import Any, Optional


async def resolve_session(session_or_gen: Any) -> Optional[Any]:
    """If ``session_or_gen`` is an async generator, advance it once and
    return the yielded value (the real session). Otherwise return it as-is.

    Note: the generator is left open; callers that need to close it may do so.
    """
    if inspect.isasyncgen(session_or_gen):
        try:
            return await session_or_gen.__anext__()
        except StopAsyncIteration:
            return None
    return session_or_gen
