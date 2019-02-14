
from flask import Flask
import furby
import RPi.GPIO as GPIO

app = Flask(__name__)

furby.prepareBoard()
f = furby.Furby()

@app.route('/')
def hello():
    return 'Hello, World!'


@app.route('/calibrate')
def calibrate():
    f.calibrate()
    return 'calibrated'

@app.route('/talk')
def talk():
    f.moveTo(20)
    f.moveTo(90)
    f.moveTo(10)
    f.moveTo(95)

"""
except KeyboardInterrupt:
    print("Cleanup by keyboard interrupt")
    GPIO.cleanup()
except Exception as e:
    print("uncaught error")
    print(e)
finally:
    print("Cleanup")
    GPIO.cleanup()

"""
