"""
Legacy compatibility shim. The API router implementation has moved to
`app.api.apis.router`. Importing this module re-exports the router so older
imports keep working during the transition.
"""

from .apis.router import router  # re-export

