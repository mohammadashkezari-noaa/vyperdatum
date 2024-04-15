import pathlib
import json
import logging.config
import time
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

# append the updated database to the pyproj data_dir path
db_dir = (r"C:\Users\mohammad.ashkezari\Documents"
          r"\projects\vyperscratch\datum_files")
db = DB(db_dir=db_dir)
