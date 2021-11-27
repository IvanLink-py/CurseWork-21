from dataclasses import dataclass
from enum import Enum, auto

import cv2
import numpy as np


class VideoSetter:
    def __init__(self, path):
        self.path = path
        self._capture = cv2.VideoCapture(path)
        self.fps = self._capture.get(5)
        self.cropping = []
        self.croppingArea = [(), ()]

        self.isCropping = False
        self.isRotating = False
        self.isPlacement = False
        self.isNaming = False

        self.scaleF = 1
        self.rotate = 0
        self.digits = []
        self.segmentsHistory = []
        self.nameHistory = []

        _, self.source_img = self._capture.read()
        self.frame = self.source_img.copy()

        self.sizeY, self.sizeX, _ = self.frame.shape
        self.originalSize = (self.sizeX, self.sizeY)

        self.ratio = self.sizeY / self.sizeX

    def set(self):
        self.showFrame()
        cv2.setMouseCallback('Frame', self.onClick)

        self.crop()
        self.rotating()
        self.placement()
        self.naming()

        cv2.destroyWindow('Frame')

    def _scale(self):
        self.sizeY, self.sizeX, _ = self.frame.shape
        if self.sizeX > 900 or self.sizeY > 900:
            self.frame = cv2.resize(self.frame, (round(900 / self.ratio), 900))
            self.scaleF = 900 / self.sizeY

        else:
            self.scaleF = 1

    def _rotate(self):
        self.frame = np.ascontiguousarray(np.rot90(self.frame, self.rotate), dtype=np.uint8)

    def _drawSegments(self):
        [d.draw() for d in self.digits]

    def crop(self):
        self.isCropping = True
        while True:
            self.showFrame()
            cv2.setWindowTitle('Frame', 'Cropping')
            key = cv2.waitKey()
            if key == 13:
                break
            elif key == 8:
                self.cropping.pop(-1)
                self.showFrame()
            elif key == -1:
                quit()
            else:
                print(key)

        self.isCropping = False

    def rotating(self):
        self.isRotating = True
        while True:
            self.showFrame()
            cv2.setWindowTitle('Frame', 'Rotating')
            key = cv2.waitKey()
            if key == 13:
                break
            elif ord('r') == key:
                self.rotate = (self.rotate + 1) % 4
            elif key == -1:
                quit()
            else:
                print(key)

        self.isRotating = False

    def placement(self):
        self.isPlacement = True

        while True:
            self.showFrame()
            cv2.setWindowTitle('Frame', 'Placement')
            key = cv2.waitKey()
            if key == 13:
                break
            elif key == -1:
                quit()
            elif key == 8:
                self.removeLast()
            else:
                print(key)

        self.isPlacement = False

    def naming(self):
        self.isNaming = True
        self.namer = SegmentName.getName()
        self.noNamedDigits = self.digits.copy()

        self.showFrame()
        cv2.setWindowTitle('Frame', 'Naming')
        while True:
            key = cv2.waitKey()
            if key == 8:
                self.nameHistory[-1].name = None
                self.nameHistory.pop(-1)
                self.showFrame()
            elif key == 13 and self.allNamed():
                break

        self.isNaming = False

    def showFrame(self):
        self.frame = self.source_img.copy()
        for crop in self.cropping:
            self.frame = self.frame[crop[0][1]:crop[1][1], crop[0][0]:crop[1][0]]

        self._scale()
        self._rotate()
        self._drawSegments()

        cv2.imshow('Frame', self.frame)

    def convertCords(self, pos):

        # Координаты с экрана → Кординаты исходного кадра
        pos = (round(pos[0] / self.scaleF), round(pos[1] / self.scaleF))

        for crop in self.cropping:
            pos = (pos[0] + crop[0][0], pos[1] + crop[0][1])

        if self.rotate == 0:
            pos = (pos[0], pos[1])
        elif self.rotate == 1:
            pos = (self.originalSize[0] - pos[1], pos[0])
        elif self.rotate == 2:
            pos = (self.originalSize[0] - pos[0], self.originalSize[1] - pos[1])
        elif self.rotate == 3:
            pos = (pos[1], self.originalSize[1] - pos[0])
        else:
            raise IndexError

        return pos

    def showedCords(self, pos):

        # Кординаты исходного кадра → Координаты на экране

        if self.rotate == 0:
            pos = (pos[0], pos[1])
        elif self.rotate == 1:
            pos = (pos[1], self.originalSize[0] - pos[0])
        elif self.rotate == 2:
            pos = (self.originalSize[0] - pos[0], self.originalSize[1] - pos[1])
        elif self.rotate == 3:
            pos = (self.originalSize[1] - pos[1], pos[0])

        else:
            raise IndexError

        for crop in self.cropping:
            pos = (pos[0] - crop[0][0], pos[1] - crop[0][1])

        pos = (round(pos[0] * self.scaleF), round(pos[1] * self.scaleF))

        return pos

    def onClick(self, event, posX, posY, flags, param):
        pos = self.convertCords((posX, posY))
        if self.isCropping:
            if event == 1:
                self.croppingArea[0] = pos
            elif event == 4:
                self.croppingArea[1] = pos
                self.cropping.append(tuple(self.croppingArea))
                self.croppingArea = [(), ()]
                self.showFrame()
        elif self.isPlacement:
            if event == 1:
                self.setSegment(pos)
                self.showFrame()

        elif self.isNaming:
            if event == 1:

                for d in self.noNamedDigits:
                    if d.isNamed():
                        d.isNaming = False
                        continue
                    noNames = [s for s in d.segments if s.name is None]
                    d.isNaming = True
                    break

                if noNames:
                    seg = min(noNames, key=lambda p: (p.pos[0] - pos[0]) ** 2 + (p.pos[1] - pos[1]) ** 2)
                    seg.name = self.namer.__next__()
                    self.nameHistory.append(seg)

                self.showFrame()

    def setSegment(self, pos):
        if not self.digits:
            self.digits.append(Digit(self))
        for d in self.digits:
            if d.isFull():
                continue
            d.place(pos)
            break
        else:
            self.digits.append(Digit(self))
            self.digits[-1].place(pos)

    def removeLast(self):
        if self.segmentsHistory:
            seg = self.segmentsHistory[-1]
            digit = seg.digit
            digit.segments.remove(seg)
            self.segmentsHistory.remove(seg)
            if digit.isEmpty():
                self.digits.remove(digit)
        self.showFrame()

    def allNamed(self):
        return all([d.isNamed() for d in self.digits])

    def export(self):
        return VideoData(0, int(self.fps), self.digits)


class Segment:
    size = 7

    def __init__(self, digit, position, setter):
        self.digit = digit
        self.pos = position
        self.videoSetter = setter
        self.name = None

    def scan(self, frame):
        return False

    def getColor(self, frame, pos=None):
        if pos is None:
            pos = self.pos
        return frame[pos[1], pos[0]].tolist()

    def draw(self, frame):
        pos = self.videoSetter.showedCords(self.pos)
        cv2.rectangle(frame,
                      (pos[0] - self.size, pos[1] - self.size),
                      (pos[0] + self.size, pos[1] + self.size),
                      self.getColor(frame, pos),
                      -1)

        color = 0, 0, 0
        if self.name is not None:
            color = 0, 255, 0
        elif self.digit.isNaming:
            color = 255, 0, 0

        cv2.rectangle(frame,
                      (pos[0] - self.size, pos[1] - self.size),
                      (pos[0] + self.size, pos[1] + self.size),
                      color,
                      1)


class Digit:
    def __init__(self, video):
        self.segments = []
        self.video = video
        self.isNaming = False

    def place(self, position):
        new_seg = Segment(self, position, self.video)
        self.segments.append(new_seg)
        self.video.segmentsHistory.append(new_seg)

    def scan(self, frame):
        data = [seg.scan(frame) for seg in self.segments]

    def draw(self):
        [seg.draw(self.video.frame) for seg in self.segments]

    def removeLast(self):
        self.segments.pop(-1)

    def isFull(self):
        return len(self.segments) >= 7

    def isNamed(self):
        return all([s.name is not None for s in self.segments])

    def isEmpty(self):
        return not self.segments


@dataclass
class VideoData:
    startFrame: int
    step: int
    digits: list


class SegmentName(Enum):
    U = auto()
    UL = auto()
    UR = auto()
    M = auto()
    BL = auto()
    BR = auto()
    B = auto()

    @staticmethod
    def getName():
        while True:
            for name in SegmentName:
                yield name