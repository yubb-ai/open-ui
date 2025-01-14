import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel

from open_webui.apps.filter.main import new_number_sign_up_notice
from open_webui.apps.webui.models.auths import (
    AddUserForm,
    ApiKey,
    Auths,
    SigninForm,
    SigninResponse,
    SignupForm,
    UpdatePasswordForm,
    UpdateProfileForm,
    UserResponse,
)
from open_webui.apps.webui.models.users import Users
from open_webui.config import (
    WEBUI_AUTH,
    ENABLE_WECHAT_NOTICE,
)
from open_webui.constants import ERROR_MESSAGES, WEBHOOK_MESSAGES
from open_webui.env import (
    WEBUI_AUTH_TRUSTED_EMAIL_HEADER,
    WEBUI_AUTH_TRUSTED_NAME_HEADER,
)
from open_webui.utils.misc import parse_duration, validate_email_format
from open_webui.utils.utils import (
    create_api_key,
    create_token,
    get_admin_user,
    get_current_user,
    get_password_hash,
    validate_token,
)
from open_webui.utils.webhook import post_webhook

router = APIRouter()


############################
# GetSessionUser
############################


@router.get("/", response_model=UserResponse)
async def get_session_user(
    request: Request, response: Response, user=Depends(get_current_user)
):
    token = create_token(
        data={"id": user.id},
        expires_delta=parse_duration(request.app.state.config.JWT_EXPIRES_IN),
    )

    # Set the cookie token
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,  # Ensures the cookie is not accessible via JavaScript
    )

    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "profile_image_url": user.profile_image_url,
        "expire_at": user.expire_at,
    }


############################
# Update Profile
############################


@router.post("/update/profile", response_model=UserResponse)
async def update_profile(
    form_data: UpdateProfileForm, session_user=Depends(get_current_user)
):
    if session_user:
        user = Users.update_user_by_id(
            session_user.id,
            {"profile_image_url": form_data.profile_image_url, "name": form_data.name},
        )
        if user:
            return user
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.DEFAULT())
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# Update Password
############################


@router.post("/update/password", response_model=bool)
async def update_password(
    form_data: UpdatePasswordForm, session_user=Depends(get_current_user)
):
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)
    if session_user:
        user = Auths.authenticate_user(session_user.email, form_data.password)

        if user:
            hashed = get_password_hash(form_data.new_password)
            return Auths.update_user_password_by_id(user.id, hashed)
        else:
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_PASSWORD)
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignIn
############################


@router.post("/signin", response_model=SigninResponse)
async def signin(request: Request, response: Response, form_data: SigninForm):
    if WEBUI_AUTH_TRUSTED_EMAIL_HEADER:
        if WEBUI_AUTH_TRUSTED_EMAIL_HEADER not in request.headers:
            raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_TRUSTED_HEADER)

        trusted_email = request.headers[WEBUI_AUTH_TRUSTED_EMAIL_HEADER].lower()
        trusted_name = trusted_email
        if WEBUI_AUTH_TRUSTED_NAME_HEADER:
            trusted_name = request.headers.get(
                WEBUI_AUTH_TRUSTED_NAME_HEADER, trusted_email
            )
        if not Users.get_user_by_email(trusted_email.lower()):
            await signup(
                request,
                response,
                SignupForm(
                    email=trusted_email, password=str(uuid.uuid4()), name=trusted_name
                ),
            )
        user = Auths.authenticate_user_by_trusted_header(trusted_email)
    elif WEBUI_AUTH == False:
        admin_email = "admin@localhost"
        admin_password = "admin"

        if Users.get_user_by_email(admin_email.lower()):
            user = Auths.authenticate_user(admin_email.lower(), admin_password)
        else:
            if Users.get_num_users() != 0:
                raise HTTPException(400, detail=ERROR_MESSAGES.EXISTING_USERS)

            await signup(
                request,
                response,
                SignupForm(email=admin_email, password=admin_password, name="User"),
            )

            user = Auths.authenticate_user(admin_email.lower(), admin_password)
    else:
        if (
            request.app.state.config.TURNSTILE_LOGIN_CHECK
            and request.app.state.config.TURNSTILE_SECRET_KEY
        ):
            res = await validate_token(
                form_data.turnstileToken, request.app.state.config.TURNSTILE_SECRET_KEY
            )
            if not res.get("success", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.TURNSTILE_ERROR,
                )
        user = Auths.authenticate_user(form_data.email.lower(), form_data.password)

    if user:
        token = create_token(
            data={"id": user.id},
            expires_delta=parse_duration(request.app.state.config.JWT_EXPIRES_IN),
        )

        # Set the cookie token
        response.set_cookie(
            key="token",
            value=token,
            httponly=True,  # Ensures the cookie is not accessible via JavaScript
        )

        return {
            "token": token,
            "token_type": "Bearer",
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "profile_image_url": user.profile_image_url,
            "expire_at": user.expire_at,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.INVALID_CRED)


############################
# SignUp
############################


@router.post("/signup", response_model=SigninResponse)
async def signup(request: Request, response: Response, form_data: SignupForm):
    if WEBUI_AUTH:
        if (
            not request.app.state.config.ENABLE_SIGNUP
            or not request.app.state.config.ENABLE_LOGIN_FORM
        ):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )
    else:
        if Users.get_num_users() != 0:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED
            )

    if (
        request.app.state.config.TURNSTILE_SIGNUP_CHECK
        and request.app.state.config.TURNSTILE_SECRET_KEY
    ):
        res = await validate_token(
            form_data.turnstileToken, request.app.state.config.TURNSTILE_SECRET_KEY
        )
        if not res.get("success", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.TURNSTILE_ERROR,
            )

    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    registered_email_suffix = request.app.state.config.REGISTERED_EMAIL_SUFFIX
    valid_email_formats = (
        [suffix for suffix in registered_email_suffix.split(",") if suffix]
        if registered_email_suffix
        else []
    )

    if valid_email_formats and not any(
        form_data.email.lower().endswith(suffix) for suffix in valid_email_formats
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT,
        )

    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        role = (
            "admin"
            if Users.get_num_users() == 0
            else request.app.state.config.DEFAULT_USER_ROLE
        )

        if role in ["pending", "admin"]:
            expire_duration = 10
            expire_unit = "year"
        else:
            expire_duration = request.app.state.config.DEFAULT_USER_EXPIRE_DURATION
            expire_unit = request.app.state.config.DEFAULT_USER_EXPIRE_UNIT

        hashed = get_password_hash(form_data.password)
        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url,
            role,
            expire_at=None,
            expire_duration=expire_duration,
            expire_unit=expire_unit,
        )

        if user:
            token = create_token(
                data={"id": user.id},
                expires_delta=parse_duration(request.app.state.config.JWT_EXPIRES_IN),
            )

            # Set the cookie token
            response.set_cookie(
                key="token",
                value=token,
                httponly=True,  # Ensures the cookie is not accessible via JavaScript
            )

            if ENABLE_WECHAT_NOTICE:
                try:
                    await new_number_sign_up_notice(user.name, user.role, user.email)
                except Exception as e:
                    print(f"new_number_sign_up函数出现问题：{e}")

            if request.app.state.config.WEBHOOK_URL:
                post_webhook(
                    request.app.state.config.WEBHOOK_URL,
                    WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                    {
                        "action": "signup",
                        "message": WEBHOOK_MESSAGES.USER_SIGNUP(user.name),
                        "user": user.model_dump_json(exclude_none=True),
                    },
                )

            return {
                "token": token,
                "token_type": "Bearer",
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "expire_at": user.expire_at,
                "profile_image_url": user.profile_image_url,
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        raise HTTPException(500, detail=ERROR_MESSAGES.DEFAULT(err))


############################
# AddUser
############################


@router.post("/add", response_model=SigninResponse)
async def add_user(form_data: AddUserForm, user=Depends(get_admin_user)):
    if not validate_email_format(form_data.email.lower()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.INVALID_EMAIL_FORMAT
        )

    if Users.get_user_by_email(form_data.email.lower()):
        raise HTTPException(400, detail=ERROR_MESSAGES.EMAIL_TAKEN)

    try:
        print(form_data)
        hashed = get_password_hash(form_data.password)
        user = Auths.insert_new_auth(
            form_data.email.lower(),
            hashed,
            form_data.name,
            form_data.profile_image_url,
            form_data.role,
            form_data.expire_at,
        )

        if user:
            token = create_token(data={"id": user.id})
            return {
                "token": token,
                "token_type": "Bearer",
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "expire_at": user.expire_at,
                "profile_image_url": user.profile_image_url,
            }
        else:
            raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_USER_ERROR)
    except Exception as err:
        raise HTTPException(500, detail=ERROR_MESSAGES.DEFAULT(err))


############################
# GetAdminDetails
############################


@router.get("/admin/details")
async def get_admin_details(request: Request, user=Depends(get_current_user)):
    if request.app.state.config.SHOW_ADMIN_DETAILS:
        admin_email = request.app.state.config.ADMIN_EMAIL
        admin_url = request.app.state.config.ADMIN_URL
        admin_name = None

        print(admin_email, admin_name)

        if admin_email:
            admin = Users.get_user_by_email(admin_email)
            if admin:
                admin_name = admin.name
        else:
            admin = Users.get_first_user()
            if admin:
                admin_email = admin.email
                admin_name = admin.name

        return {
            "name": admin_name,
            "email": admin_email,
            "url": admin_url,
        }
    else:
        raise HTTPException(400, detail=ERROR_MESSAGES.ACTION_PROHIBITED)


############################
# ToggleSignUp
############################


@router.get("/admin/config")
async def get_admin_config(request: Request, user=Depends(get_admin_user)):
    return {
        "SHOW_ADMIN_DETAILS": request.app.state.config.SHOW_ADMIN_DETAILS,
        "ENABLE_SIGNUP": request.app.state.config.ENABLE_SIGNUP,
        "DEFAULT_USER_ROLE": request.app.state.config.DEFAULT_USER_ROLE,
        "DEFAULT_USER_EXPIRE_DURATION": request.app.state.config.DEFAULT_USER_EXPIRE_DURATION,
        "DEFAULT_USER_EXPIRE_UNIT": request.app.state.config.DEFAULT_USER_EXPIRE_UNIT,
        "JWT_EXPIRES_IN": request.app.state.config.JWT_EXPIRES_IN,
        "ENABLE_COMMUNITY_SHARING": request.app.state.config.ENABLE_COMMUNITY_SHARING,
        "ENABLE_MESSAGE_RATING": request.app.state.config.ENABLE_MESSAGE_RATING,
        "ADMIN_URL": request.app.state.config.ADMIN_URL,
        "REGISTERED_EMAIL_SUFFIX": request.app.state.config.REGISTERED_EMAIL_SUFFIX,
        "TURNSTILE_SIGNUP_CHECK": request.app.state.config.TURNSTILE_SIGNUP_CHECK,
        "TURNSTILE_LOGIN_CHECK": request.app.state.config.TURNSTILE_LOGIN_CHECK,
        "TURNSTILE_SITE_KEY": request.app.state.config.TURNSTILE_SITE_KEY,
        "TURNSTILE_SECRET_KEY": request.app.state.config.TURNSTILE_SECRET_KEY,
    }


class AdminConfig(BaseModel):
    SHOW_ADMIN_DETAILS: bool
    ENABLE_SIGNUP: bool
    DEFAULT_USER_ROLE: str
    DEFAULT_USER_EXPIRE_DURATION: int
    DEFAULT_USER_EXPIRE_UNIT: str
    JWT_EXPIRES_IN: str
    ENABLE_COMMUNITY_SHARING: bool
    ENABLE_MESSAGE_RATING: bool
    ADMIN_URL: str
    REGISTERED_EMAIL_SUFFIX: str
    TURNSTILE_SIGNUP_CHECK: bool
    TURNSTILE_LOGIN_CHECK: bool
    TURNSTILE_SITE_KEY: str
    TURNSTILE_SECRET_KEY: str


@router.post("/admin/config")
async def update_admin_config(
    request: Request, form_data: AdminConfig, user=Depends(get_admin_user)
):
    request.app.state.config.SHOW_ADMIN_DETAILS = form_data.SHOW_ADMIN_DETAILS
    request.app.state.config.ENABLE_SIGNUP = form_data.ENABLE_SIGNUP
    request.app.state.config.ADMIN_URL = form_data.ADMIN_URL
    request.app.state.config.REGISTERED_EMAIL_SUFFIX = form_data.REGISTERED_EMAIL_SUFFIX
    request.app.state.config.TURNSTILE_SIGNUP_CHECK = form_data.TURNSTILE_SIGNUP_CHECK
    request.app.state.config.TURNSTILE_LOGIN_CHECK = form_data.TURNSTILE_LOGIN_CHECK
    request.app.state.config.TURNSTILE_SITE_KEY = form_data.TURNSTILE_SITE_KEY
    request.app.state.config.TURNSTILE_SECRET_KEY = form_data.TURNSTILE_SECRET_KEY

    if form_data.DEFAULT_USER_ROLE in ["pending", "user", "vip", "svip", "admin"]:
        request.app.state.config.DEFAULT_USER_ROLE = form_data.DEFAULT_USER_ROLE

    if form_data.DEFAULT_USER_EXPIRE_DURATION > 0:
        request.app.state.config.DEFAULT_USER_EXPIRE_DURATION = (
            form_data.DEFAULT_USER_EXPIRE_DURATION
        )

    if form_data.DEFAULT_USER_EXPIRE_UNIT in ["day", "week", "month", "year"]:
        request.app.state.config.DEFAULT_USER_EXPIRE_UNIT = (
            form_data.DEFAULT_USER_EXPIRE_UNIT
        )

    pattern = r"^(-1|0|(-?\d+(\.\d+)?)(ms|s|m|h|d|w))$"

    # Check if the input string matches the pattern
    if re.match(pattern, form_data.JWT_EXPIRES_IN):
        request.app.state.config.JWT_EXPIRES_IN = form_data.JWT_EXPIRES_IN

    request.app.state.config.ENABLE_COMMUNITY_SHARING = (
        form_data.ENABLE_COMMUNITY_SHARING
    )
    request.app.state.config.ENABLE_MESSAGE_RATING = form_data.ENABLE_MESSAGE_RATING

    return {
        "ADMIN_URL": request.app.state.config.ADMIN_URL,
        "SHOW_ADMIN_DETAILS": request.app.state.config.SHOW_ADMIN_DETAILS,
        "ENABLE_SIGNUP": request.app.state.config.ENABLE_SIGNUP,
        "DEFAULT_USER_ROLE": request.app.state.config.DEFAULT_USER_ROLE,
        "DEFAULT_USER_EXPIRE_DURATION": request.app.state.config.DEFAULT_USER_EXPIRE_DURATION,
        "DEFAULT_USER_EXPIRE_UNIT": request.app.state.config.DEFAULT_USER_EXPIRE_UNIT,
        "JWT_EXPIRES_IN": request.app.state.config.JWT_EXPIRES_IN,
        "ENABLE_COMMUNITY_SHARING": request.app.state.config.ENABLE_COMMUNITY_SHARING,
        "ENABLE_MESSAGE_RATING": request.app.state.config.ENABLE_MESSAGE_RATING,
        "REGISTERED_EMAIL_SUFFIX": request.app.state.config.REGISTERED_EMAIL_SUFFIX,
        "TURNSTILE_SIGNUP_CHECK": request.app.state.config.TURNSTILE_SIGNUP_CHECK,
        "TURNSTILE_LOGIN_CHECK": request.app.state.config.TURNSTILE_LOGIN_CHECK,
        "TURNSTILE_SITE_KEY": request.app.state.config.TURNSTILE_SITE_KEY,
        "TURNSTILE_SECRET_KEY": request.app.state.config.TURNSTILE_SECRET_KEY,
    }


############################
# API Key
############################


# create api key
@router.post("/api_key", response_model=ApiKey)
async def create_api_key_(user=Depends(get_admin_user)):
    api_key = create_api_key()
    success = Users.update_user_api_key_by_id(user.id, api_key)
    if success:
        return {
            "api_key": api_key,
        }
    else:
        raise HTTPException(500, detail=ERROR_MESSAGES.CREATE_API_KEY_ERROR)


# delete api key
@router.delete("/api_key", response_model=bool)
async def delete_api_key(user=Depends(get_admin_user)):
    success = Users.update_user_api_key_by_id(user.id, None)
    return success


# get api key
@router.get("/api_key", response_model=ApiKey)
async def get_api_key(user=Depends(get_admin_user)):
    api_key = Users.get_user_api_key_by_id(user.id)
    if api_key:
        return {
            "api_key": api_key,
        }
    else:
        raise HTTPException(404, detail=ERROR_MESSAGES.API_KEY_NOT_FOUND)
