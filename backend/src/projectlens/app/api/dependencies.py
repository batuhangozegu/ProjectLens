from fastapi import Request
from sqlalchemy.orm import Session


def get_session(request: Request):
    factory = request.app.state.session_factory
    with factory() as session:
        yield session
