import cv2
import numpy as np
from pdf2image import convert_from_bytes


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
