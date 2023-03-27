import redis.commands.timeseries
from fastapi import WebSocket

r = redis.Redis(encoding="utf-8", decode_responses=True, host="redis_channels")


class WsManager:
    """WebSocket handler"""

    group_prefix = "group:"

    def __init__(self, websocket: WebSocket) -> None:
        self.connect_id = websocket.scope.get("client")[1]
        # TODO: need to populate redis here

    async def on_connect(self, websocket: WebSocket, user) -> None:
        await self.check_connections(user["_id"])
        # r.json().set(f"active:{self.connect_id}", ".", websocket)
        await websocket.accept()

    async def on_disconnect(self, websocket: WebSocket, close: int):
        # r.json().delete(f'active:{self.connect_id}')
        pass

    async def group_send(self, websocket: WebSocket, message: dict):
        # active_connections = r.scan(match='active:*')[1]
        # for connection in active_connections:
        #     await connection.send_json(message)
        pass

    async def check_connections(self, user_id):
        if r.exists(f"user:{user_id}"):
            pass
