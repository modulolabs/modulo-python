#!/usr/local/bin/python
from PyQt4 import QtCore, QtGui
import modulo, time, sys, random, math

class TileWidget(QtGui.QFrame) :

    def __init__(self, port, deviceID) :
        super(TileWidget, self).__init__()

        self._productName = port._get_product(deviceID).replace(" Module","")

        self.setMinimumHeight(128)
        self.setMinimumWidth(256)
        self.setFrameStyle(QtGui.QFrame.Box);


    def updateUI(self) :
        pass

class ColorPickerWidget(QtGui.QWidget) :

    colorChanged = QtCore.pyqtSignal((QtGui.QColor))


    def __init__(self, horizontal=False) :
        super(ColorPickerWidget, self).__init__()
        self._horizontal = horizontal

        self._colors = [
            QtGui.QColor(80, 80 ,80),
            QtGui.QColor(255, 0, 0),
            QtGui.QColor(255, 255, 0),
            QtGui.QColor(0, 255, 0),
            QtGui.QColor(0, 255, 255),
            QtGui.QColor(0, 0, 255),
            QtGui.QColor(255, 0, 255)
            ]

        if horizontal :
           self.setSizePolicy(
                QtGui.QSizePolicy.Preferred,
                QtGui.QSizePolicy.Fixed)
        else :
            self.setSizePolicy(
                QtGui.QSizePolicy.Fixed,
                QtGui.QSizePolicy.Preferred)

 


        self._selectedColor = 0

    def sizeHint(self) :
        if (self._horizontal) :
            return QtCore.QSize(100, 20)
        else :
            return QtCore.QSize(20, 100)

 
    def paintEvent(self, e) :
        painter = QtGui.QPainter(self)

        numColors = len(self._colors)
        for i in range(numColors) :
            if (self._horizontal) :
                painter.fillRect(
                    i*self.width()//numColors, 0,
                    self.width()//numColors + 1, self.height(),
                    self._colors[i])
            else :
                painter.fillRect(
                    0, i*self.height()//numColors,
                    self.width(), self.height()//numColors + 1,
                    self._colors[i])


        if self._selectedColor is not None :
            painter.setPen(QtGui.QColor(255,255,255))
            if self._horizontal :
                painter.drawRect(
                    self._selectedColor*self.width()//numColors, 0,
                    self.width()//numColors-1, self.height()-1)
            else :
                painter.drawRect(
                    0, self._selectedColor*self.height()//numColors,
                    self.width()-1, self.height()//numColors-1)



    def mousePressEvent(self, e) :
        if self._horizontal :
            i = e.pos().x()*len(self._colors)/self.width()
        else :
            i = e.pos().y()*len(self._colors)/self.height()
        if (i >= 0 and i <= len(self._colors)) :
            self._selectedColor = i
            self.colorChanged.emit(self._colors[i])
            self.update()



class DisplayCanvasWidget(QtGui.QWidget) :

    def __init__(self, display) :
        super(DisplayCanvasWidget, self).__init__()

        self._display = display
        self._display.clear()
      
        self._display.fillScreen((0,0,0,255))
        self._display.setLineColor(self._display.White)
        self._display.refresh()
        self._polys = []
        self._colors = []
        self._mousePos = None

        self._currentColor = QtGui.QColor(255,255,255)

        self.setMinimumHeight(128)

    def addPoint(self, p) :
        poly = self._polys[-1]
        color = self._colors[-1]
        poly.append(p)
        if self._mousePos is not None:
            self._display.setLineColor((color.red(), color.green(), color.blue(), 255))
            self._display.drawLine(
                self._mousePos.x()*self._display.get_width()/self.width(),
                self._mousePos.y()*self._display.get_height()/self.height(),
                p.x()*self._display.get_width()/self.width(),
                p.y()*self._display.get_height()/self.height())
            self._display.refresh()
        self.update()
        self._mousePos = p


    def paintEvent(self, e) :
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0,0,0))
        for poly,color in zip(self._polys, self._colors) :
            painter.setPen(color)
            if len(poly) > 1 :
                painter.drawPolyline(QtGui.QPolygonF(poly))

    def mousePressEvent(self, e) :
        self._polys.append([])
        self._colors.append(self._currentColor)
        self.addPoint(e.pos())

    def mouseMoveEvent(self, e):
        self.addPoint(e.pos())

    def mouseReleaseEvent(self, e) :
        self.addPoint(e.pos())
        self._mousePos = None

    def setColor(self, c) :
        self._currentColor = c

    def clear(self) :
        self._display.fillScreen((0,0,0,255))
        self._display.refresh()
        self._polys = []
        self._colors = []
        self.update()



class DisplayWidget(TileWidget) :
    def __init__(self, port, deviceID) :

        super(DisplayWidget, self).__init__(port, deviceID)
        self._layout = QtGui.QVBoxLayout(self)
        #self._title = QtGui.QLabel(self._productName)
        #self._layout.addWidget(self._title)

        self._display = modulo.Display(port, deviceID)
        self._colorPickerWidget = ColorPickerWidget(horizontal = True)
        self._canvasWidget = DisplayCanvasWidget(self._display)
        self._clearButton = QtGui.QPushButton('Clear')
        self._clearButton.clicked.connect(self.onClear)

        self._toolbar = QtGui.QWidget()
        self._toolbarLayout = QtGui.QHBoxLayout(self._toolbar)
        self._toolbarLayout.addWidget(self._clearButton)
        self._toolbarLayout.addWidget(self._colorPickerWidget)

        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvasWidget)


        #self._display.drawLine(0, 0, self._display.get_width(), self._display.get_height())

        self._colorPickerWidget.colorChanged.connect(self.onColorChanged)

    def onColorChanged(self, c) :
        self._canvasWidget.setColor(c)

    def onClear(self) :
        self._canvasWidget.clear()


class KnobWidget(TileWidget) :

    def __init__(self, port, deviceID) :
        super(KnobWidget, self).__init__(port, deviceID)
        self._layout = QtGui.QVBoxLayout(self)
        self._title = QtGui.QLabel(self._productName)
        self._layout.addWidget(self._title)

        self._knob = modulo.Knob(port, deviceID)

        self._valueLabel = QtGui.QLabel("")
        self._layout.addWidget(self._valueLabel)

        self._layout.addStretch()
        self._colors = [
            QtGui.QColor(80, 80 ,80),
            QtGui.QColor(255, 0, 0),
            QtGui.QColor(255, 255, 0),
            QtGui.QColor(0, 255, 0),
            QtGui.QColor(0, 255, 255),
            QtGui.QColor(0, 0, 255),
            QtGui.QColor(255, 0, 255)
            ]
        self._currentColor = 0

        self._swatchWidth = 30


    def paintEvent(self, e) :
        painter = QtGui.QPainter(self)

        #painter.fillRect(self.rect(), QtGui.QColor(255,0,0))
        circleSize = .9*self.height()
        angle = self._knob.get_angle()*math.pi/180

        circleX = (self.width()-circleSize)/2
        circleY = (self.height()-circleSize)/2

        painter.setBrush(self._colors[self._currentColor])
        painter.drawEllipse(circleX, circleY, circleSize, circleSize)
        painter.drawLine(
            self.width()/2,
            self.height()/2,
            self.width()/2 + math.cos(angle)*circleSize/2,
            self.height()/2 + math.sin(angle)*circleSize/2)

        numColors = len(self._colors)
        for i in range(numColors) :
            painter.fillRect(self.width()-self._swatchWidth, i*self.height()//numColors,
                self._swatchWidth, self.height()//numColors + 1, self._colors[i])
        
    def mousePressEvent(self, e) :
        if (e.pos().x() >= self.width()-self._swatchWidth) :
            e.accept()
            self._currentColor = e.pos().y()*len(self._colors)/self.height()
            self.update()
            c = self._colors[self._currentColor]
            self._knob.set_color(c.red()/255.0, c.green()/255.0, c.blue()/255.0)

    def updateUI(self) :
        self._valueLabel.setText(str(self._knob.get_position()))
        self.update()

class ThermocoupleWidget(TileWidget) :

    def __init__(self, port, deviceID) :
        super(ThermocoupleWidget, self).__init__(port, deviceID)
        self._layout = QtGui.QVBoxLayout(self)
        self._title = QtGui.QLabel(self._productName)
        self._layout.addWidget(self._title)

        self._thermocouple = modulo.Thermocouple(port, deviceID)

        self._tempLabel = QtGui.QLabel("")
        self._layout.addWidget(self._tempLabel)

        self._layout.addStretch()

    def updateUI(self) :
        temp = self._thermocouple.get_fahrenheit()
        self._tempLabel.setText(str(temp))


class JoystickWidget(TileWidget) :

    def __init__(self, port, deviceID) :
        super(JoystickWidget, self).__init__(port, deviceID)
        self._layout = QtGui.QVBoxLayout(self)
        self._title = QtGui.QLabel(self._productName)
        self._layout.addWidget(self._title)

        self._joystick = modulo.Joystick(port, deviceID)

        self._layout.addStretch()

    def paintEvent(self, e) :
        painter = QtGui.QPainter(self)
        center = QtCore.QPoint(self.width()/2, self.height()/2)
        largeRect = QtCore.QRect(0,0,self.height()*.9, self.height()*.9)
        largeRect.moveCenter(center)

        smallRect = QtCore.QRect(0,0,self.height()*.3, self.height()*.3)
        smallRect.moveCenter(center - QtCore.QPoint(25*self._joystick.getHPos(),
            25*self._joystick.getVPos()))

        painter.drawEllipse(largeRect)

        if (self._joystick.getButton()) :
            painter.setBrush(QtGui.QColor(255,255,255))
        painter.drawEllipse(smallRect)

    def updateUI(self) :
        self.update()


class ControllerWidget(TileWidget) :

    def __init__(self, port, deviceID) :
        super(ControllerWidget, self).__init__(port, deviceID)
        self._layout = QtGui.QVBoxLayout(self)
        self._title = QtGui.QLabel(self._productName)
        self._layout.addWidget(self._title)


        self._layout.addStretch()


class Controller :

    def __init__(self) :
        self._port = modulo.Port()

        self._window = QtGui.QWidget()
        self._layout = QtGui.QVBoxLayout(self._window)
        self._layout.addStretch(10)
        self._window.show()

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.onRefresh)
        self._timer.start(100)

        self._tileWidgets = {}

        self._widgetClasses = {
            'co.modulo.knob' : KnobWidget,
            'co.modulo.joystick' : JoystickWidget,
            'co.modulo.controller' : ControllerWidget,
            'co.modulo.thermocouple' : ThermocoupleWidget,
            'co.modulo.colordisplay' : DisplayWidget,
        }

        self.onRefresh()

    def onRefresh(self) :
        deviceID = self._port._get_next_device_id(0)
        deviceIDs = []
        while deviceID is not None :
            deviceIDs.append(deviceID)
            deviceID = self._port._get_next_device_id(deviceID+1)

        for deviceID in deviceIDs :
            if deviceID not in self._tileWidgets :
                deviceType = self._port._get_device_type(deviceID)
                if deviceType in self._widgetClasses :
                    widget = self._widgetClasses[deviceType](self._port, deviceID)
                else :
                    widget = TileWidget(self._port, deviceID)
                count = self._layout.count()
                self._layout.insertWidget(len(self._tileWidgets), widget)
                self._tileWidgets[deviceID] = widget

        for deviceID in self._tileWidgets.keys() :
            if deviceID not in deviceIDs :
                self._tileWidgets[deviceID].setParent(None)
                del self._tileWidgets[deviceID]

        for widget in self._tileWidgets.values() :
            widget.updateUI()

        #qApp = QtGui.QApplication.instance()
        #palette = qApp.palette()

        #palette.setColor(QtGui.QPalette.WindowText,QtCore.Qt.red)
        #qApp.setPalette(palette)


# Use a darker color scheme so that the QPalette is more... paletteable?
def SetStyle(qApp) :
    # Overrides for some colors don't work with the default style
    qApp.setStyle(QtGui.QCommonStyle())

    palette = qApp.palette()

    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(64,64,64))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(90,90,90))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(110,110,110))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(160,160,160))

    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(240, 240, 240))

    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(240, 240, 240))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(240, 240, 240))
    palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))

    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(107, 153, 212))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(20, 20, 20))

    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Button,
                     QtGui.QColor(100,100,100))
    palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text,
                     QtGui.QColor(160,160,160))

    qApp.setPalette(palette)

    qApp.setStyleSheet("QLabel { color : white; }");


if __name__ == '__main__' :
    app = QtGui.QApplication(sys.argv)
    controller = Controller()
    SetStyle(app)

    app.exec_()
