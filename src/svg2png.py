import os
import sys

if sys.platform == 'win32':
    inkscape_path = os.path.join(os.environ['PROGRAMFILES'], "Inkscape")
    assert os.path.exists(inkscape_path), "Inkscape not found in %s" % inkscape_path
    os.environ['PATH'] = os.environ['PATH'] + ';%s' % inkscape_path

import cairosvg

assert cairosvg.svg2png


def svg2png(svg_filename, png_filename):
    with open(svg_filename, 'rb') as f_obj:
        cairosvg.svg2png(file_obj=f_obj, write_to=png_filename)
