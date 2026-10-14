from collections.abc import AsyncGenerator

import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
)

from app.db.session import (
    get_db,
)
from app.main import (
    app,
)


class FakeDB:

    def __init__(self):

        self.added = []
        self.commits = 0
        self.refreshed = []

    def add(
        self,
        item,
    ):

        self.added.append(
            item
        )

    async def commit(
        self,
    ):

        self.commits += 1

    async def refresh(
        self,
        item,
    ):

        self.refreshed.append(
            item
        )


@pytest.fixture
def fake_db():

    return FakeDB()


@pytest.fixture
def app_instance():

    return app


@pytest.fixture
async def api_client(
    app_instance,
    fake_db,
):

    async def override_get_db(
    ) -> AsyncGenerator[
        FakeDB,
        None,
    ]:

        yield fake_db

    app_instance.dependency_overrides[
        get_db
    ] = override_get_db

    transport = ASGITransport(
        app=app_instance,
    )

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:

        yield client

    app_instance.dependency_overrides.clear()