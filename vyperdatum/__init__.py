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
