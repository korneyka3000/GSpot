import datetime
from datetime import timedelta

from fastapi import APIRouter, Body, Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from .schemas import Token, TokenData, User, UserInDB
from .service import Auth

auth_instance = Auth()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
    "/login",
    response_model=Token,
)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth_instance.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_exp = timedelta(minutes=auth_instance.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_instance.create_access_token(
        data={
            "sub": user.username,
        },
        expires_delta=access_token_exp,
    )
    refresh_token = auth_instance.create_refresh_token(
        data={
            "sub": user.username,
        },
        expires_delta=access_token_exp,
    )

    response = JSONResponse(
        content={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }
    )
    expiration = datetime.datetime.utcnow() + timedelta(hours=1)
    response.set_cookie(
        key="access_token",
        value=access_token,
        # httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        # httponly=True,
        secure=True,
        samesite="strict",
        max_age=1800,
    )
    return response
