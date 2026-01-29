from types import SimpleNamespace
from typing import Dict, Optional, List, Any


class InMemoryDB:
    """Simple in-memory DB for quick local development / fallback.

    Provides async methods used by the APIs CRUD layer. Objects returned are
    SimpleNamespace instances so Pydantic's `from_attributes` can read them.
    """

    def __init__(self) -> None:
        self.in_memory = True
        self._apis: Dict[int, SimpleNamespace] = {}
        self._next_api_id = 1

    async def create_api(self, payload: Dict[str, Any]) -> SimpleNamespace:
        # check for existing API with same name+version
        for a in self._apis.values():
            if a.name == payload.get("name") and a.version == payload.get("version"):
                raise ValueError("API with same name and version already exists")

        api = SimpleNamespace()
        api.id = self._next_api_id
        api.name = payload.get("name")
        api.version = payload.get("version")
        api.description = payload.get("description")
        api.owner_id = payload.get("owner_id")
        api.config = payload.get("config")

        self._apis[self._next_api_id] = api
        self._next_api_id += 1
        return api

    async def list_apis(self) -> List[SimpleNamespace]:
        return list(self._apis.values())

    async def get_api(self, api_id: int) -> Optional[SimpleNamespace]:
        return self._apis.get(api_id)

    async def update_api(self, api: SimpleNamespace, patch: Dict[str, Any]) -> SimpleNamespace:
        for k, v in patch.items():
            if v is not None and hasattr(api, k):
                setattr(api, k, v)
        # store is by id so no re-insertion required
        self._apis[api.id] = api
        return api

    async def delete_api(self, api: SimpleNamespace) -> None:
        if api.id in self._apis:
            del self._apis[api.id]
