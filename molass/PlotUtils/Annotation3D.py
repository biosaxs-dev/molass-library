"""
    Annotation3D.py

    Collected 2023-2025, Molass Cmmunity 
"""
from mpl_toolkits.mplot3d.proj3d import proj_transform
from mpl_toolkits.mplot3d.axes3d import Axes3D
from matplotlib.text import Annotation

"""
    c.f.
        https://gist.github.com/WetHat/1d6cd0f7309535311a539b42cccca89c
        https://stackoverflow.com/questions/10374930/matplotlib-annotating-a-3d-scatter-plot
"""
class Annotation3D(Annotation):

    def __init__(self, text, xyz, *args, **kwargs):
        super().__init__(text, xy=(0, 0), *args, **kwargs)
        self._xyz = xyz

    def draw(self, renderer):
        x2, y2, z2 = proj_transform(*self._xyz, self.axes.M)
        self.xy = (x2, y2)
        super().draw(renderer)

def _annotate3D(ax, text, xyz, *args, **kwargs):
    '''Add anotation `text` to an `Axes3d` instance.'''

    annotation = Annotation3D(text, xyz, *args, **kwargs)
    ax.add_artist(annotation)

def add_annotate3D():
    """
    Add annotate3D method to Axes3D class.
    """
    setattr(Axes3D, 'annotate3D', _annotate3D)

"""
    c.f.
        https://stackoverflow.com/questions/44465242/getting-the-legend-label-for-a-line-in-matplotlib
"""
def get_labeltext_from_line(line):
    leg = line.axes.get_legend()
    for h, t in zip(leg.legendHandles, leg.texts):
        if h.get_label() == line.get_label():
            return t    # changed from t.get_text() the above reference code