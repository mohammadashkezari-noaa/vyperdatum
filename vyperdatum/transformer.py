import os
import pathlib
import logging
from typing import Union, Optional
import pyproj as pp
from pyproj._transformer import AreaOfInterest
import numpy as np
from osgeo import gdal


logger = logging.getLogger("root_logger")


class Transformer():
    """
    """
    def __init__(self,
                 crs_from: Union[pp.CRS, int, str],
                 crs_to: Union[pp.CRS, int, str]
                 ) -> None:
        """

        Parameters
        ----------
        crs_from: pyproj.crs.CRS or input used to create one
            Projection of input data.
        crs_to: pyproj.crs.CRS or input used to create one
            Projection of output data.
        """

        if not isinstance(crs_from, pp.CRS):
            crs_from = pp.CRS(crs_from)
        if not isinstance(crs_to, pp.CRS):
            crs_to = pp.CRS(crs_to)
        self.crs_from = crs_from
        self.crs_to = crs_to

    def transform_points(self,
                         x: Union[float, int, list, np.ndarray],
                         y: Union[float, int, list, np.ndarray],
                         z: Union[float, int, list, np.ndarray],
                         always_xy: bool = False,
                         area_of_interest: Optional[AreaOfInterest] = None,
                         authority: Optional[str] = None,
                         accuracy: Optional[float] = None,
                         allow_ballpark: Optional[bool] = False,
                         force_over: bool = False,
                         only_best: Optional[bool] = True                         
                         ):
        """
        Conduct point transformation between two coordinate reference systems.

        .. Some of the parameter descriptions adopted from pyproj :class:`Transformer`

        Parameters
        ----------
        x: numeric scalar or array
           Input x coordinate(s).
        y: numeric scalar or array
           Input y coordinate(s).
        z: numeric scalar or array, optional
           Input z coordinate(s).
        always_xy: bool, default=False
            If true, the transform method will accept as input and return as output
            coordinates using the traditional GIS order, that is longitude, latitude
            for geographic CRS and easting, northing for most projected CRS.
        area_of_interest: :class:`.AreaOfInterest`, optional
            The area of interest to help select the transformation.
        authority: str, optional
            When not specified, coordinate operations from any authority will be
            searched, with the restrictions set in the
            authority_to_authority_preference database table related to the
            authority of the source/target CRS themselves. If authority is set
            to “any”, then coordinate operations from any authority will be
            searched. If authority is a non-empty string different from "any",
            then coordinate operations will be searched only in that authority
            namespace (e.g. EPSG).
        accuracy: float, optional
            The minimum desired accuracy (in metres) of the candidate
            coordinate operations.
        allow_ballpark: bool, optional, default=False
            Set to False to disallow the use of Ballpark transformation
            in the candidate coordinate operations. Default is to allow.
        force_over: bool, default=False
            If True, it will to force the +over flag on the transformation.
            Requires PROJ 9+.
        only_best: bool, optional, default=True
            Can be set to True to cause PROJ to error out if the best
            transformation known to PROJ and usable by PROJ if all grids known and
            usable by PROJ were accessible, cannot be used. Best transformation should
            be understood as the transformation returned by
            :c:func:`proj_get_suggested_operation` if all known grids were
            accessible (either locally or through network).
            Note that the default value for this option can be also set with the
            :envvar:`PROJ_ONLY_BEST_DEFAULT` environment variable, or with the
            ``only_best_default`` setting of :ref:`proj-ini`.
            The only_best kwarg overrides the default value if set.
            Requires PROJ 9.2+.
        """

        try:
            xt, yt, zt = None, None, None
            transformer = pp.Transformer.from_crs(crs_from=self.crs_from,
                                                  crs_to=self.crs_to,
                                                  always_xy=always_xy,
                                                  area_of_interest=area_of_interest,
                                                  authority=authority,
                                                  accuracy=accuracy,
                                                  allow_ballpark=allow_ballpark,
                                                  force_over=force_over,
                                                  only_best=only_best
                                                  )
            xt, yt, zt = transformer.transform(x, y, z)
        except Exception:
            logger.exception("Error while running the point transformation.")
        return xt, yt, zt

    @staticmethod
    def gdal_extensions():
        return sorted(
            ["." + gdal.GetDriver(i).ShortName.lower() for i in range(gdal.GetDriverCount())]
            + [".tif", ".tiff"]
            )

    def transform_raster(self,
                         input_file: str,
                         output_file: str
                         ) -> bool:
        """
        Transform the gdal-supported input rater file (`input_file`) and store the
        transformed file on the local disk (`output_file`).

        Raises
        -------
        ValueError:
            If `.crs_input` or `.crs_output` is not set.
        FileNotFoundError:
            If the input raster file is not found.

        Parameters
        -----------
        input_file: str
            Path to the input raster file (gdal supported).
        output_file: str
            Path to the transformed raster file.

        Returns
        --------
        bool:
            True is successful, otherwise False.
        """
        if not (isinstance(self.crs_from, pp.CRS) & isinstance(self.crs_to, pp.CRS)):
            raise ValueError(("The `.crs_input` and `.crs_output` attributes"
                              "must be set with `pyproj.CRS` type values.")
                             )
        if not os.path.isfile(input_file):
            raise FileNotFoundError(f"The input raster file not found at {input_file}.")

        if pathlib.Path(input_file).suffix.lower() not in self.gdal_extensions():
            raise NotImplementedError(f"{pathlib.Path(input_file).suffix} is not supported")
        try:
            success = False
            gdal.Warp(output_file,
                      input_file,
                      dstSRS=self.crs_to,
                      srcSRS=self.crs_from,
                      creationOptions=["COMPRESS=DEFLATE", "TILED=YES"]
                      )
            success = True
        finally:
            return success
