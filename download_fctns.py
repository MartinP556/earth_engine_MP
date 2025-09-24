import ee
import pandas as pd
import numpy as np
from masks import csPlus_mask_collection, mask_other
import geetools
import eemont
import geemap
from ee_extra.TimeSeries.core import getTimeSeriesByRegion

def count_reducer(img):
    return img.reduceResolution(ee.Reducer.count(), #ee.Reducer.percentile([90]),#ee.Reducer.median(),#ee.Reducer.count(),
                                maxPixels=1200, bestEffort=True)

class timeseries_downloader:
    def __init__(self, coords):
        self.coords = coords
        
    def initiate_image_collection(self, instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], 
                                  start_date = '2000-01-01', end_date = '2022-12-31', 
                                  QC_function = csPlus_mask_collection, pixel_scale = 500,
                                 get_NDVI = True, indices = False):
        self.bands = bands
        self.get_NDVI = get_NDVI
        self.instrument = instrument
        self.dataset = ee.ImageCollection(instrument).filterDate(start_date, end_date)
        self.dataset = QC_function(self.dataset)
        if indices:
            self.dataset = self.dataset.spectralIndices(['EVI','NDVI', 'SAVI', 'NDWI', 'CIG'])
        if self.instrument == "MODIS/061/MOD09GQ":
            self.dataset = self.dataset.map(addNDVI)
        self.dataset = self.dataset.select(*bands)
        #.map(lambda img: addNDVI(img, bands = ['B4', 'B8']))
        #self.dataset = self.dataset.spectralIndices(['EVI','NDVI']))#.map(addNDVI)
        self.pixel_scale = pixel_scale
        self.start_year = int(start_date[:4])
        self.end_year = int(end_date[:4])
        
    def read_at_coords(self, buffer_size = 1500, loc_type = 'box', count_threshold = 700, mask_scale = 250, crop_type = 'M', mask_to_use = 'worldCereal', N=1):
        first = True
        country_codes = {'DE': 93,
                         'KEN': 133}
        product_codes = {'M': 'product == "maize"',
                         'ww': 'product == "wintercereals"'}
        for coord_index, coord in enumerate(self.coords):
            print(coord_index)
            f1 = ee.Feature(ee.Geometry.Point([coord[1],coord[0]]).buffer(buffer_size),{'ID':'A'})
            f1c = ee.FeatureCollection([f1])
            filtered_dataset = self.dataset.filterBounds(f1c)
            if loc_type == 'box':
                location = box_around_point(coord, box_width)
            elif loc_type == 'point' or loc_type == 'random_points':
                if mask_to_use == 'worldCereal':
                    world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100').map(mask_other)
                    crop = world_cereals.filter(product_codes[crop_type]).mosaic().select('classification')#.gte(0))
                    crop = crop.setDefaultProjection(world_cereals.first().select('classification').projection(), scale = 10)
                    if count_threshold > 0:
                        crop = count_reducer(crop).gt(count_threshold)
                    else:
                        crop = crop.gt(count_threshold)
                    region = mask_other(crop.clip(f1))#.geometry())#.geometry()
                    filtered_dataset = filtered_dataset.map(lambda img: img.updateMask(region))
                elif mask_to_use == 'Thuenen':
                    thuenen_mask = ee.Image(f'projects/ee-martinparker637/assets/CTM_GER_{self.start_year}_rst_v202_COG')
                    if crop_type == 'M':
                        thuenen_mask = thuenen_mask.select('b1').eq(1300)
                    elif crop_type == 'ww':
                        thuenen_mask = thuenen_mask.select('b1').eq(92)
                    scale = thuenen_mask.select('b1').projection().nominalScale().getInfo()
                    thuenen_mask = thuenen_mask.setDefaultProjection(thuenen_mask.projection(), scale = scale)
                    crop = thuenen_mask.updateMask(thuenen_mask)
                    if count_threshold > 0:
                        crop = count_reducer(crop).gt(count_threshold)
                    else:
                        crop = crop.gt(count_threshold)
                    region = mask_other(crop.clip(f1))
                    filtered_dataset = filtered_dataset.map(lambda img: img.updateMask(region))
                if loc_type == 'point':
                    location = ee.Geometry.Point([coord[1],coord[0]]).buffer(buffer_size)
                elif loc_type == 'random_points':
                    location = random_crop_points(coord[1], coord[0], buffer_size = buffer_size, crop=region, N=N)
                #filtered_dataset = reduce_region_collection(filtered_dataset, location, reducer_code = 'median', pixel_scale = self.pixel_scale)
            elif loc_type == 'pixel':
                location = ee.Geometry.Point(coord[1], coord[0])
            elif loc_type == 'radius':
                location = ee.Geometry.Point(coord[1], coord[0]).buffer(buffer_size)
            if self.get_NDVI:
                ts = getTimeSeriesByRegion(filtered_dataset,
                                           reducer = [ee.Reducer.mean()],#,ee.Reducer.median(), ee.Reducer.max()
                                           geometry = location,
                                           bands = self.bands, #['B4','B8'],
                                           scale = mask_scale)
                try:
                    df = geemap.ee_to_df(ts)
                except:
                    continue
                df['lat'] = coord[0]
                df['lon'] = coord[1]
                if isinstance(coord[2], str):
                    df['Stations_Id'] = coord[2]
                else:
                    df['Stations_Id'] = np.int64(coord[2])
                #df = collection_properties_to_frame(filtered_dataset, coord, self.bands + ['ndvi'], reducer_code = 'median')
            else:
                df = collection_properties_to_frame(filtered_dataset, coord, self.bands, reducer_code = 'median')
            if first == True:
                self.df_full = df
                first = False
            else:
                self.df_full = pd.concat([self.df_full, df])

def box_around_point(coord, box_width):
    '''
    coord: coordinate in (lat, lon) (?)
    '''
    return ee.Geometry.BBox(coord[1] - box_width, coord[0] - box_width, coord[1] + box_width, coord[0] + box_width)

def random_crop_points(lon, lat, buffer_size = 1500, N = 1, worldcereal = True, crop = None):
    if worldcereal:
        world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100')
        # Get a global mosaic for all agro-ecological zone (AEZ) of winter wheat
        crop = world_cereals.filter('product == "maize"').mosaic().select('classification').gt(0)
        crop = crop.updateMask(crop)
    grid_cell = ee.Geometry.Point(lon, lat).buffer(buffer_size).bounds()
    region = crop.clip(grid_cell).geometry()
    vectors = crop.reduceToVectors(**{
        'geometry': region,
        'scale': 10,
        'maxPixels': 1e13,
        'bestEffort':True,
        'eightConnected': False,
        }).map(lambda x: x.buffer(-20))
    random_points = ee.FeatureCollection.randomPoints(**{'region': vectors, 'points': N, 'seed': 42, 'maxError': 1})
    return random_points

def get_mean(image, location, pixel_scale= 500):
    return image.set('mean', image.reduceRegion(ee.Reducer.mean(), location , pixel_scale))

def get_median(image, location, pixel_scale= 500):
    return image.set('median', image.reduceRegion(ee.Reducer.median(), location , pixel_scale))

def reduce_region_collection(image_collection, location, reducer_code = 'median', pixel_scale = 500):
    if reducer_code == 'mean':
        return image_collection.map(lambda img: get_mean(img, location, pixel_scale = pixel_scale))
    elif reducer_code == 'median':
        return image_collection.map(lambda img: get_median(img, location, pixel_scale = pixel_scale))
    else:
        print('invalid reducer code')

def collection_properties_to_frame(image_collection, coord, bands, reducer_code = 'median'):
    timelist = image_collection.aggregate_array('system:time_start').getInfo()
    bandlist = image_collection.aggregate_array('median').getInfo()
    data = {'Time': timelist,
            'lat': [coord[0] for count in range(len(timelist))],
            'lon': [coord[1] for count in range(len(timelist))],
            'Stations_Id': [np.int64(coord[2]) for count in range(len(timelist))]
           }
    for band in bands:
        data[f'{reducer_code} {band}'] = [band_data[band] for band_data in bandlist]
    df = pd.DataFrame(data)
    df['formatted_time'] = pd.to_datetime(df['Time'], unit='ms').dt.strftime('%Y-%m-%d-%H-%M-%S')
    return df

def addNDVI(image, bands = ['sur_refl_b02', 'sur_refl_b01']):
    ndvi = image.normalizedDifference(bands).rename('NDVI')
    return image.addBands([ndvi])

def satellite_data_at_coords(coords, start_date = '2000-01-01', end_date = '2022-12-31', instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], box_width = 0.002, pixel_scale = 500, QC_function = csPlus_mask_collection):
    dataset = ee.ImageCollection(instrument).filterDate(start_date, end_date)
    dataset = QC_function(dataset)
    for coord_index, coord in enumerate(coords):
        print(coord_index)
        location = box_around_point(coord, box_width)
        filtered_dataset = dataset.filterBounds(location)
        filtered_dataset = filtered_dataset.select(*bands).map(lambda img: img.set('median', img.reduceRegion(ee.Reducer.median(), location , pixel_scale)))
        timelist = filtered_dataset.aggregate_array('system:time_start').getInfo()
        bandlist = filtered_dataset.aggregate_array('median').getInfo()
        dataset = {'Time': timelist,
                   'lat': [coord[0] for count in range(len(timelist))],
                   'lon': [coord[1] for count in range(len(timelist))],
                   'Stations_Id': [np.int64(coord[2]) for count in range(len(timelist))]
                   }
        for band in bands:
            dataset[f'Median {band}'] = [band_data[band] for band_data in bandlist]
        df = pd.DataFrame(dataset)
        df['formatted_time'] = pd.to_datetime(df['Time'], unit='ms').dt.strftime('%Y-%m-%d-%H-%M-%S')
        if coord_index == 0:
            df_full = df
        else:
            df_full = pd.concat([df_full, df])
    return df_full