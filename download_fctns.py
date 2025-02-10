import ee
import pandas as pd
import numpy as np
from masks import mask_s2_clouds_collection

class timeseries_downloader:
    def __init__(self, coords):
        self.coords = coords
        
    def initiate_image_collection(self, instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], 
                                  start_date = '2000-01-01', end_date = '2022-12-31', 
                                  QC_function = mask_s2_clouds_collection, pixel_scale = 500,
                                 get_NDVI = True):
        self.bands = bands
        self.get_NDVI = get_NDVI
        self.instrument = instrument
        self.dataset = ee.ImageCollection(instrument).filterDate(start_date, end_date)
        self.dataset = QC_function(self.dataset)
        self.dataset = self.dataset.select(*bands)
        if get_NDVI:
            if self.instrument == "COPERNICUS/S2_SR_HARMONIZED":
                self.dataset = self.dataset.map(lambda img: addNDVI(img, bands = ['B4', 'B8']))
            elif self.instrument == "MODIS/061/MOD09GA":
                self.dataset = self.dataset.map(addNDVI)
        self.pixel_scale = pixel_scale
        
    def read_at_coords(self, box_width = 0.002, loc_type = 'box'):
        for coord_index, coord in enumerate(self.coords):
            print(coord_index)
            if loc_type == 'box':
                location = box_around_point(coord, box_width)
            elif loc_type == 'random_points':
                location = random_crop_points(coord[1], coord[0])
            filtered_dataset = filtered_dataset = self.dataset.filterBounds(location)
            
            filtered_dataset = reduce_region_collection(filtered_dataset, location, reducer_code = 'median', pixel_scale = self.pixel_scale)
            if self.get_NDVI:
                df = collection_properties_to_frame(filtered_dataset, coord, self.bands + ['ndvi'], reducer_code = 'median')
            else:
                df = collection_properties_to_frame(filtered_dataset, coord, self.bands, reducer_code = 'median')
            if coord_index == 0:
                self.df_full = df
            else:
                self.df_full = pd.concat([self.df_full, df])

def box_around_point(coord, box_width):
    '''
    coord: coordinate in (lat, lon) (?)
    '''
    return ee.Geometry.BBox(coord[1] - box_width, coord[0] - box_width, coord[1] + box_width, coord[0] + box_width)

def random_crop_points(lon, lat, buffer_size = 2000, N = 10):
    world_cereals = ee.ImageCollection('ESA/WorldCereal/2021/MODELS/v100')
    # Get a global mosaic for all agro-ecological zone (AEZ) of winter wheat
    crop = world_cereals.filter('product == "maize"').mosaic().select('classification').gte(0)
    grid_cell = ee.Geometry.Point(lon, lat).buffer(buffer_size).bounds()
    region = crop.clip(grid_cell).geometry()
    vectors = crop.reduceToVectors(**{
        'geometry': region,
        'scale': 100,
        'maxPixels': 1e13,
        'bestEffort':True,
        'eightConnected': False,
        })#.map(lambda x: x.buffer(-20))
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

def addNDVI(image, bands = ['sur_refl_b01', 'sur_refl_b02']):
    ndvi = image.normalizedDifference(bands).rename('ndvi')
    return image.addBands([ndvi])

def satellite_data_at_coords(coords, start_date = '2000-01-01', end_date = '2022-12-31', instrument = "COPERNICUS/S2_SR_HARMONIZED", bands = ['B4', 'B8'], box_width = 0.002, pixel_scale = 500, QC_function = mask_s2_clouds_collection):
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