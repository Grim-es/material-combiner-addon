def is_single_colour_generated(img):
    """:return:True if the img argument is a generated image of a single color that doesn't have any pending changes"""
    return not img.is_dirty and img.generated_type == 'BLANK'


def is_image_valid(img):
    """:return:True if the img argument is a valid image for packing into an atlas"""
    if img is not None:
        # TODO: Not sure if these images can get picked currently
        if img.filepath and img.filepath.lower().endswith(('.spa', '.sph')):
            return False
        else:
            return True
    else:
        return False


def save_generated_image_to_file(image, filepath, file_format=None):
    """Save a generated image to a filepath, this will set the filepath of the image and cause the
    image source to be changed to 'FILE' instead of 'GENERATED'"""
    # Note that setting image.filepath and/or image.source = 'FILE' can't be done, otherwise it will reset the image
    image.filepath_raw = filepath
    if file_format:
        image.file_format = file_format
    image.save()
