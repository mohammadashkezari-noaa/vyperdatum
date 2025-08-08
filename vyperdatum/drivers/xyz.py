import numpy as np
from typing import Optional, List
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from vyperdatum.drivers.base import Driver


class XYZ(Driver):
    """
    Handle loading and parsing of a generic .xyz.

    Attributes
    ----------
    input_file: str
        Full path to the xyz file.
    invalid_error: bool = True
        If True, throws an error when the input file has an unexpected format.
    skiprows: Optional[int] = None
        The number of rows at the beginning of the file to ignore.
    col_names: Optional[List[str]] = None
        The names of the columns in the file. If None, defaults to ['x', 'y', 'z'].
    negate_z: bool = False
        If True, negates the z values in the file.
    unit_conversion: float = 1.0
        A factor to convert the z values to the desired unit.

    Pseudo Example
    --------
    >>> xyz = XYZZ('PATH_TO_NPZ_FILE')
    >>> df = xyz.transform(crs_from=crs_from, crs_to=crs_to, steps=steps)
    >>> print(df.head())
    >>> xyz.to_gpkg(crs=crs_to, output_file=output_file)
    """

    def __init__(self, input_file: str,
                 invalid_error: bool = True,
                 skiprows: Optional[int] = None,
                 col_names: Optional[List[str]] = None,
                 negate_z: bool = False,
                 unit_conversion: float = 1.0
                 ) -> None:
        """
        Load a numpy .xyz file (a csv file with generic comments at the top).

        Parameters
        ----------
        input_file: str
            Full file path.
        invalid_error: bool, default True
            If True, throws an error when the input file has an unexpected format.

        Raises
        --------
        ValueError:
            If the input file is not recognized as xyz file.

        Returns
        -----------
        None
        """
        super().__init__()
        self.input_file = input_file
        try:
            self.skiprows = self._detect_data_start() if skiprows is None else skiprows
            self.col_names = col_names
            self.negate_z = negate_z
            self.unit_conversion = unit_conversion
            self.df = self._parse()
            self.is_xyz = True
        except:
            self.is_xyz = False
        if invalid_error and not self.is_xyz:
            raise ValueError(f"Not a valid .xyz file: {self.input_file}.")

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

    def _parse(self) -> pd.DataFrame:
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
        if self.negate_z:
            df["z"] = -df["z"]
        df["z"] *= self.unit_conversion
        return df


    def wkt(self) -> str:
        """
        Return wkt stored in the xyz file.
        Will raise NotImplementedError as xyz files do not have a dedicated attribute for WKT.
        """
        raise NotImplementedError("xyz files have no dedicated attribute for WKT.")
        return None


    def transform(self, transformer_instance, output_file: str, vdatum_check: bool) -> bool:
        """
        Apply point transformation on npz data according to the `transformer_instance`.

        Parameters
        -----------
        transformer_instance: vyperdatum.transformer.Transform
            Instance of the transformer class.
        output_file: str
            The output file path where the transformed data will be saved.
        vdatum_check: bool
            If True, performs vertical datum checks after transformation.

        Returns
        -----------
        bool:
            True if successful, otherwise False.
        """
        x, y, z = self.df["x"].values, self.df["y"].values, self.df["z"].values
        success, xt, yt, zt = transformer_instance.transform_points(x, y, z,
                                                                    vdatum_check=vdatum_check)
        if not success:
            raise ValueError(f"XYZ transformation failed for {self.input_file}.")
        self.df["x_t"], self.df["y_t"], self.df["z_t"] = xt, yt, zt
        if self.negate_z:
            self.df["z"] = -self.df["z"]
            self.df["z_t"] = -self.df["z_t"]
        self.df["Uncertainty"] = 1 + 0.02 * self.df["z_t"].abs()

        self.to_gpkg(crs=transformer_instance.crs_to, output_file=output_file)
        return success

    def to_gpkg(self,
                crs: str,
                output_file: str) -> None:
        tdf = pd.DataFrame({"x": self.df["x_t"].values,
                            "y": self.df["y_t"].values,
                            "Elevation": self.df["z_t"].values,
                            })
        tdf["geometry"] = tdf.apply(lambda row: Point(row["x"], row["y"], row["Elevation"]), axis=1)
        tdf["Uncertainty"] = self.df["Uncertainty"].values
        gdf = gpd.GeoDataFrame(tdf, geometry="geometry", crs=crs)
        gdf.to_file(output_file, driver="GPKG")
        return
    
    @property
    def is_valid(self):
        return self.is_xyz
