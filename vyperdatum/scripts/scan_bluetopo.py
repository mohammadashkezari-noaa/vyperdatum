import os, sys, pathlib
import pyproj as pp
sys.path.append("..")
from transformer import Transformer
from utils.raster_utils import raster_metadata
import pandas as pd
from collections import Counter


def scan_blue(parent_dir: str, scan_file):
    """
    Walk through the parent directory and return the absolute path of all .tiff files.
    """
    tiff_files = []
    crs_name = []
    hori_auth = []
    vert_auth = []    
    xipe_vertical_datum_wkt = []
    counter = 0
    for (dirpath, dirnames, filenames) in os.walk(parent_dir):
        for filename in filenames:
            ef = filename.split(".")[0]
            if ef.endswith("_difference") or ef.endswith("_base"):
                continue
            if filename.endswith(".tiff") or filename.endswith(".tif"):
                counter += 1
                try:
                    meta = raster_metadata(os.sep.join([dirpath, filename]))
                except Exception as e:
                    tiff_files.append(os.sep.join([dirpath, filename]))
                    crs_name.append(str(e))
                    hori_auth.append("")
                    vert_auth.append("")
                    xipe_vertical_datum_wkt.append("")
                    pd.DataFrame({"filename": tiff_files, "crs_name": crs_name, "hori_auth": hori_auth, "vert_auth": vert_auth, "xipe_vertical_datum_wkt": xipe_vertical_datum_wkt}).to_csv(scan_file, index=False)
                    continue
                input_crs = pp.CRS(meta["wkt"])
                input_horizontal_crs = pp.CRS(input_crs.sub_crs_list[0])
                input_vertical_crs = pp.CRS(input_crs.sub_crs_list[1])                

                tiff_files.append(os.sep.join([dirpath, filename]))
                crs_name.append(input_crs.name)
                hori_auth.append(input_horizontal_crs.to_authority())
                vert_auth.append(input_vertical_crs.to_authority())
                xipe_vertical_datum_wkt.append(meta["vertical_datum_wkt"])
                if counter % 100 == 0:
                    print(counter)
                    pd.DataFrame({"filename": tiff_files, "crs_name": crs_name, "hori_auth": hori_auth, "vert_auth": vert_auth, "xipe_vertical_datum_wkt": xipe_vertical_datum_wkt}).to_csv(scan_file, index=False)
    pd.DataFrame({"filename": tiff_files, "crs_name": crs_name, "hori_auth": hori_auth, "vert_auth": vert_auth, "xipe_vertical_datum_wkt": xipe_vertical_datum_wkt}).to_csv(scan_file, index=False)
    return tiff_files







def analyze_blue(bf):
    df = pd.read_csv(bf)
    # df["vyper"] = df["xipe_vertical_datum_wkt"].str.split("vyperdatum=")
    print(f"{'-'*80}")
    print(f"Unique value counts:\n{df.nunique()}")
    # print(df["xipe_vertical_datum_wkt"].value_counts())

    vdatums, vypers, pipelines = [], [], []
    for i, r in df.iterrows():
        xipe = r["xipe_vertical_datum_wkt"]
        if xipe != xipe:
            continue
        if len(xipe.split("vdatum=")) < 2:
            vdatums.append("NO VDATUM")
        else:
            vdatums.append(xipe.split("vdatum=")[1].split(",")[0])

        if len(xipe.split("vyperdatum=")) < 2:
            vypers.append("NO VYPERDATUM")
        else:
            vypers.append(xipe.split("vyperdatum=")[1].split(",")[0])

        if len(xipe.split("pipelines=[")) < 2:
            pipelines.append("NO PIPELINES")
        else:
            pipes = xipe.split("pipelines=[")[1].split("]")[0].split(";")
            for pipe in pipes:
                pipelines.append(pipe)
    print(f"{'-'*10}\nvdatum version counts:\n{Counter(vdatums)}")
    print(f"{'-'*10}\nvyperdatums version counts:\n{Counter(vypers)}")
    print(f"{'-'*10}\npipelines version counts:\n{Counter(pipelines)}")
    print(f"{'-'*80}")
    return


if __name__ == "__main__":
    scan_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\blue_scan.csv"
    # scan_blue(r"W:\Xipe\BlueTopo_Products\Delivered", scan_file)
    analyze_blue(scan_file)

