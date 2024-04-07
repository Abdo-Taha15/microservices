from sqlmodel import select, Session

from models import DeRequests


def _get_request_from_hash(hash: str, session: Session):
    return session.exec(
        select(DeRequests).where(DeRequests.file_hash == hash)
    ).one_or_none()
