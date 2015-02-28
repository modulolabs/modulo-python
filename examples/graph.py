#!/usr/local/bin/python

from PyQt4 import QtCore, QtGui
import sys, modulo


class Graph(QtGui.QWidget) :

    def __init__(self) :
        super(Graph, self).__init__()
        self._pixelsPerSample = 5
        self._data = [] 
        self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

    def addSample(self, value) :
        maxSamples = self.width()/self._pixelsPerSample
        self._data.append(value)
        self._data = self._data[-maxSamples:]
        self.update()

    def paintEvent(self, event) :
        painter = QtGui.QPainter(self)
        points = []

        prevPoint = None
        for i in range(len(self._data)) :
            x = self.width() - self._pixelsPerSample*(len(self._data)-i)
            y = self.height()/2 - 5*self._data[i]
            point = QtCore.QPointF(x, y)
            if (prevPoint) :
                points.append(prevPoint)
                points.append(point)
            prevPoint = point
        painter.drawLines(points)


class ColorPicker(QtGui.QWidget) :

    colorChanged = QtCore.pyqtSignal((float, float, float))

    def __init__(self) :
        super(ColorPicker, self).__init__()

        self._hueSlider = QtGui.QSlider()
        self._saturationSlider = QtGui.QSlider()
        self._valueSlider = QtGui.QSlider()

        layout = QtGui.QGridLayout(self)
        layout.addWidget(QtGui.QLabel("Hue"))
        layout.addWidget(self._hueSlider)

        layout.addWidget(QtGui.QLabel("Saturation"))
        layout.addWidget(self._saturationSlider)

        layout.addWidget(QtGui.QLabel("Value"))
        layout.addWidget(self._valueSlider)

        self._hueSlider.valueChanged.connect(self.sliderChanged)
        self._saturationSlider.valueChanged.connect(self.sliderChanged)
        self._valueSlider.valueChanged.connect(self.sliderChanged)

    def set_hsv(self, h, s, v) :
        self._hueSlider.setValue(h*100)
        self._saturationSlider.setValue(s*100)
        self._valueSlider.setValue(v*100)

    def sliderChanged(self) :
        self.colorChanged.emit(
            self._hueSlider.value() / 100.0,
             self._saturationSlider.value() / 100.0,
             self._valueSlider.value() / 100.0)

class Controller(object) :

    def __init__(self) :

        # Connect to Modulo
        self._port = modulo.Port()
        self._knob = modulo.Knob(self._port)
        self._display = modulo.Display(self._port)

        # Create the Widgets
        self._graph = Graph()
        self._colorPicker = ColorPicker()
        self._colorPicker.colorChanged.connect(self.onColorChanged)

        # Assemble the widgets
        self._widget = QtGui.QWidget()
        self._widget.setWindowTitle('Graph Demo')
        self._layout = QtGui.QHBoxLayout(self._widget)
        self._layout.addWidget(self._graph)
        self._layout.addWidget(self._colorPicker)
        self._widget.resize(1200, 600)
        self._widget.show()
        self._widget.raise_()

        # Create a timer to get the knob position periodically
        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.onTimeout)
        self._timer.start(50)

        # Set the initial color
        self._color = (.5, 1, 1)
        self._colorPicker.set_hsv(self._color[0], self._color[1], self._color[2])


    # When the timer fires, add a data point to the graph and update the display
    def onTimeout(self) :
        self._graph.addSample(self._knob.get_position())

        self._display.clear()
        self._display.set_cursor(0,0)
        self._display.write("Pos:")
        self._display.writeln(self._knob.get_position())
        self._display.write("Hue:")
        self._display.writeln(self._color[0])
        self._display.write("Sat:")
        self._display.writeln(self._color[1])
        self._display.write("Val:")
        self._display.writeln(self._color[2])

        self._display.update()

    # When the color changes, push it to the knob
    def onColorChanged(self, h, s, v) :
        self._color = (h, s, v)
        self._knob.set_hsv(h,s,v)


if __name__ == '__main__' :
    app = QtGui.QApplication(sys.argv)
    controller = Controller()
    app.exec_()

