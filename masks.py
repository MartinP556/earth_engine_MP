import ee

def mask_MODIS_clouds(image):
    """Masks clouds in a Sentinel-2 image using the stateQA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('state_1km')
    # Bits 0-1 are cloud, 2 cloud shadow, 8-9 cirrus
    cloud_bit_mask = 3 << 0
    #cloud_bit_mask2 = 1 << 1
    cloud_shadow_bit_mask = 1 << 2
    cirrus_bit_mask = 3 << 8
    #cirrus_bit_mask2 = 1 << 9
    mask = (
        qa.bitwiseAnd(cloud_bit_mask).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0)
             .And(qa.bitwiseAnd(cloud_shadow_bit_mask).eq(0)
                 )
            )
    )
    return image.updateMask(mask)

def MODIS_Mask_QC(image):
    """Masks clouds in a Sentinel-2 image using the stateQA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QC_500m')
    # Bits 0-1 are cloud, 2 cloud shadow, 8-9 cirrus
    b1_mask = 15 << 2
    b2_mask = 15 << 6
    b3_mask = 15 << 10
    b4_mask = 15 << 14
    mask = (
        qa.bitwiseAnd(b1_mask).eq(0)
        .And(qa.bitwiseAnd(b2_mask).eq(0)
             .And(qa.bitwiseAnd(b3_mask).eq(0)
                  .And(qa.bitwiseAnd(b4_mask).eq(0)
                      )
                 )
            )
    )
    return image.updateMask(mask)

def mask_s2_clouds(image):
    """Masks clouds in a Sentinel-2 image using the QA band.

    Args:
        image (ee.Image): A Sentinel-2 image.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image.
    """
    qa = image.select('QA60')

    # Bits 10 and 11 are clouds and cirrus, respectively.
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11

    # Both flags should be set to zero, indicating clear conditions.
    mask = (
        qa.bitwiseAnd(cloud_bit_mask)
        .eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )

    return image.updateMask(mask)

def mask_s2_clouds_collection(image_collection):
    """Masks clouds in a Sentinel-2 image collection using the SLC band.

    Args:
        image (ee.ImageCollection): A Sentinel-2 image collection.

    Returns:
        ee.Image: A cloud-masked Sentinel-2 image collection.
    """
    return image_collection.map(mask_s2_clouds)