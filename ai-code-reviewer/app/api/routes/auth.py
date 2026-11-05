from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    ForgotPasswordRequest,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    UserCreate,
    UserResponse,
    VerifyEmailRequest,
)
from app.services import email_service, email_verification_service, password_reset_service
from app.schemas.token import Token
from app.core.security import verify_password, get_password_hash, create_access_token

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Без налаштованої пошти підтвердити email неможливо, тож акаунт активний одразу (режим розробки)
    verified = not email_service.smtp_configured()
    hashed = get_password_hash(user_data.password)

    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if user:
        if user.email_verified:
            raise HTTPException(status_code=400, detail="Email вже зареєстрований")
        # Непідтверджений акаунт недоступний і не має даних, тож реєстрацію можна пройти заново:
        # чужа адреса не залишається «зайнятою», а підтвердити її зможе лише власник скриньки
        user.hashed_password = hashed
        user.email_verified = verified
    else:
        user = User(email=user_data.email, hashed_password=hashed, email_verified=verified)
        db.add(user)
    await db.commit()
    await db.refresh(user)

    if not user.email_verified:
        link = await email_verification_service.create_verification_link(db, user)
        if link:
            background_tasks.add_task(email_service.send_verification_email, user.email, link)
    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email не підтверджено. Перейдіть за посиланням з листа або надішліть його ще раз.",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Надіслати на email посилання для скидання пароля.

    Відповідь завжди однакова, незалежно від того, чи існує такий акаунт, щоб не розкривати зареєстровані адреси.
    Лист надсилається у фоні, тож і час відповіді не видає наявність акаунта.
    """
    created = await password_reset_service.create_reset_link(db, data.email)
    if created:
        email, link = created
        background_tasks.add_task(email_service.send_password_reset_email, email, link)
    return {"message": "Якщо акаунт з такою адресою існує, ми надіслали на неї лист з посиланням для скидання пароля."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Задати новий пароль за одноразовим посиланням з листа."""
    await password_reset_service.reset_password(db, data.token, data.password)
    return {"message": "Пароль змінено. Тепер можна увійти з новим паролем."}


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    """Підтвердити email за одноразовим посиланням з листа."""
    await email_verification_service.verify_email(db, data.token)
    return {"message": "Email підтверджено. Тепер можна увійти."}


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    data: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Надіслати лист підтвердження ще раз. Відповідь однакова незалежно від того, чи існує акаунт."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if user and user.is_active and not user.email_verified:
        link = await email_verification_service.create_verification_link(db, user)
        if link:
            background_tasks.add_task(email_service.send_verification_email, user.email, link)
    return {"message": "Якщо акаунт існує і ще не підтверджений, ми надіслали лист з посиланням."}
