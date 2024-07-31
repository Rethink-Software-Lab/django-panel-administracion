from graphql_jwt.utils import jwt_payload


def custom_jwt_payload(user, context=None):
    payload = jwt_payload(user, context)
    payload["id"] = user.id
    payload["rol"] = user.rol
    return payload
