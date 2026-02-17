from fastapi import Security, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.api import Environment

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    env: Environment = Depends(odoo_env),
):
    token = credentials.credentials
    api_key_record = (
        env["auth.api.key"].sudo().search([("key", "=", token)], limit=1)
    )
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key_record.user_id
