import numpy as np
import tensorflow as tf
from paddleocr import PaddleOCR
import re

ocr = PaddleOCR(use_angle_cls=True, lang="ch")


def extract_text(img):
    result = ocr.ocr(img, cls=False)
    return result[0]


# def get_threshold(result):
#     threshold = 0
#     if result:
#         for line in result:
#             threshold += line[0][2][1] - line[0][0][1]
#         threshold /= len(result)
#     return threshold


def intersection(box_1, box_2):
    return [box_2[0], box_1[1], box_2[2], box_1[3]]


def iou(box_1, box_2):
    x_1 = max(box_1[0], box_2[0])
    y_1 = max(box_1[1], box_2[1])
    x_2 = min(box_1[2], box_2[2])
    y_2 = min(box_1[3], box_2[3])

    inter = abs(max((x_2 - x_1, 0)) * max((y_2 - y_1), 0))
    if inter == 0:
        return 0

    box_1_area = abs((box_1[2] - box_1[0]) * (box_1[3] - box_1[1]))
    box_2_area = abs((box_2[2] - box_2[0]) * (box_2[3] - box_2[1]))

    return inter / float(box_1_area + box_2_area - inter)


def get_data(img, output):
    image_height = img.shape[0]
    image_width = img.shape[1]

    boxes = [line[0] for line in output]
    texts = [line[1][0] for line in output]
    probabilities = [line[1][1] for line in output]

    horiz_boxes = []
    vert_boxes = []

    for box in boxes:
        x_h, x_v = 0, int(box[0][0])
        y_h, y_v = int(box[0][1]), 0
        width_h, width_v = image_width, int(box[2][0] - box[0][0])
        height_h, height_v = int(box[2][1] - box[0][1]), image_height

        horiz_boxes.append([x_h, y_h, x_h + width_h, y_h + height_h])
        vert_boxes.append([x_v, y_v, x_v + width_v, y_v + height_v])

    horiz_out = tf.image.non_max_suppression(
        horiz_boxes,
        probabilities,
        max_output_size=1000,
        iou_threshold=0.1,
        score_threshold=float("-inf"),
        name=None,
    )

    horiz_lines = np.sort(np.array(horiz_out))

    vert_out = tf.image.non_max_suppression(
        vert_boxes,
        probabilities,
        max_output_size=1000,
        iou_threshold=0.1,
        score_threshold=float("-inf"),
        name=None,
    )
    vert_lines = np.sort(np.array(vert_out))

    out_array = ["" for _ in range(len(horiz_lines))]

    unordered_boxes = []

    for i in vert_lines:
        unordered_boxes.append(vert_boxes[i][0])

    ordered_boxes = np.argsort(unordered_boxes)

    for i in range(len(horiz_lines)):
        for j in range(len(vert_lines)):
            resultant = intersection(
                horiz_boxes[horiz_lines[i]], vert_boxes[vert_lines[ordered_boxes[j]]]
            )

            for b in range(len(boxes)):
                the_box = [
                    boxes[b][0][0],
                    boxes[b][0][1],
                    boxes[b][2][0],
                    boxes[b][2][1],
                ]
                if iou(resultant, the_box) > 0.1:
                    out_array[i] += f" {texts[b]}"

    out_array = np.array(out_array)
    return out_array


def is_valid(line: str, text: str):
    if line.lower().find(f"{text}") == -1:
        return False
    return True


# def x_intercept(first, second, thr: float = 0):
#     if (
#         (
#             first[0] <= second[0]
#             and first[2] <= second[2]
#             and first[0] < second[2]
#             and first[2] > second[0]
#             and (abs(first[2] - second[0] > thr) if thr != 0 else True)
#         )
#         or (
#             first[0] >= second[0]
#             and first[2] >= second[2]
#             and first[0] < second[2]
#             and first[2] > second[0]
#             and (abs(second[2] - first[0] > thr) if thr != 0 else True)
#         )
#         or (
#             first[0] <= second[0]
#             and first[2] >= second[2]
#             and first[0] < second[2]
#             and first[2] > second[0]
#             and (abs(second[2] - second[0] > thr) if thr != 0 else True)
#         )
#         or (
#             first[0] >= second[0]
#             and first[2] <= second[2]
#             and first[0] < second[2]
#             and first[2] > second[0]
#             and (abs(first[2] - first[0] > thr) if thr != 0 else True)
#         )
#     ):
#         return True
#     return False


# def y_intercept(first, second, thr: float = 0):
#     if (
#         (
#             first[1] <= second[1]
#             and first[3] <= second[3]
#             and first[1] < second[3]
#             and first[3] > second[1]
#             and (abs(first[3] - second[1] > thr) if thr != 0 else True)
#         )
#         or (
#             first[1] >= second[1]
#             and first[3] >= second[3]
#             and first[1] < second[3]
#             and first[3] > second[1]
#             and (abs(second[3] - first[1] > thr) if thr != 0 else True)
#         )
#         or (
#             first[1] <= second[1]
#             and first[3] >= second[3]
#             and first[1] < second[3]
#             and first[3] > second[1]
#             and (abs(second[3] - second[1] > thr) if thr != 0 else True)
#         )
#         or (
#             first[1] >= second[1]
#             and first[3] <= second[3]
#             and first[1] < second[3]
#             and first[3] > second[1]
#             and (abs(first[3] - first[1] > thr) if thr != 0 else True)
#         )
#     ):
#         return True
#     return False


# def get_coor(first, second):
#     return (
#         min(first[0], second[0]),
#         min(first[1], second[1]),
#         max(first[2], second[2]),
#         max(first[3], second[3]),
#     )


# def prepare_rows(result, threshold):
#     """
#     ** columns are seperated **
#     * add each element from the extracted text to its row according to the coordinate intersection with respect to the average length of the row
#     * the intersection is True if the intersected part is bigger than the threshold number (ex: half of the average length of the row)
#     * return the column of the arranged rows
#     """
#     col = []
#     row = []
#     col_coor = []
#     intersection = False
#     for i, line in enumerate(result):
#         line_coor = (
#             line[0][0][0],
#             line[0][0][1],
#             line[0][1][0],
#             line[0][2][1],
#         )
#         if i == 0:
#             row.append(line)
#             if i == len(result) - 1:
#                 col_coor.append(line_coor)
#                 col.append(sorted(row.copy(), key=lambda x: x[0][0][0]))
#             continue

#         row_coor = (
#             row[-1][0][0][0],
#             row[-1][0][0][1],
#             row[-1][0][1][0],
#             row[-1][0][2][1],
#         )
#         if y_intercept(row_coor, line_coor, thr=threshold * 0.5):
#             row.append(line)
#         else:
#             col.append(sorted(row.copy(), key=lambda x: x[0][0][0]))
#             row = [line]
#         if i == len(result) - 1:
#             col.append(sorted(row.copy(), key=lambda x: x[0][0][0]))

#         if len(row) < 2:
#             continue
#         for ele in row:
#             line_coor = (
#                 ele[0][0][0],
#                 ele[0][0][1],
#                 ele[0][1][0],
#                 ele[0][2][1],
#             )
#             for idx, coor in enumerate(col_coor):
#                 if x_intercept(coor, line_coor):
#                     intersection = True
#                     col_coor[idx] = get_coor(coor, line_coor)
#             if not intersection:
#                 col_coor.append(line_coor)
#             intersection = False
#     col_coor = list(sorted(col_coor, key=lambda x: x[0]))
#     for i in range(len(col_coor)):
#         if i >= len(col_coor) - 1:
#             break
#         if x_intercept(col_coor[i], col_coor[i + 1]):
#             col_coor[i] = get_coor(col_coor[i], col_coor[i + 1])
#             col_coor.pop(i + 1)
#             i -= 1
#     return col, col_coor
