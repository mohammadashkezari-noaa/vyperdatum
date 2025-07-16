import os
from typing import Optional, List, Union
from pathlib import Path
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from vyperdatum.transformer import Transformer


class XYZ:
    def __init__(self,
                 input_file: str,
                 skiprows: Optional[int] = None,
                 col_names: Optional[List[str]] = None
                 ):
        self.input_file = input_file
        self.skiprows = self._detect_data_start() if skiprows is None else skiprows
        self.col_names = col_names
        self.df = self.parse()

    def _detect_data_start(self) -> Optional[int]:
        with open(self.input_file, "r") as f:
            for i, line in enumerate(f):
                parts = line.strip().split(",")
                if len(parts) >= 3:
                    try:
                        float(parts[0])
                        float(parts[1])
                        float(parts[2])
                        return i
                    except ValueError:
                        continue
        raise ValueError("No valid data lines found in file.")

    def parse(self) -> pd.DataFrame:
        """
        Reads the .XYZ file into a pandas DataFrame.
        If self.col_names is not set, assumes the first three columns are x, y, z.

        Returns:
            pd.DataFrame: the parsed data
        """
        df = pd.read_csv(self.input_file, sep=",", skiprows=self.skiprows)
        num_cols = df.shape[1]
        if self.col_names:
            base_names = self.col_names
        else:
            base_names = ["x", "y", "z"]
        if num_cols > len(base_names):
            column_names = base_names + [f"col{i}" for i in range(len(base_names)+1, num_cols + 1)]
        else:
            column_names = base_names[:num_cols]
        df.columns = column_names
        return df

    def transform(self,
                  crs_from: str,
                  crs_to: str,
                  steps: Optional[List[dict]] = None
                  ) -> pd.DataFrame:
        """
        Transform the coordinates from one CRS to another using a Transformer.

        Parameters:
        -----------
            crs_from (str): The source coordinate reference system.
            crs_to (str): The target coordinate reference system.
        """
        tf = Transformer(crs_from=crs_from, crs_to=crs_to, steps=steps)
        x, y, z = self.df["x"].values, self.df["y"].values, self.df["z"].values
        success, xt, yt, zt = tf.transform_points(x, y, z,
                                                  always_xy=True,
                                                  allow_ballpark=False,
                                                  only_best=True,
                                                  vdatum_check=False)
        if not success:
            raise ValueError("Transformation failed.")
        self.df["x_t"], self.df["y_t"], self.df["z_t"] = xt, yt, zt
        return self.df

    def to_gpkg(self,
                crs: str,
                output_file: str) -> None:
        try:
            x, y, z = self.df["x"].values, self.df["y"].values, self.df["z"].values
            tdf = pd.DataFrame({"x": x, "y": y, "z": z})
            temp_file = Path(output_file).with_suffix(".tmp.csv")
            tdf.to_csv(temp_file, index=False)
            tdf["geometry"] = tdf.apply(lambda row: Point(row["x"], row["y"], row["z"]), axis=1)
            gdf = gpd.GeoDataFrame(tdf, geometry="geometry", crs=crs)
            gdf.to_file(output_file, driver="GPKG")
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return


# from vyperdatum.pipeline import Pipeline
# import sys
# # print(Pipeline(crs_from="ESRI:103060", crs_to="EPSG:6318").graph_steps())
# print(Pipeline(crs_from="NOAA:1731", crs_to="EPSG:6319").graph_steps())
# sys.exit()



input_file = r"C:\Users\mohammad.ashkezari\Documents\projects\vyperdatum\untrack\data\point\MLG\Original\AR_01_BAR_20240117_PR\AR_01_BAR_20240117_PR.XYZ"
crs_from = "ESRI:103295+NOAA:65" # MLG depth
# crs_from = "ESRI:103060+NOAA:65" # deprecated but 103295 has no transform path to NAD83
crs_to = "EPSG:6344+NOAA:74"  # MLLW depth


# steps = [{"crs_from": "ESRI:103295", "crs_to": "EPSG:6783", "v_shift": False},
#          {"crs_from": "EPSG:6318+NOAA:65", "crs_to": "EPSG:6318+NOAA:78", "v_shift": True},
#          {"crs_from": "EPSG:6318", "crs_to": "EPSG:6344", "v_shift": False}
#          ]

steps = [{"crs_from": "ESRI:103295", "crs_to": "EPSG:6783", "v_shift": False},
         {"crs_from": "EPSG:6318+NOAA:65", "crs_to": "EPSG:6319", "v_shift": True},
         {"crs_from": "EPSG:6319", "crs_to": "EPSG:6318+NOAA:74", "v_shift": True},
         {"crs_from": "EPSG:6318", "crs_to": "EPSG:6344", "v_shift": False}
         ]


xyz = XYZ(input_file=input_file,
        #   skiprows=15,
        #   col_names=["xccc", "y", "z"]
          )
df = xyz.transform(crs_from=crs_from, crs_to=crs_to,
                   steps=steps
                   )
print(df.head())


