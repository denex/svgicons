import cairosvg

assert cairosvg.svg2png


def svg2png(svg_filename, png_filename):
    cairosvg.svg2png(url=svg_filename, write_to=png_filename)
