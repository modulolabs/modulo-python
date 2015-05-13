#!/usr/local/bin/python
from PyQt4 import QtCore, QtGui
import modulo
import time
import math
import sys

lastUpdateTime = time.time()

class Paddle(object) :

    def __init__(self, knob, left) :
        self.knob = knob
        self.knobPos = knob.get_position()
        self.paddlePos = .5
        self.speed = .4
        self.score = 0
        self.paddleWidth = .01
        self.paddleHeight = .1
        self.knobWasPressed = False
        self.isLeft = left
        self.lastKnobMove = 0
        self.idleTimeout = 5




class Pong(QtGui.QFrame):

    RunningState = 0
    GoalState = 1

    def __init__(self) :
        super(Pong, self).__init__()

        self._port = modulo.Port()
        self._display = modulo.Display(self._port)
        self._leftKnob = modulo.Knob(self._port, 1560)
        self._rightKnob = modulo.Knob(self._port, 65282)

        self._rightKnob.set_color(1,0,0)
        self._leftKnob.set_color(0,0,1)

        self._leftPaddle = Paddle(self._leftKnob, True)
        self._rightPaddle = Paddle(self._rightKnob, False)

        self._paused = True
        self._lastUpdateTime = time.time()
        self._ballX = .5
        self._ballY = .5

        self._ballSpeed = .7
        self._ballDx = .9
        self._ballDy = .1

        self.resize(640, 480)
        self.show()

        self._timer = QtCore.QTimer()
        self._timer.timeout.connect(self.onTimeout)
        self._timer.start(10)

        self._stateStartTime = time.time()
        self._state = self.RunningState

        self.updateScoreboard()

    def paintEvent(self, e) :

        painter = QtGui.QPainter(self)

        painter.fillRect(self.rect(), QtGui.QColor(0,0,0))

        painter.setBrush(QtGui.QColor(255,255,255))
        painter.drawEllipse(self.width()*self._ballX, self.height()*self._ballY,
            10, 10)

        for paddle in self._leftPaddle, self._rightPaddle :
            if paddle.isLeft :
                x = 0
            else :
                x = 1-paddle.paddleWidth
            if paddle.isLeft :
                color = QtGui.QColor(0,0,255)
            else :
                color = QtGui.QColor(255,0,0)
            painter.fillRect(
                self.width()*x,
                self.height()*(paddle.paddlePos-paddle.paddleHeight/2),
                self.width()*paddle.paddleWidth,
                self.height()*paddle.paddleHeight,
                color);

    def onTimeout(self) :
        self.update_game()
        self.update()

        if False :
             # Wait for 3 seconds
            pauseStartTime = time.time()
            while time.time() < pauseStartTime+3 :
                self._knob.set_hsv(time.time()-pauseStartTime, 1, 1)
                self._knob.set_color(0,0,0)

            # Move the ball back to the center
            self._ballX = .5
            self._ballY = .5
            self._ballDx = .9
            self._ballDy = .1

            # Reset the last update time, since we want to start the game from now
            self._lastUpdateTime = time.time()

    def check_goal(self, paddle) :
        if (paddle.isLeft and self._ballX > paddle.paddleWidth) :
            return False
        if (not paddle.isLeft and self._ballX < 1-paddle.paddleWidth) :
            return False

        posOnPaddle = self._ballY-paddle.paddlePos

        # Check and see if the ball missed the paddle
        if abs(self._ballY-paddle.paddlePos) > paddle.paddleHeight/2:
            return True

        angle = .5*math.pi*posOnPaddle*.8/paddle.paddleHeight

        self._ballDx = -math.cos(angle)
        self._ballDy = math.sin(angle)

        if paddle.isLeft :
            self._ballDx = -self._ballDx

        return False
    
    def updateScoreboard(self) :
        self._display.clear()
        self._display.setTextSize(2)
        self._display.setTextColor((255,0,0,255))
        self._display.setCursor(0, 10);
        self._display.write(str(self._rightPaddle.score))
        self._display.setTextColor((0,0,255,255))
        self._display.setCursor(0, 30);
        self._display.write(str(self._leftPaddle.score))
        self._display.refresh()
        self._display.setTextColor((255,255,255,255))
        self._display.setTextSize(1)


    def update_game(self) :
        currentTime = time.time()
        dt = currentTime-self._lastUpdateTime
        self._lastUpdateTime = time.time()

        if self._state == self.GoalState :
            self.updateScoreboard()
            if (time.time() > self._stateStartTime+1) :
                self._state = self.RunningState
                self._ballX = .5
                self._ballY = .5
            return


        for paddle in self._leftPaddle, self._rightPaddle :
            if (time.time() > paddle.lastKnobMove+paddle.idleTimeout) :
                if (paddle.paddlePos > self._ballY) :
                    paddle.paddlePos -= dt*paddle.speed
                if (paddle.paddlePos < self._ballY) :
                    paddle.paddlePos += dt*paddle.speed

            newKnobPos = paddle.knob.get_position()
            if newKnobPos != paddle.knobPos :
                paddle.paddlePos += .02*(newKnobPos - paddle.knobPos)
                paddle.knobPos = newKnobPos
                paddle.lastKnobMove = time.time()


            paddle.paddlePos = max(paddle.paddlePos, paddle.paddleHeight/2)
            paddle.paddlePos = min(paddle.paddlePos, 1-paddle.paddleHeight/2)

        if (self.check_goal(self._leftPaddle)) :
            self._state = self.GoalState
            self._stateStartTime = time.time()
            self._rightPaddle.score += 1
            return           

        if (self.check_goal(self._rightPaddle)) :
            self._state = self.GoalState
            self._stateStartTime = time.time()
            self._leftPaddle.score += 1
            return

        if (self._ballX <= 0) :
            self._ballDx = math.fabs(self._ballDx)
        if (self._ballX >= 1) :
            self._ballDx = -math.fabs(self._ballDx)

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



