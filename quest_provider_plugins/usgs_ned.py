"""
Example Services
"""

from quest.plugins import ProviderBase, SingleFileServiceBase
from quest import util
from ulmo.usgs import ned
import os

DEFAULT_FILE_PATH = os.path.join('usgs','ned')
CACHE_FILE = 'ned_%s_metadata.json'


class UsgsNedServiceBase(SingleFileServiceBase):
    service_type = 'geo-discrete'
    unmapped_parameters_available = False
    geom_type = 'polygon'
    datatype = 'raster'
    geographical_areas = ['Alaska', 'USA', 'Hawaii']
    bounding_boxes = [[-180, -90, 180, 90]]
    smtk_template = None
    _parameter_map = {
        'elevation': 'elevation'
    }

    def get_features(self, **kwargs):
        service = self._description
        features = util.to_geodataframe(
            ned.get_raster_availability(service, (-180, -90, 180, 90))
        )
        if features.empty:
            return features

        features['parameters'] = 'elevation'
        features['filename'] = features['download url'].apply(lambda x: x.split('/')[-1])
        features['reserved'] = features.apply(
            lambda x: {'download_url': x['download url'],
                       'filename': x['filename'],
                       'file_format': 'raster-gdal',
                       'extract_from_zip': '.img',
                       }, axis=1)

        features.drop(labels=['filename', 'download url', 'format'], axis=1, inplace=True)

        return features.rename(columns={'name': 'display_name'})


class UsgsNedServiceAlaska(UsgsNedServiceBase):
    service_name = 'alaska-2-arc-second'
    _description = 'Alaska 2 arc-second'
    display_name = 'USGS National Elevation Dataset {}'.format(_description)
    description = 'Retrieve USGS NED at {} resolution'.format(_description)


class UsgsNedService1ArcSec(UsgsNedServiceBase):
    service_name = '1-arc-second'
    _description = '1 arc-second'
    display_name = 'USGS National Elevation Dataset {}'.format(_description)
    description = 'Retrieve USGS NED at {} resolution'.format(_description)


class UsgsNedService13ArcSec(UsgsNedServiceBase):
    service_name = '13-arc-second'
    _description = '1/3 arc-second'
    display_name = 'USGS National Elevation Dataset {}'.format(_description)
    description = 'Retrieve USGS NED at {} resolution'.format(_description)


class UsgsNedService19ArcSec(UsgsNedServiceBase):
    service_name = '19-arc-second'
    _description = '1/9 arc-second'
    display_name = 'USGS National Elevation Dataset {}'.format(_description)
    description = 'Retrieve USGS NED at {} resolution'.format(_description)


class UsgsNedProvider(ProviderBase):
    service_list = [UsgsNedServiceAlaska, UsgsNedService1ArcSec, UsgsNedService13ArcSec, UsgsNedService19ArcSec]
    display_name = 'USGS National Elevation Dataset'
    description = 'National Elevation Dataset at several resolutions'
    organization_name = 'United States Geological Survey'
    organization_abbr = 'USGS'
    name = 'usgs-ned'