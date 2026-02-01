"""
Use TokenAuthentication with Authorization: Bearer <token> to match frontend.
"""
from rest_framework.authentication import TokenAuthentication


class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"
