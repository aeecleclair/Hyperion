import secrets
from datetime import datetime, timedelta

from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.cruds import cruds_users
from app.models import models_core

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=13)
"""
In order to salt and hash password, we use a *passlib* [CryptContext](https://passlib.readthedocs.io/en/stable/narr/quickstart.html) object.

We use "bcrypt" to hash password, a different hash will be added automatically for each password. See [Auth0 Understanding bcrypt](https://auth0.com/blog/hashing-in-action-understanding-bcrypt/) for informations about bcrypt.
deprecated="auto" may be used to do password hash migration, see [Passlib hash migration](https://passlib.readthedocs.io/en/stable/narr/context-tutorial.html#deprecation-hash-migration).
It is improtant to use enough rounds while accounting for the hash computation time. Default is 12. 13 allows for a 0.5 seconds computing delay.
"""

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")
"""
To generate JWT access tokens, we use a *FastAPI* OAuth2PasswordBearer object.
See [FastAPI documentation](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) about JWT.
"""

jwt_algorithme = "HS256"
"""
The algorithme used to generate JWT access tokens
"""


def get_password_hash(password: str) -> str:
    """
    Return a salted hash computed from password. The function use a bcrypt based *passlib* CryptContext.
    Both the salt and the algorithme identifier are included in the hash.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare `plain_password` against its salted hash representation `hashed_password`. The function use a bcrypt based *passlib* CryptContext.
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_token() -> str:
    """
    Generate a 32 bytes cryptographically strong random urlsafe token using the *secrets* library.
    """
    # We use https://docs.python.org/3/library/secrets.html#secrets.token_urlsafe to generate the activation secret token
    return secrets.token_urlsafe(32)


async def authenticate_user(
    db: AsyncSession, email: str, password: str
) -> models_core.CoreUser | None:
    """
    Try to authenticate the user.
    If the user is unknown or the password is invalid return `None`. Else return the user's *CoreUser* representation.
    """
    user = await cruds_users.get_user_by_email(db=db, email=email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(
    settings: Settings,
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a JWT. The token is generated using ACCESS_TOKEN_SECRET_KEY secret.
    """
    if expires_delta is None:
        # We use the default value
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = data.copy()
    expire_on = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire_on})
    encoded_jwt = jwt.encode(
        to_encode, settings.ACCESS_TOKEN_SECRET_KEY, algorithm=jwt_algorithme
    )
    return encoded_jwt


def create_access_token_RS256(
    data: dict,
    expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
) -> str:
    """
    Create a JWT. The token is generated using ACCESS_TOKEN_SECRET_KEY secret.

    "iss": "http://127.0.0.1:8000/",
    "sub": "",
    "aud": client_id,
    "exp": 0,
    # "auth_time": "" # not sure
            "iat": 0,  # Required for oidc
            "nonce": "",  # oidc only, required if provided by the client

    """
    pubandpriv = {
        "p": "4kom51UNpLnMUjSzhu5yYI1kHub2Pp-a_13h2Zd_RFYM3Uyo_KSHRFABK_lf1P_yF7eGmkQqi1MLFrVD8A7bdBAbFZmJg1jOpJL-qjGA3YBhP8OCj_AKqpbaY3VVpWmnS9E0qTARaJuDgN18nQSBf9lJOlSsb9GjHgcRiUhrhd0",
        "kty": "RSA",
        "q": "o8q8UucMLu0Khg9hX08ei4sFNzSLnjxM7QTXMiDWr9G1WSl7r-wwkTJmuFWp_HacrdWQ6fz4ofVcKlGWs_Eaotij8E6C1QNySdyr7Utx5k_T9dwsiAdoZwrr88Ads0XIvDenJgqX9UWhpDoGCpRASWqfT8BQ6m4DdFt3z_LnaoE",
        "d": "kKFl4bVvpSUzHFt3HSj7q7l55Itrk6GvpugMoqATyJ5cE6gXcl96IW1WuAcW8j7sikmwmvXjByfhSvixITkzGDHG0-4p-oxxjih3r4CYGawN_4-YCgCaD_tV_nZIRbPupIosVyIcnOKsXbcGVEHx4csbChYaiXVRD0m7mxjAsJgpx2lOe8Gc4cJTZ3gWjSVA7JChPGVFglIYHJo65u2KlCY0TCmojqKdyNtSxyRn67ZgDXbGsN7pxOMjUYykX4zAD4tPOhJXRPy7vcTpkUa4EpO0QqJ7RK5GQ1uYpPGSV-KJjpq8h0tZLiG9Dq5n_veeQ4ajWlnuhKiH980Vfi1oAQ",
        "e": "AQAB",
        "use": "sig",
        "kid": "sig-16525550979",  # "sig-1652555097",
        "qi": "myiQFKf_pFmgmCJ6xFQO7quBSbU6yI_2-n7nVcGenyq7vx89Pp5MNVgl_l-OtiNTucuku8BEf_kAbf8OWz0ANNIT2A0du6HYT8arK_-RwLvHiXu72XVTBQZBpqaprrn5bXnbT7u-1Fs0c-ykHdXJIxalArP7A1v94Cl5BeBM298",
        "dp": "WCsqM1JJaZhXCuSr2nQHrqUIkJ3O7iGD4-HxgLVtifO5OXSIF0AH0E8X1clpVHWRHzqLwIm0xepKVMO1v9AaI4Ou-eCD2uB8S1VW0ntNSYCe45hKw8h0b3ktiDkMcNHUtE7EJPOspMSLHWevCQLbbjP8OzUIptzYoHeClqnX8yU",
        "alg": "RS256",
        "dq": "KJ9Zgb4n-WN03rbl0XuP-c_q5Tw0_HO8KHSw4o_ebxC1x31QXdtYWEqFy2YDmMfaKAr1u_Kvv4tY5m4B0HMVxhmw3yK5tBb8u3DtexbhEtvtl-aZbMtZi2TcDEIzm4jNNlEfNYIfGgfBBTgW03zdTNgS1va9msbaOHuPBZYa6wE",
        "n": "kMhrv7o-00T2kw2jF_J1O9kLRQOlFudYvCmunQ5uPfqbQ0IIpMKwN7ZEj5PyRbBhoyWQ3yHC9NPwvsyqdzH9mMFyaBikdGVXBbeKmMjc9PU4zrR_i3mwY2_PrPY4IuV5TLEv8gq-maAXxrQr5vGeUcq2rbdJTwjY3jXRMGU2q-AHjtq13gDtrR-4yYPVumnjzAaZrntpDLx_SHBn7fyl8KxdGsZcO6xq5Y9Wa9ClVvSsYj724zvWeSUbqZ3VxV-mjzKbYSITeUilNrgeavpHKGRo_6tU3soPruOvAU-2gdDLLdXszIv-jU3LFAUw8p1Ey92OCwf98bjr4qRtuAb2XQ",
    }

    to_encode = data.copy()
    expire_on = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire_on})
    encoded_jwt = jwt.encode(to_encode, pubandpriv, algorithm="RS256")
    return encoded_jwt
