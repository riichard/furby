#!/usr/bin/env python

# Import required modules
import time
import RPi.GPIO as GPIO

# Declare the GPIO settings
GPIO.setmode(GPIO.BOARD)

# Turn off GPIO warnings caused by us declaring our pins outside of the start_furby and stop_furby functions
GPIO.setwarnings(True)

GPIO.cleanup()

def stop_furby():
    # Reset all the GPIO pins by setting them to LOW
    GPIO.output(16, GPIO.LOW) # Set AIN1
    GPIO.output(11, GPIO.LOW) # Set AIN2
    GPIO.output(7, GPIO.LOW) # Set PWMA
    GPIO.output(13, GPIO.LOW) # Set STBY

def main():
    # Set up GPIO pins
    GPIO.setup(7, GPIO.OUT) # Connected to PWMA 
    GPIO.setup(11, GPIO.OUT) # Connected to AIN2
    GPIO.setup(16, GPIO.OUT) # Connected to AIN1
    GPIO.setup(13, GPIO.OUT) # Connected to STBY

    stop_furby()

    return

if __name__ == '__main__':
    main()
