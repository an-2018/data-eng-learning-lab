import os
from functools import lru_cache
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .config import DEV_AUTH
from .db import User, get_db

bearer = HTTPBearer(auto_error=False)

@lru_cache
def jwks():
    url = os.getenv('OIDC_JWKS_URL', '')
    if not url.startswith('https://'):
        raise RuntimeError('A HTTPS OIDC_JWKS_URL is required')
    return jwt.PyJWKClient(url)

def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)):
    if DEV_AUTH and credentials and credentials.credentials == 'local-development':
        uid, email = 'local-learner', 'learner@localhost'
    else:
        if not credentials:
            raise HTTPException(401, 'Sign in to continue')
        try:
            key = jwks().get_signing_key_from_jwt(credentials.credentials)
            claims = jwt.decode(credentials.credentials, key.key, algorithms=['RS256'], audience=os.environ['OIDC_AUDIENCE'], issuer=os.environ['OIDC_ISSUER'], options={'require':['exp','sub','iss','aud']})
            email = claims.get('email', '').lower()
            if not claims.get('email_verified') or email not in [x.strip().lower() for x in os.getenv('INVITED_EMAILS','').split(',')]:
                raise HTTPException(403, 'This account has not been invited')
            uid = claims['iss'] + '|' + claims['sub']
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(401, 'Your sign-in has expired or is invalid')
    user = db.get(User, uid)
    role = 'admin' if email in os.getenv('ADMIN_EMAILS','').split(',') else 'learner'
    if not user:
        user = User(id=uid, email=email, role=role)
        db.add(user)
    else:
        user.role = role
    db.commit()
    return user
