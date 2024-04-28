from sqlmodel import select, Session

from models import DeRequests


def _get_request_from_id(id: int, session: Session):
    return session.exec(select(DeRequests).where(DeRequests.id == id)).one_or_none()
