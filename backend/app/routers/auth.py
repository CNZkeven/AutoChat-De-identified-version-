from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import TokenResponse, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password
from ..services.user_profiles import refresh_system_profile

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    if payload.email:
        email_exists = db.query(User).filter(User.email == payload.email).first()
        if email_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            major=user.major,
            grade=user.grade,
            gender=user.gender,
        ),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(str(user.id))
    background_tasks.add_task(refresh_system_profile, user.id)
    return TokenResponse(
        access_token=token,
        user=UserOut(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            major=user.major,
            grade=user.grade,
            gender=user.gender,
        ),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        major=current_user.major,
        grade=current_user.grade,
        gender=current_user.gender,
    )
