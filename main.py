from datetime import datetime
from socket import gethostname
import json
from os.path import exists
from random import random
from math import pi
from functools import reduce

from oscpy.server import OSCThreadServer
from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.garden import magnet
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import RenderContext
from kivy.animation import Animation
from kivy.properties import (
    NumericProperty, StringProperty, ColorProperty, ListProperty
)

PORT = 9999
PEER_PORT = 9998

CONF = 'conf.json'

class Logo(magnet.Magnet):
    source = StringProperty()
    image_center = ListProperty((0, 0))
    _cache = {}

    @classmethod
    def get(cls, source, **kwargs):
        "get a cached logo, or create it"
        if source not in cls._cache:
            cls._cache[source] = cls(source=source, **kwargs)
        return cls._cache[source]


class ShaderWidget(FloatLayout):
    # property to set the source code for fragment shader
    fs = StringProperty(None)
    source = StringProperty()

    def __init__(self, **kwargs):
        # Instead of using Canvas, we will use a RenderContext,
        # and change the default shader used.
        self.canvas = RenderContext()

        # call the constructor of parent
        # if they are any graphics object, they will be added on our new canvas
        super(ShaderWidget, self).__init__(**kwargs)

        # We'll update our glsl variables in a clock
        Clock.schedule_interval(self.update_glsl, 1 / 60.)

    def on_source(self, instance, value):
        with open(self.source) as f:
            self.fs = f.read()

    def on_fs(self, instance, value):
        # set the fragment shader to our source code
        shader = self.canvas.shader
        old_value = shader.fs
        shader.fs = value
        if not shader.success:
            shader.fs = old_value
            raise Exception('failed')

    def update_glsl(self, *largs):
        self.canvas['time'] = Clock.get_boottime()
        self.canvas['resolution'] = list(map(float, self.size))
        # This is needed for the default vertex shader.
        win_rc = Window.render_context
        self.canvas['projection_mat'] = win_rc['projection_mat']
        self.canvas['modelview_mat'] = win_rc['modelview_mat']
        self.canvas['frag_modelview_mat'] = win_rc['frag_modelview_mat']


class Pres(App):
    page = NumericProperty()
    direction = StringProperty()
    clocktime = StringProperty()
    time = NumericProperty()

    colors = ListProperty([[random() for i in range(4)] for i in range(3)])
    origins = ListProperty([[random() * Window.width, random() * Window.height] for i in range(3)])
    angles = ListProperty([random() * 2 * pi for i in range(3)])

    paragraph_font_size = NumericProperty('40dp')
    title_font_size = NumericProperty('50dp')
    paragraph_color = ColorProperty('#FFFFFF')
    background_color = ColorProperty('#000000FF')
    title_color = ColorProperty('#FFFFFFFF')

    def on_start(self, *_):
        "wooo"
        Clock.schedule_interval(self.update_clocktime, .1)
        Window.bind(on_key_down=self.manage_key)
        if exists(CONF):
            with open(CONF) as f:
                conf = json.load(f)

            for k, v in conf.items():
                setattr(self, k, v)

        self.animate_bg()

    def on_stop(self, *_):
        conf = {
            'paragraph_font_size': self.paragraph_font_size,
            'title_font_size': self.title_font_size,
            'paragraph_color': self.paragraph_color,
            'background_color': self.background_color,
            'title_color': self.title_color,
        }

        with open(CONF, 'w') as f:
            json.dump(conf, f)

    def animate_bg(self, *args):
        a = Animation(
            colors=[[random() for i in range(4)] for i in range(3)],
            origins=[[random() * Window.width, random() * Window.height] for i in range(3)],
            angles=[random() * 2 * pi for i in range(3)],
            d=60,
            t='in_out_cubic')
        a.bind(on_complete=self.animate_bg)
        a.start(self)

    def manage_key(self, win, key, scancode, codepoint, modifier, **kwargs):
        "manage key events"
        print(key, scancode, codepoint, modifier)
        if key == 275:
            self.next()
        elif key == 276:
            self.previous()
        elif key == 274:
            self.down()
        elif key == 273:
            self.up()

    def down(self):
        "next sub slide"
        self.root.ids.sm.current_screen.index += 1

    def up(self):
        "previous sub slide"
        self.root.ids.sm.current_screen.index -= 1

    def update_clocktime(self, dt):
        "tic toc"
        self.clocktime = datetime.now().strftime('%H:%M:%S')
        self.time += dt

    def pages(self):
        "all the pages"
        return self.root.ids.sm.screen_names

    def next(self):
        "next slide"
        self.direction = 'left'
        self.root.ids.sm.current = self.root.ids.sm.next()

    def previous(self):
        "previous slide"
        self.direction = 'right'
        self.root.ids.sm.current = self.root.ids.sm.previous()


if __name__ == '__main__':
    APP = Pres()
    SERVER = OSCThreadServer(encoding='utf8')
    SERVER.listen(address='0.0.0.0', port=PORT, default=True)

    @SERVER.address(b'/probe')
    def _probe(*_):
        print("got probe")
        host = gethostname()
        SERVER.answer(b'/found', values=[host], port=9998)

    @SERVER.address(b'/next')
    @mainthread
    def _next(*_):
        print("got next")
        APP.next()

    @SERVER.address(b'/previous')
    @mainthread
    def _previous(*_):
        print("got previous")
        APP.previous()

    @SERVER.address(b'/up')
    @mainthread
    def _up(*_):
        print("got up")
        APP.up()

    @SERVER.address(b'/down')
    @mainthread
    def _down(*_):
        print("got down")
        APP.down()

    @SERVER.address(b'/color/text')
    @mainthread
    def _text_color(r, g, b, a):
        print(r, g, b, a)
        print("got down")
        APP.paragraph_color = r, g, b, 1

    @SERVER.address(b'/color/background')
    @mainthread
    def _background_color(r, g, b, a):
        print(r, g, b, a)
        print("got down")
        APP.background_color = r, g, b, 1

    @SERVER.address(b'/color/title')
    @mainthread
    def _title_color(r, g, b, a):
        print(r, g, b, a)
        APP.title_color = r, g, b, 1

    @SERVER.address(b'/size/title')
    @mainthread
    def _title_size(v):
        APP.title_font_size = v

    @SERVER.address(b'/size/text')
    @mainthread
    def _text_size(v):
        APP.paragraph_font_size = v

    @SERVER.address(b'/get_conf')
    def _send_conf():
        SERVER.answer(
            b'/conf',
            (
                APP.background_color[:3] +
                APP.paragraph_color[:3] +
                [APP.paragraph_font_size] +
                APP.title_color[:3] +
                [APP.title_font_size]
            ),
            port=PEER_PORT
        )

    APP.run()
