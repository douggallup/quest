import appdirs
from geojson import LineString, Point, Polygon, Feature, FeatureCollection
import itertools
from .config import get_settings
import os
import pandas as pd
from stevedore import extension, driver
try:
    import simplejson as json
except ImportError:
    import json

from uuid import uuid4, UUID


def append_features(old, new):
    if not old:
        return new

    existing_features = [feature['id'] for feature in old['features']]
    for feature in new['features']:
        if feature['id'] not in existing_features:
            old['features'].append(feature)

    return old


def bbox2poly(x1, y1, x2, y2, reverse_order=False):
    if reverse_order:
        x1, y1 = y1, x1
        x2, y2 = y2, x2

    xmin, xmax = sorted([float(x1), float(x2)])
    ymin, ymax = sorted([float(y1), float(y2)])
    poly = [(xmin, ymin), (xmin, ymax), (xmax, ymax), (xmax, ymin)]
    poly.append(poly[0])

    return poly


def get_cache_dir(service=None):
    settings = get_settings()
    path = _abs_path(settings['CACHE_DIR'])
    if service is not None:
        path = os.path.join(path, service)

    return path


def get_dsl_dir():
    settings = get_settings()
    return settings['BASE_DIR']


def get_projects_dir():
    settings = get_settings()
    return _abs_path(settings['PROJECTS_DIR'])


def mkdir_if_doesnt_exist(dir_path):
    """makes a directory if it doesn't exist"""
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def get_projects_dir():
    settings = get_settings()
    return _abs_path(settings['PROJECTS_DIR'], mkdir=False)


def parse_uri(uri):
    """parse uri and return dictionary.

    if uri starts with svc then parse as a service
    otherwise it is a collection name
    if uri is a uuid then it is either a feature or a dataset

    service uri definition
        <service://<provider[:service]>/<feature or query]>
        <collection>/

    args:
        uri (string): uri string to parse

    return:
        parsed_uri (tuple): resource,

    examples:
        svc://usgs-nwis:iv/0803200
        service://gebco-bathymetry

        project://myproj:mycol/93d2e03543224096b14ce2eacd2eb275/temperature/472e7a7dd177405192fcb47a0c959c9d
        project://myproj:mycol/52b588510ce948b2a2515da02024c53e/temperature/

        service://<name>:<datalayer>/<feature>
        project://<name>:<collection>/<feature>/<dataset>
        feature://<collection>/<feature>/<dataset>
    """

    if uri.startswith('svc://'):
        resource, name, feature = uri.split('://')[-1].split('/')

    uri_dict = {}
    uri_dict['resource'], remainder = uri.split('://')
    parts = remainder.split('/')

    if uri_dict['resource'] not in ['collection', 'service']:
        raise ValueError('Unknown resource type in uri: %s' % uri_dict['resource'])

    if uri_dict['resource'] == 'service':
        keys = ['name', 'feature']

    if uri_dict['resource'] == 'collection':
        keys = ['name', 'feature', 'dataset']

    uri_dict.update({k: parts[i].strip() if i < len(parts) else None for i, k in enumerate(keys)})
    return uri_dict


def parse_service_uri(uri):
    """parse service uri into provider, service, feature.

    Examples:
        usgs-nwis:dv/0800345522
        gebco-bathymetry
        usgs-ned:1-arc-second

    args:
            uri (string): service uri_dict

        returns:
            parsed_uri (tuple): tuple containing provider, service, feature
    """
    svc, feature = (uri.split('://')[-1].split('/') + [None])[:2]
    provider, service = (svc.split(':') + [None])[:2]

    return provider, service, feature


def listify(liststr, delimiter=','):
    """If input is a string, split on comma and convert to python list
    """
    if liststr is None:
        return None

    return isinstance(liststr, list) and liststr or [s.strip() for s in liststr.split(delimiter)]


def list_drivers(namespace):
    namespace = 'dsl.' + namespace
    mgr = extension.ExtensionManager(
            namespace=namespace,
            invoke_on_load=False,
        )
    return [x.name for x in mgr]


def load_drivers(namespace, names=None):
    names = listify(names)
    namespace = 'dsl.' + namespace

    if names is None:
        mgr = extension.ExtensionManager(
            namespace=namespace,
            invoke_on_load=True,
        )
        return dict((x.name, x.obj) for x in mgr)

    return {name: driver.DriverManager(namespace, name, invoke_kwds={'uid': name}, invoke_on_load='True') for name in names}


def load_service(uri):
    if not isinstance(uri, dict):
        uri = parse_uri(uri)
    return load_drivers('services', names=uri['name'])[uri['name']].driver


def remove_key(d, key):
    r = dict(d)
    del r[key]
    return r


def jsonify(f):
    def wrapped_f(*args, **kw):
        if 'json' in list(kw.keys()):
            kw = json.loads(kw['json'])

        as_json = kw.get('as_json')
        if as_json:
            del kw['as_json']
            return json.dumps(f(*args, **kw), sort_keys=True, indent=4, separators=(',', ': '))
        else:
            return f(*args, **kw)
    return wrapped_f  # the wrapped function gets returned.


def stringify(args):
    return isinstance(args, list) and ','.join(args) or None


def to_dataframe(feature_collection):
    features = {}
    for feature in feature_collection['features']:
        data = feature['properties']
        coords = pd.np.array(feature['geometry']['coordinates']).mean(axis=1)
        data.update({
            'geom_type': feature['geometry']['type'],
            'geom_coords': feature['geometry']['coordinates'],
            'longitude': coords.flatten()[0],
            'latitude': coords.flatten()[1],
        })

        features[feature['id']] = data
    return pd.DataFrame.from_dict(features, orient='index')


def to_geojson(df):
    _func = {
        'LineString': LineString,
        'Point': Point,
        'Polygon': Polygon,
    }
    features = []
    for idx, row in df.iterrows():
        geometry = None
        if row['geom_type'] is not None:
            geometry = _func[row['geom_type']](row['geom_coords'])
        del row['geom_type']
        del row['geom_coords']
        properties = json.loads(row.dropna().to_json())
        features.append(Feature(geometry=geometry, properties=properties, id=idx))

    return FeatureCollection(features)


def uuid(resource_type):
    """Generate new uuid.

    First character of uuid is replaced with 'f' or 'd' respectively
    for resource_type feature, dataset respectovely

    args:
        resource_type (string): type of resource i.e. 'feature' or 'dataset'

    returns:
        uuid (string)
    """
    uuid = uuid4().hex

    if resource_type=='feature':
        uuid = 'f' + uuid[1:]

    if resource_type=='dataset':
        uuid = 'd' + uuid[1:]

    return uuid


def is_uuid(uuid):
    """Check if string is a uuid4

    Validate that a UUID string is in fact a valid uuid4.
    source: https://gist.github.com/ShawnMilo/7777304
    """

    try:
        val = UUID(uuid, version=4)
    except ValueError:
        # If it's a value error, then the string is not a valid UUID.
        return False

    # If the uuid_string is a valid hex code, but an invalid uuid4,
    # the UUID.__init__ will convert it to a valid uuid4.
    # This is bad for validation purposes.
    return val.hex == uuid


def _abs_path(path, mkdir=True):
    if not os.path.isabs(path):
        path = os.path.join(get_dsl_dir(), path)

    if mkdir:
        mkdir_if_doesnt_exist(path)

    return path
