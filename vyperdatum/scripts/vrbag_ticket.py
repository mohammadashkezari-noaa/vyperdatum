import h5py
from io import BytesIO
from lxml import etree
import numpy as np
import pyproj as pp
from pyproj.enums import WktVersion
from vyperdatum.utils.raster_utils import raster_metadata


def change_wkt(fname: str,
                wkt_h: str,
                wkt_v: str
                ) -> None:
    """
    Update the xml metadata's horizontal, and vertical WKTs with new values.
    """
    bag = h5py.File(fname)
    meta = bag["BAG_root/metadata"]
    buffer = BytesIO(meta[()])
    tree = etree.parse(buffer)
    root = tree.getroot()
    gco = ".//{" + root.nsmap['gco'] + "}"
    root.findall(f"{gco}CharacterString")[6].text = wkt_h
    root.findall(f"{gco}CharacterString")[7].text = "WKT"

    root.findall(f"{gco}CharacterString")[8].text = wkt_v
    root.findall(f"{gco}CharacterString")[9].text = "WKT"
    # tree.write(xml_fname)
    # xml = etree.tostring(root, pretty_print=True).decode("ascii")
    xmet = etree.tostring(root).decode()
    bag.close()
    bag = h5py.File(fname, mode="r+")
    root = bag.require_group("/BAG_root")
    del bag["/BAG_root/metadata"]
    metadata = np.array(list(xmet), dtype="S1")
    root.create_dataset("metadata",
                        maxshape=(None,),
                        data=metadata,
                        compression="gzip",
                        compression_opts=9
                        )
    bag.close()
    return

input_file = r"C:\Users\mohammad.ashkezari\Desktop\H13549_MB_VR_MLLW_1of1.bag"

change_wkt(fname=input_file,
           wkt_h=pp.CRS("EPSG:6339").to_wkt(version=WktVersion.WKT1_GDAL),
           wkt_v=pp.CRS("EPSG:5866").to_wkt(version=WktVersion.WKT1_GDAL)
           )

print(raster_metadata(input_file))