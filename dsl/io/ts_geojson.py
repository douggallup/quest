"""I/O plugin for Geojson with timeseries


"""
from .base import IoBase
from geojson import Feature, Point, dump
import json
import pandas as pd


class TsGeojson(IoBase):
    """Base class for I/O for different file formats
    """

    def register(self):
        """Register plugin by setting description and io type 
        """
        self.description = 'Reader/Writer for Geojson with timeseries in properties field'
        self.iotype = 'timeseries' 

    def read(self, path, as_dataframe=False):
        """Read data from format
        """
        with open(path) as f:
            data = json.load(f)

        if as_dataframe:
            data['values'] = pd.Series(data=data['values'], index=data['time'])
            del data['time']

        return data

    def write(self, path, location, name, longitude, latitude, parameter, unit, statistic, df, metadata=None):
        """Write data to format
        """

        feature = Feature(id=location,
                        geometry=Point((float(longitude),
                                        float(latitude))),
                        properties={
                            'name': name,
                            'parameter': parameter,
                            'statistic': statistic,
                            'metadata': metadata,
                            'unit_of_measurement': unit,
                            'statistic': statistic,
                            'time': df.index.to_native_types(),
                            'values': df.values.tolist(),
                        },
                    )
        if not path.endswith('.json'):
            path += '.json'
        with open(path+'.json', 'w') as f:
            dump(feature, f)

        print 'file written to %s' % path
