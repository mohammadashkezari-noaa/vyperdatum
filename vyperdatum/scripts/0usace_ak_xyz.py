import os
import glob
import pathlib
import pandas as pd
from vyperdatum.transformer import Transformer
import geopandas as gpd
from shapely.geometry import Point


def get_skiprows(fname: str):
    ln = 0
    with open(fname, "r") as f:
        for line in f:
            ln += 1
            if line.startswith("append_to_abstract=="):
                return ln
    return None


if __name__ == "__main__":
    files = glob.glob(r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\point\USACE\PBA\UTM9N\Original\**\*.XYZ", recursive=True)

    # steps = [
    #         {"crs_from": "ESRI:102445", "crs_to": "EPSG:6319"},
    #         {"crs_from": "EPSG:6319", "crs_to": "EPSG:7912"},
    #         {"crs_from": "EPSG:7912", "crs_to": "EPSG:9989"},
    #         {"crs_from": "EPSG:9990+NOAA:98", "crs_to": "EPSG:9990+NOAA:5537"},
    #         {"crs_from": "EPSG:9989", "crs_to": "EPSG:7912"},
    #         {"crs_from": "EPSG:7912", "crs_to": "EPSG:6319"},
    #         {"crs_from": "EPSG:6319", "crs_to": "EPSG:6337"},
    #         # {"crs_from": "EPSG:6319", "crs_to": "ESRI:102445"},
    #         ]
    steps = [
            {"crs_from": "ESRI:102445", "crs_to": "EPSG:6337"}  # UTM Zone 8N
            # {"crs_from": "ESRI:102445", "crs_to": "EPSG:6338"}  # UTM Zone 9N
            ]
    
    files = [r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\point\USACE\PBA\UTM8N\Original\AK_01_CRA_20220520_CS\AK_01_CRA_20220520_CS_FULL.XYZ"]

    for i, input_file in enumerate(files[:]):
        print(f"{i+1}/{len(files)}: {input_file}")
        df = pd.read_csv(input_file, sep=",", names=["x", "y", "z"], skiprows=get_skiprows(input_file))
        x, y, z = df.x.values, df.y.values, df.z.values
        tf = Transformer(crs_from=steps[0]["crs_from"],
                         crs_to=steps[-1]["crs_to"],
                         steps=steps
                         )
        output_file = input_file.replace("Original", "Manual")
        tf.transform(input_file=input_file,
                    output_file=output_file,
                    pre_post_checks=True,
                    vdatum_check=False,
                    # negate_z=negate_z,
                    # unit_conversion=0.3048006096
                    )

