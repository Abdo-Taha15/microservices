import os
import cv2
import numpy as np
from pdf2image import convert_from_bytes
from typing import BinaryIO
import hashlib
from sqlmodel import Session


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


def get_img(uploaded_file):
    # convert file bytes into cv2 image
    file_bytes = np.asarray(bytearray(uploaded_file), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)
    return img


def convert_pdf_to_image(filename):
    # * returns back a list of images according to the pdf pages
    pdf_pages = convert_from_bytes(filename, 500)
    return pdf_pages


def filter_color(img, lower_val, upper_val):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # define range of black color in HSV

    lower_val = lower_val

    upper_val = upper_val

    # Threshold the HSV image to get only black colors

    mask = cv2.inRange(hsv, lower_val, upper_val)

    # Bitwise-AND mask and original image

    res = cv2.bitwise_not(mask)
    return res
