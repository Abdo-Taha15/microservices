from typing import BinaryIO
import hashlib
from sqlmodel import Session
import os


def hash_file(file: BinaryIO):
    """ "This function returns the SHA-256 hash
    of the file passed into it"""
    BLOCK_SIZE = 65536

    # make a hash object
    h = hashlib.sha256()

    # open file for reading in binary mode
    # loop till the end of the file
    chunk = 0
    while chunk != b"":
        # read only 65536 bytes at a time
        chunk = file.read(BLOCK_SIZE)
        h.update(chunk)

    # return the hex representation of digest
    return h.hexdigest()


def _commit_transaction(obj, session: Session):
    session.add(obj)
    session.flush()
    session.refresh(obj)
