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
