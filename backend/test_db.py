import asyncio

import asyncpg


async def main() -> None:
    connection = await asyncpg.connect(
        host="127.0.0.1",
        port=5433,
        user="proofpatch",
        password="proofpatch",
        database="proofpatch",
    )

    result = await connection.fetchval(
        "SELECT current_user"
    )

    print("Connected as:", result)

    await connection.close()


asyncio.run(main())