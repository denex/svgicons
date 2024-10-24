"""
    TODO:
"""
import os
import sys
import subprocess
import logging
import shutil

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PIL import Image, ImageChops, ImageOps
from websocket_server import WebsocketServer
from jinja2 import FileSystemLoader, Environment
import begin

from svg2png import svg2png

SCRIPT_DIR = os.path.dirname(__file__)
WORK_DIR = os.path.join(SCRIPT_DIR, '..')

WWW_DIR = os.path.abspath(os.path.join(WORK_DIR, 'www'))
SVG_DIR = os.path.join(WWW_DIR, 'svg')
TMP_DIR = os.path.join(WWW_DIR, 'tmp')
TEMPLATE_DIR = os.path.join(WORK_DIR, 'templates')
HTML_FILE = os.path.join(WWW_DIR, 'index.html')
HTML_URL = "file://" + os.path.realpath(HTML_FILE).replace(os.path.sep, '/')

TEMPLATE_ENVIRONMENT = Environment(loader=FileSystemLoader(searchpath=TEMPLATE_DIR))
IGNORE_SVG = frozenset(["grid.svg"])

WS_SERVER_CONFIG = {
    'host': "localhost",
    'port': 8080
}

DIFF_FILENAME = os.path.join(TMP_DIR, 'diff.png')
GENERATED_FILENAME = os.path.join(TMP_DIR, 'generated.png')


def generate_png_from_svg(svg_filename, png_filename):
    try:
        svg2png(svg_filename, png_filename)
    except Exception as e:
        logging.exception(e)
        raise


def compute_difference(origin_png_filename, generated_png_filename):
    assert os.path.isfile(origin_png_filename)
    assert os.path.isfile(generated_png_filename)

    with Image.open(origin_png_filename) as origin, Image.open(generated_png_filename) as generated:
        logging.info(f"{origin.mode=} {generated.mode=}")
        # Convert to one mode (color space)
        origin = origin.convert(generated.mode)
        with ImageChops.difference(origin, generated) as diff:
            diff = diff.convert('RGB')
            new = ImageOps.invert(diff)
            new.save(DIFF_FILENAME, format='PNG')


WS_SERVER: WebsocketServer = None


def on_some_svg_file_changed(svg_filename):
    logging.info("Changed file %s", svg_filename)
    WS_SERVER.send_message_to_all("Refresh")


def on_observable_svg_changed(svg_filename, png_filename, reload_view=True):
    logging.info("SVG file %s changed", svg_filename)
    generate_png_from_svg(svg_filename, png_filename=GENERATED_FILENAME)
    compute_difference(origin_png_filename=png_filename, generated_png_filename=GENERATED_FILENAME)
    if reload_view:
        logging.info("Reloading page...")
        WS_SERVER.send_message_to_all("Refresh")


def render_file(template_name, template_kwargs, dst_filename):
    template = TEMPLATE_ENVIRONMENT.get_template(template_name)
    rendered_text = template.render(**template_kwargs)
    with open(dst_filename, 'w', encoding='utf-8') as out_f:
        out_f.write(rendered_text)


def render_templates(png_filename, open_svg):
    assert os.path.exists(png_filename)
    filename_wo_extension = os.path.splitext(png_filename)[0]
    base_name = os.path.basename(filename_wo_extension)
    svg_filename = os.path.join(SVG_DIR, base_name + '.svg')
    grid_filename = os.path.join(WWW_DIR, 'grid.svg')
    paths = {
        'origin_png_filename': os.path.relpath(os.path.join(TMP_DIR, 'origin.png'), WWW_DIR),
        'svg_filename': os.path.relpath(svg_filename, WWW_DIR),
        'grid_filename': os.path.relpath(grid_filename, WWW_DIR),
        'diff_filename': os.path.relpath(DIFF_FILENAME, WWW_DIR),
        'generated_png_filename': os.path.relpath(GENERATED_FILENAME, WWW_DIR),
    }
    icon = {}
    with Image.open(png_filename) as png_image:
        icon['height'] = png_image.height
        icon['width'] = png_image.width
    render_file('grid.template', {'icon': icon}, grid_filename)
    if not os.path.exists(svg_filename):
        render_file('svg.template', {'icon': icon}, svg_filename)
    if open_svg:
        args = ['open'] if sys.platform == 'darwin' else ['cmd.exe', '/c', 'start']
        args.append(svg_filename)
        subprocess.call(args)
    render_file('html.template', {'icon': icon,
                                  'server': WS_SERVER_CONFIG,
                                  'paths': paths},
                HTML_FILE)
    return svg_filename


class SVGModificationHandler(FileSystemEventHandler):
    def __init__(self, observable_filename: str, png_filename: str):
        assert os.path.isabs(observable_filename)
        self.observable_filename = observable_filename
        self.png_filename = png_filename

    def on_modified(self, event):
        if event.is_directory:
            return
        if not os.path.isfile(event.src_path):
            return
        if not event.src_path.endswith('.svg'):
            return
        if event.src_path == self.observable_filename:
            on_observable_svg_changed(event.src_path, self.png_filename)
        else:
            on_some_svg_file_changed(event.src_path)


@begin.start
def main(origin_png_filename, open_html=False, open_svg=False):
    global WS_SERVER
    logging.basicConfig(force=True, level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    assert os.path.isfile(origin_png_filename), origin_png_filename
    os.makedirs(TMP_DIR, exist_ok=True)
    dst_png_filename = os.path.join(TMP_DIR, 'origin.png')
    shutil.copyfile(origin_png_filename, dst_png_filename)

    svg_filename = render_templates(origin_png_filename, open_svg)
    on_observable_svg_changed(svg_filename, dst_png_filename, reload_view=False)

    print("Set change observer")
    event_handler = SVGModificationHandler(svg_filename, dst_png_filename)
    observer = Observer()
    observer.schedule(event_handler, WWW_DIR, recursive=True)
    observer.start()

    print("Start WebSocket server")
    WS_SERVER = WebsocketServer(**WS_SERVER_CONFIG)
    if open_html:
        args = ['open'] if sys.platform == 'darwin' else ['cmd.exe', '/c', 'start']
        args.append(HTML_URL)
        subprocess.check_call(args)
    WS_SERVER.run_forever()
    #
    observer.stop()
