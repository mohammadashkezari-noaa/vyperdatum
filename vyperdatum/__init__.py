import pathlib
import json
import logging.config
import time
from osgeo import gdal
from vyperdatum.db import DB

log_configuration_dict = json.load(
    open(
        pathlib.Path(
            pathlib.Path(__file__).parent, "logging_conf.json"
        )
    )
)
logging.config.dictConfig(log_configuration_dict)
logging.Formatter.converter = time.gmtime


gdal.UseExceptions()


# commented out as overwrote the original database
# (pyproj.datadir) with the update database
# db_dir = (r"C:\Users\mohammad.ashkezari\Documents"
#           r"\projects\vyperscratch\datum_files")
# db = DB(db_dir=db_dir)
