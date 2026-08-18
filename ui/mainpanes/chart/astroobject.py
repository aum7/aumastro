# ui/mainpanes/chart/astroobject.py
from user.settings import OBJECTS
from math import pi, radians, cos, sin


class AstroObject:
    def __init__(self, data):
        self.data = data
        # print(f"astrochart : objects : {data}")
        self.size = 0.7
        name = self.data.get("name", "su").lower()
        # default color & scale
        self.color = (0.1, 0.1, 0.1, 0.5)
        # leave below for proper event ring objects scaling
        self.scale = 1.0

        for obj in OBJECTS.values():
            if obj[0].lower() == name:
                self.color = obj[4]
                self.scale = obj[5]
                break

    def __repr__(self):
        # use this to access data with print(...)
        name = self.data.get("name", "/")
        lon = self.data.get("lon", "/")
        lat = self.data.get("lat", "/")
        return f"{name}-lon:{lon}-lat:{lat}"

    def draw(self, cr, cx, cy, radius, obj_scale=1.0, scale=None, color=None):
        # allow for custom color & scale
        draw_color = color if color is not None else self.color
        draw_scale = scale if scale is not None else self.scale
        # compute angle & draw in ccw direction, start at left (aries)
        angle = pi - radians(self.data.get("lon", 0))
        # determine radius by scale
        obj_size = self.size * draw_scale * obj_scale
        x = cx + radius * cos(angle)
        y = cy + radius * sin(angle)
        # simple ring marker for object / planet
        cr.arc(x, y, obj_size, 0, 2 * pi)
        cr.set_source_rgba(*draw_color)
        cr.fill()
