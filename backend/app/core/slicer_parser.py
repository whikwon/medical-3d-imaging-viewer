import json

import nrrd
import numpy as np

from .constant import LPS
from .coordinate import CoordinateSystem, PatientCoordinates


class SlicerSegmentationNrrd:
    def __init__(self, file_path: str):
        self.data, self.header = nrrd.read(file_path)
        # Slicer default setting, https://discourse.slicer.org/t/slicer-nrrd-coordinate-systems/19827/2
        assert self.coordinate_system == LPS

    @property
    def coordinate_system(self):
        return self.header["space"]

    @property
    def direction(self):
        return self.header["space directions"]

    @property
    def origin(self):
        return self.header["space origin"]

    def get_point_cloud(self, mask_value: int):
        coords = np.stack(np.where(self.data == mask_value), axis=-1)
        coords = (self.direction @ coords.T).T + self.origin
        return PatientCoordinates(coords, CoordinateSystem.LPS)


class SlicerMarkupsMrkJson:
    def __init__(self, file_path: str):
        with open(file_path, "r") as f:
            self.data = json.load(f)
        assert self.coordinate_system == LPS

    @property
    def coordinate_system(self):
        return self.data["markups"][0]["coordinateSystem"]

    @property
    def coordinate_units(self):
        return self.data["markups"][0]["coordinateUnits"]

    @property
    def control_points(self):
        """
        position은 coordinateSystem에 맞는 값으로 나오고, orientation은 RAS로 가기 위한 값으로 보인다.

        Reference
        ---------
        .. [1] https://raw.githubusercontent.com/slicer/slicer/master/Modules/Loadable/Markups/Resources/Schema/markups-schema-v1.0.3.json#
        """
        markups = self.data["markups"][0]
        if "controlPoints" in markups:
            coords = np.stack(
                [np.array(i["position"]) for i in markups["controlPoints"]], axis=0
            )
            return PatientCoordinates(coords, CoordinateSystem.LPS)

    @property
    def control_points_with_label(self):
        markups = self.data["markups"][0]
        if "controlPoints" in markups:
            data = dict()
            for d in markups["controlPoints"]:
                label = d["label"]
                position = PatientCoordinates(
                    np.array(d["position"]), CoordinateSystem.LPS
                )
                data.update({label: position})
            return data

    @property
    def cips(self):
        markups = self.data["markups"][0]
        if "controlPoints" in markups:
            cips = []
            for d in markups["controlPoints"]:
                label = d["label"]
                if label.startswith("cip"):
                    cips.append(d["position"])
            if cips:
                return PatientCoordinates(np.stack(cips, axis=0), CoordinateSystem.LPS)
        return []
