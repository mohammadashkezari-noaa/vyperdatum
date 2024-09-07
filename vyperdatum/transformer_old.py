import os
import pathlib
import logging
from typing import Union, Optional
import pyproj as pp
from pyproj.transformer import TransformerGroup
from pyproj._transformer import AreaOfInterest
import numpy as np
from osgeo import gdal, osr, ogr
from tqdm import tqdm
from vyperdatum.utils import raster_utils, crs_utils
from vyperdatum.utils.raster_utils import raster_metadata
from vyperdatum.pipeline import Pipeline


logger = logging.getLogger("root_logger")
gdal.UseExceptions()


class Transformer():
    """
    """
    def __init__(self,
                 crs_from: Union[pp.CRS, int, str],
                 crs_to: Union[pp.CRS, int, str],
                 always_xy: bool = False,
                 area_of_interest: Optional[AreaOfInterest] = None,
                 authority: Optional[str] = None,
                 accuracy: Optional[float] = None,
                 allow_ballpark: Optional[bool] = False,
                 force_over: bool = False,
                 only_best: Optional[bool] = True
                 ) -> None:
        """
        .. Some of the parameter descriptions adopted from pyproj :class:`Transformer`

        Parameters
        ----------
        crs_from: pyproj.crs.CRS or input used to create one
            Projection of input data.
        crs_to: pyproj.crs.CRS or input used to create one
            Projection of output data.
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

        if not isinstance(crs_from, pp.CRS):
            crs_from = pp.CRS(crs_from)
        if not isinstance(crs_to, pp.CRS):
            crs_to = pp.CRS(crs_to)
        self.crs_from = crs_from
        self.crs_to = crs_to
        self.transformer_group = TransformerGroup(crs_from=self.crs_from,
                                                  crs_to=self.crs_to,
                                                  allow_ballpark=allow_ballpark
                                                  )
        if len(self.transformer_group.transformers) > 0:
            print(f"Found {len(self.transformer_group.transformers)} transformer(s) for"
                  f"\n\tcrs_from: {self.crs_from.name}\n\tcrs_to: {self.crs_to.name}")
        else:
            err_msg = ("No transformers identified for the following transformation:"
                       f"\n\tcrs_from: {self.crs_from.name}\n\tcrs_to: {self.crs_to.name}")
            logger.exception(err_msg)
            raise NotImplementedError(err_msg)
        self.transformer = pp.Transformer.from_crs(crs_from=self.crs_from,
                                                   crs_to=self.crs_to,
                                                   always_xy=always_xy,
                                                   area_of_interest=area_of_interest,
                                                   authority=authority,
                                                   accuracy=accuracy,
                                                   allow_ballpark=allow_ballpark,
                                                   force_over=force_over,
                                                   only_best=only_best
                                                   )
        if not self.transformer.has_inverse:
            logger.warning("No inverse transformer has defined!")

    def transform_points(self,
                         x: Union[float, int, list, np.ndarray],
                         y: Union[float, int, list, np.ndarray],
                         z: Union[float, int, list, np.ndarray],
                         ):
        """
        Conduct point transformation between two coordinate reference systems.        

        Parameters
        ----------
        x: numeric scalar or array
           Input x coordinate(s).
        y: numeric scalar or array
           Input y coordinate(s).
        z: numeric scalar or array, optional
           Input z coordinate(s).
        """

        try:
            xt, yt, zt = None, None, None
            xt, yt, zt = self.transformer.transform(x, y, z)
        except Exception:
            logger.exception("Error while running the point transformation.")
        return xt, yt, zt

    @staticmethod
    def gdal_extensions() -> list[str]:
        """
        Return a lower-cased list of driver names supported by gdal.

        Returns
        -------
        list[str]
        """
        return sorted(
            ["." + gdal.GetDriver(i).ShortName.lower() for i in range(gdal.GetDriverCount())]
            + [".tif", ".tiff"]
            )

    def transform_raster(self,
                         input_file: str,
                         output_file: str,
                         apply_vertical: bool,
                         overview: bool = False,
                         warp_kwargs: Optional[dict] = None,
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
        NotImplementedError:
            If the input vector file is not supported by gdal.

        Parameters
        -----------
        input_file: str
            Path to the input raster file (gdal supported).
        output_file: str
            Path to the transformed raster file.
        apply_vertical: bool
            Apply GDAL vertical shift.
        overview: bool, default=True
            If True, overview bands are added to the output raster file (only GTiff support).

        Returns
        --------
        bool:
            True if successful, otherwise False.
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
            input_metadata = raster_utils.raster_metadata(input_file)
            raster_utils.pre_transformation_checks(source_meta=input_metadata)
            raster_utils.warp(input_file=input_file,
                              output_file=output_file,
                              apply_vertical=apply_vertical,
                              crs_from=self.crs_from,
                              crs_to=self.crs_to,
                              input_metadata=input_metadata,
                              warp_kwargs=warp_kwargs
                              )
            output_metadata = raster_utils.raster_metadata(output_file)
            raster_utils.post_transformation_checks(source_meta=input_metadata,
                                                    target_meta=output_metadata,
                                                    target_crs=self.crs_to,
                                                    vertical_transform=apply_vertical
                                                    )
            # if apply_vertical and isinstance(warp_kwargs.get("srcBands"), list):
            #     raster_utils.unchanged_to_nodata(src_raster_file=input_file,
            #                                      xform_raster_file=output_file,
            #                                      xform_band=warp_kwargs.get("srcBands")[0])

            if overview and input_metadata["driver"].lower() == "gtiff":
                raster_utils.add_overview(raster_file=output_file,
                                          compression=input_metadata["compression"]
                                          )
                # raster_utils.add_rat(output_file)
            success = True
        finally:
            return success

    def transform_vector(self,
                         input_file: str,
                         output_file: str
                         ) -> bool:
        """
        Transform the gdal-supported input vector file (`input_file`) and store the
        transformed file on the local disk (`output_file`).

        Raises
        -------
        ValueError:
            If `.crs_input` or `.crs_output` is not set.
        FileNotFoundError:
            If the input vector file is not found.
        NotImplementedError:
            If the input vector file is not supported by gdal.

        Parameters
        -----------
        input_file: str
            Path to the input vector file (gdal supported).
        output_file: str
            Path to the transformed vector file.

        Returns
        --------
        bool:
            True if successful, otherwise False.
        """
        try:
            if not (isinstance(self.crs_from, pp.CRS) & isinstance(self.crs_to, pp.CRS)):
                raise ValueError("The `.crs_input` and `.crs_output` attributes"
                                 "must be set with `pyproj.CRS` type values."
                                 )
            if not os.path.isfile(input_file):
                raise FileNotFoundError(f"The input vector file not found at {input_file}.")

            if pathlib.Path(input_file).suffix.lower() not in self.gdal_extensions():
                raise NotImplementedError(f"{pathlib.Path(input_file).suffix} is not supported")

            pbar, success = None, False
            ds = gdal.OpenEx(input_file)
            driver = ogr.GetDriverByName(ds.GetDriver().ShortName)
            inSpatialRef = osr.SpatialReference()
            inSpatialRef.ImportFromWkt(self.crs_from.to_wkt())
            outSpatialRef = osr.SpatialReference()
            outSpatialRef.ImportFromWkt(self.crs_to.to_wkt())
            coordTrans = osr.CoordinateTransformation(inSpatialRef, outSpatialRef)
            inDataSet = driver.Open(input_file)
            if os.path.exists(output_file):
                driver.DeleteDataSource(output_file)
            outDataSet = driver.CreateDataSource(output_file)
            layer_count = inDataSet.GetLayerCount()
            for layer_index in range(layer_count):
                inLayer = inDataSet.GetLayer(layer_index)
                outLayer = outDataSet.CreateLayer(inLayer.GetName(), geom_type=ogr.wkbMultiPolygon)
                inLayerDefn = inLayer.GetLayerDefn()
                for i in range(0, inLayerDefn.GetFieldCount()):
                    fieldDefn = inLayerDefn.GetFieldDefn(i)
                    outLayer.CreateField(fieldDefn)
                outLayerDefn = outLayer.GetLayerDefn()
                inFeature = inLayer.GetNextFeature()
                feature_count = inLayer.GetFeatureCount()
                pbar = tqdm(total=feature_count)
                feature_counter = 0
                while inFeature:
                    geom = inFeature.GetGeometryRef()
                    geom.Transform(coordTrans)
                    outFeature = ogr.Feature(outLayerDefn)
                    outFeature.SetGeometry(geom)
                    for i in range(0, outLayerDefn.GetFieldCount()):
                        outFeature.SetField(outLayerDefn.GetFieldDefn(i).GetNameRef(), inFeature.GetField(i))
                    outLayer.CreateFeature(outFeature)
                    outFeature = None
                    inFeature = inLayer.GetNextFeature()
                    feature_counter += 1
                    pbar.update(1)
                    pbar.set_description(f"Processing Layer {layer_index+1} / {layer_count}")
            inDataSet, outDataSet, ds = None, None, None
            success = True
        finally:
            if pbar:
                pbar.close()
            return success
