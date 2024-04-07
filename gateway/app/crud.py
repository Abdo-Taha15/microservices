from sqlmodel import select, Session

from .models import DeRequests, Status
from .tools import _commit_transaction


def _create_de_request(data: dict, session: Session):
    de_request = DeRequests(**data)

    _commit_transaction(de_request, session)

    return de_request


def _get_request_from_hash(hash: str, session: Session):
    return session.exec(
        select(DeRequests).where(DeRequests.file_hash == hash)
    ).one_or_none()


def _get_request_from_id(id: int, session: Session):
    return session.exec(select(DeRequests).where(DeRequests.id == id)).one_or_none()


def _update_de_request(de_request: DeRequests, data: dict, session: Session):

    def __update_status(value: str, de_request: DeRequests):
        if value == "PENDING":
            setattr(de_request, key, Status.PENDING)
        elif value == "IN PROGRESS":
            setattr(de_request, key, Status.IN_PROGRESS)
        elif value == "FAILED":
            setattr(de_request, key, Status.FAILED)
        elif value == "COMPLETED":
            setattr(de_request, key, Status.COMPLETED)

    for key, value in data.items():
        if value:
            if value in Status.list():
                __update_status(value, de_request)
            else:
                setattr(de_request, key, value)

    _commit_transaction(de_request, session)

    return de_request
