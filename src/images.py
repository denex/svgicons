import os

from PIL import Image, ImageChops, ImageOps


def compute_difference(origin_png_filename: str, generated_png_filename: str, diff_filename: str) -> None:
    assert os.path.isfile(origin_png_filename)
    assert os.path.isfile(generated_png_filename)
    with Image.open(origin_png_filename) as origin, Image.open(generated_png_filename) as generated:
        with ImageChops.difference(origin, generated) as diff:
            diff = diff.convert('RGB')
            new = ImageOps.invert(diff)
            new.save(diff_filename, format='PNG')


def get_image_height_and_width(image_filename: str) -> tuple:
    """
    :return: (height, width)
    """
    with Image.open(image_filename) as png_image:
        return png_image.height, png_image.width
