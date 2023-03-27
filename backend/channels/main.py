from typing import Annotated

import motor.motor_asyncio
from fastapi import (Depends, FastAPI, HTTPException, Query, Request,
                     WebSocket, WebSocketDisconnect, status)
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext

from auth.router import auth_router
from auth.schemas import (BaseUser, BaseUserInDB, Token, TokenData, User,
                          UserInDB)
from auth.service import Auth
from ws.service import WsManager

SECRET_KEY = "b2c4eb822b886919e8b4842c0fac3cf6ca98aa2c8db8d085a3ff61286360788d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="WS CHAT")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

app.include_router(auth_router)


origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

auth_instance = Auth()

fake_users_db = {
    "johndoe": {
        "username": "johndoe",
        "full_name": "John Doe",
        "email": "johndoe@example.com",
        "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
        "disabled": False,
    },
    "alice": {
        "username": "alice",
        "full_name": "Alice Wonderson",
        "email": "alice@example.com",
        "hashed_password": "fakehashedsecret2",
        "disabled": True,
    },
}

# mongo_db
client = motor.motor_asyncio.AsyncIOMotorClient("mongodb_channels")
db = client.chat


@app.on_event("startup")
async def populate_db_with_users():
    if "users" not in await db.list_collection_names():
        data = [
            {
                "username": "johndoe",
                "full_name": "John Doe",
                "email": "johndoe@example.com",
                "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",
                "disabled": False,
            },
            {
                "username": "admin",
                "full_name": "Admin Admin",
                "email": "admin@admin.com",
                "hashed_password": "$2b$12$q.7PXJAgneWCl8eKoUWilOGnoA14WWOn8wfT1aK..CQPKLj5hHvBK",
                "disabled": False,
            },
            {
                "username": "superuser",
                "full_name": "Super User",
                "email": "super@user.com",
                "hashed_password": "$2b$12$IS3d/9clJTdwZ2lzlLfMIezUc07pp2QXR9Sxm0Vv4J75gmxJD3v4a",
                "disabled": False,
            },
            {
                "username": "yourfriend",
                "full_name": "Your Friend",
                "email": "your@friend.com",
                "hashed_password": "$2b$12$.N2uTAxGg60eJSu29aOAleFAwlPU3yhoWCrlH21uNKep2JsL94Rgy",
                "disabled": False,
            },
        ]
        data = [BaseUserInDB(**instance) for instance in data]
        encoded_data = jsonable_encoder(data)
        await db.users.insert_many(encoded_data)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, Auth.SECRET_KEY, algorithms=[Auth.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = await Auth.get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@app.get("/login/", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/chat/", response_class=HTMLResponse)
async def get_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.get("/users/me")
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


async def all_users(exclude_user_id: str | None = None) -> list[BaseUserInDB]:
    users = await db.users.find({"_id": {"$ne": f"{exclude_user_id}"}}).to_list(
        length=1000
    )
    print(users, "users")
    return users


@app.websocket("/ws/chat")
async def lighter_endpoint(
    websocket: WebSocket, access_token: str = Query(default=None)
):
    ws = WsManager(websocket)
    user = await auth_instance.get_current_user(access_token)
    print(websocket)
    # await ws.on_connect(websocket, user)
    users = await all_users(user["_id"])
    await websocket.accept()
    await websocket.send_json({"user": user})
    await websocket.send_json({"users": users})
    try:
        while True:
            data = await websocket.receive_json()
            print(data)
            await websocket.send_json(data)

            # await ws.group_send(websocket, data)
    except WebSocketDisconnect:
        # await ws.on_disconnect(websocket, 1000)
        # await ws.group_send(websocket, {"message": f"client {websocket} left the chat"})
        print(websocket)


@app.get(
    "/all_users/",
    response_model=list[BaseUserInDB],
    response_description="All users from db",
)
async def get_users():
    users = await all_users()
    return users
