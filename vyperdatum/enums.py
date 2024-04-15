from enum import Enum


class RootEnum(Enum):
    ...


class PROJDB(RootEnum):
    """
    Proj db attributes.

    Attributes
    ----------
    FILE_NAME
    """
    FILE_NAME = "proj.db"

    TABLE_VERTICAL_CRS = "vertical_crs"
    TABLE_GRID_TRANS = "grid_transformation"
    TABLE_OTHER_TRANS = "other_transformation"
    TABLE_CONCAT_OPS = "concatenated_operation"
