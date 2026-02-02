from app.db import models
from app.api.apis import schemas


def test_api_pydantic_roundtrip():
    # create a fake SQLAlchemy model instance (not persisted) and validate via Pydantic
    api = models.API(
        id=1,
        name="test-api",
        version="v1",
        description="A test API",
        owner_id=None,
        config={"paths": {"/hello": {"get": {}}}},
    )

    # Pydantic from ORM
    p = schemas.APIMeta.from_orm(api)
    assert p.name == "test-api"
    assert p.version == "v1"
    assert p.config and p.config.get("paths")

    # convert back to dict and ensure keys
    d = p.dict()
    assert d["name"] == "test-api"
    assert d["config"]["paths"]["/hello"]["get"] == {}
