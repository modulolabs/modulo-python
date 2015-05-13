#!/usr/local/bin/python
from PyQt4 import QtCore, QtGui
import modulo
import time
import math
import sys

lastUpdateTime = time.time()



class Pong(QtGui.QFrame):

    def __init__(self) :
        super(Pong, self).__init__()

        self._port = modulo.Port()
        self._display = modulo.Display(self._port)
        self._knob = modulo.Knob(self._port)

        self._paddleWidth = .01
        self._paddleHeight = .1

        self._leftPaddlePos = .5
        self._rightPaddlePos = .5
        self._knobPos = self._knob.get_position()

        self._paused = True
        self._lastUpdateTime = time.time()
        self._ballX = .5
        self._ballY = .5

        self._ballSpeed = .5
        self._ballDx = .9
        self._ballDy = .1

        self._leftPaddleSpeed = self._ballSpeed*.9

        self._rightScore = 0
        self._leftScore = 0

        self.resize(640, 480)
        self.show()

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.onTimeout)
        self._timer.start(10)

    def paintEvent(self, e) :

        painter = QtGui.QPainter(self)

        painter.fillRect(self.rect(), QtGui.QColor(0,0,0))

        painter.setBrush(QtGui.QColor(255,255,255))
        painter.drawEllipse(self.width()*self._ballX, self.height()*self._ballY,
            10, 10)

        painter.fillRect(
            self.width()*(1-self._paddleWidth),
            self.height()*(self._rightPaddlePos-self._paddleHeight/2),
            self.width()*self._paddleWidth,
            self.height()*self._paddleHeight,
            QtGui.QColor(255,255,255));

        painter.fillRect(0,
            self.height()*(self._leftPaddlePos-self._paddleHeight/2),
            self.width()*self._paddleWidth,
            self.height()*self._paddleHeight,
            QtGui.QColor(255,255,255));

    def update_input(self) :
        newKnobPos = self._knob.get_position()
        self._rightPaddlePos += .02*(newKnobPos - self._knobPos)
        self._knobPos = newKnobPos

        minPaddlePosition = self._paddleHeight/2
        maxPaddlePosition = 1-self._paddleHeight/2

        self._rightPaddlePos = max(self._rightPaddlePos, minPaddlePosition)
        self._rightPaddlePos = min(self._rightPaddlePos, maxPaddlePosition)

    def end_round(self) :
        self.draw()

        # Wait for 3 seconds
        pauseStartTime = time.time()
        while time.time() < pauseStartTime+3 :
            self._knob.set_hsv(time.time()-pauseStartTime, 1, 1)
        self._knob.set_color(0,0,0)

        # Move the ball back to the center
        self._ballX = .5
        self._ballY = .5

        # Reset the last update time, since we want to start the game from now
        self._lastUpdateTime = time.time()

    def check_right_goal(self) :
        rightGoal = 1-self._paddleWidth

        if (self._ballX < rightGoal) :
            return False

        posOnPaddle = self._ballY-self._rightPaddlePos

        # Check and see if the ball missed the paddle
        if abs(posOnPaddle) > .6*self._paddleHeight :
            return True

        angle = .5*math.pi*posOnPaddle/self._paddleHeight
        self._ballDx = -math.cos(angle)
        self._ballDy = math.sin(angle)
        return False

    def check_left_goal(self) :
        leftGoal = self._paddleWidth

        if (self._ballX > leftGoal) :
            return False

        posOnPaddle = self._ballY-self._leftPaddlePos

        # Check and see if the ball missed the paddle
        if abs(posOnPaddle) > .6*self._paddleHeight :
            return True

        angle = .5*math.pi*posOnPaddle/self._paddleHeight
        self._ballDx = -math.cos(angle)
        self._ballDy = math.sin(angle)
        return False

    def onTimeout(self) :
        knobWasPressed = False
        knobIsPressed = self._knob.get_button()
        if knobIsPressed and not knobWasPressed :
            self._paused = not self._paused
            self._lastUpdateTime = time.time()
        knobWasPressed = knobIsPressed

        self.update_input()
        self.update_game()

        self.update()

    def update_game(self) :
        if self._paused :
            return False

        leftGoal = self._paddleWidth

        if self.check_right_goal() :
            self._leftScore += 1
            self.end_round()
            return

        if self.check_left_goal() :
            self._rightScore += 1
            self.end_round()
            return

        currentTime = time.time()
        dt = currentTime-self._lastUpdateTime
        self._lastUpdateTime = time.time()

        if (self._leftPaddlePos > self._ballY) :
            self._leftPaddlePos -= dt*self._leftPaddleSpeed
        if (self._leftPaddlePos < self._ballY) :
            self._leftPaddlePos += dt*self._leftPaddleSpeed

        if (self._ballX <= leftGoal) :
            self._ballDx = -self._ballDx

        if (self._ballY >= 1 or
            self._ballY <= 0) :
            self._ballDy = -self._ballDy

        self._ballX += self._ballSpeed*self._ballDx*dt
        self._ballY += self._ballSpeed*self._ballDy*dt

    def draw(self) :
        """
        self._display.clear()

        self._display.draw_ellipse(self._ballX, self._ballY, 2, 2, 1)

        self._display.draw_rectangle(self._width-self._paddleWidth,
            self._rightPaddlePos-self._paddleHeight/2, self._paddleWidth,
            self._paddleHeight,
            fill=1);

        self._display.draw_rectangle(0,
            self._leftPaddlePos-self._paddleHeight/2, self._paddleWidth,
            self._paddleHeight,
            fill=1);

        self._display.set_cursor(self._width/3, 0)
        self._display.write(self._leftScore)

        self._display.set_cursor(self._width*2/3, 0)
        self._display.write(self._rightScore)

        if self._paused :
            self._display.draw_rectangle(25, 10,
                self._width-40, self._height-20, fill=0, outline=1)
            self._display.set_cursor(0, 15)
            self._display.writeln("        Paused.")
            self._display.writeln("      Press Knob")
            self._display.writeln("      to continue")


        self._display.update()
        """

if __name__ == '__main__' :
    app = QtGui.QApplication(sys.argv)
    pong = Pong()
    app.exec_()



