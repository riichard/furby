#!/usr/bin/env python3
"""furby.py — Low-level hardware driver for 1st-gen Furby on Raspberry Pi."""

import math
import time

import RPi.GPIO as GPIO

# ---------------------------------------------------------------------------
# GPIO pin assignments (BOARD numbering)
# ---------------------------------------------------------------------------
AIN1      = 29  # Motor direction
AIN2      = 31  # Motor direction
PWMA      = 7   # Motor enable
STDBY     = 13  # Motor standby
IR        = 18  # IR position sensor
CAL       = 36  # Calibration switch
TONGUE    = 33  # Tongue button
PWMA_TEST = 32  # PWM output (BCM12)


class Furby:
    def __init__(self):
        self.pos        = 1
        self.maxPos     = 0
        self.maxError   = 30
        self.speed      = 70
        self.clockwise  = True
        self.calibrated = False
        self.des        = 0
        self.desPerc    = 0

        GPIO.cleanup()
        GPIO.setmode(GPIO.BOARD)

        GPIO.setup(IR,        GPIO.IN,  pull_up_down=GPIO.PUD_UP)
        GPIO.setup(CAL,       GPIO.IN,  pull_up_down=GPIO.PUD_UP)
        GPIO.setup(TONGUE,    GPIO.IN,  pull_up_down=GPIO.PUD_UP)
        GPIO.setup(PWMA_TEST, GPIO.OUT)
        GPIO.setup(PWMA,      GPIO.OUT)
        GPIO.setup(AIN1,      GPIO.OUT)
        GPIO.setup(AIN2,      GPIO.OUT)
        GPIO.setup(STDBY,     GPIO.OUT)

        self.pwm = GPIO.PWM(PWMA_TEST, 300)

        GPIO.add_event_detect(CAL,    GPIO.RISING, callback=self._cal_callback,    bouncetime=200)
        GPIO.add_event_detect(TONGUE, GPIO.RISING, callback=self._tongue_callback, bouncetime=200)
        GPIO.add_event_detect(IR,     GPIO.RISING, callback=self._ir_callback)

        self._set_direction(True)

    # ------------------------------------------------------------------
    # Motor primitives
    # ------------------------------------------------------------------

    def start(self):
        GPIO.output(STDBY, GPIO.HIGH)
        self.pwm.start(self.speed)

    def stop(self):
        self.pwm.stop()
        GPIO.output(STDBY, GPIO.LOW)

    def _set_direction(self, clockwise):
        if clockwise:
            GPIO.output(AIN1, GPIO.HIGH)
            GPIO.output(AIN2, GPIO.LOW)
        else:
            GPIO.output(AIN1, GPIO.LOW)
            GPIO.output(AIN2, GPIO.HIGH)
        self.clockwise = clockwise

    def set_speed(self, speed):
        self.speed = speed
        self.pwm.ChangeDutyCycle(speed)

    # ------------------------------------------------------------------
    # GPIO callbacks
    # ------------------------------------------------------------------

    def _cal_callback(self, pin):
        self.calibrated = True
        self.pos = 0

    def _ir_callback(self, pin):
        if self.maxPos < self.pos:
            self.maxPos = self.pos
        self.pos += 1 if self.clockwise else -1

    def _tongue_callback(self, pin):
        pass

    # ------------------------------------------------------------------
    # Movement
    # ------------------------------------------------------------------

    def _move_up(self, des):
        self._set_direction(True)
        self.des = des
        self.start()
        while self.pos < des:
            time.sleep(0.0001)
        self.stop()

    def _move_down(self, des):
        self._set_direction(False)
        self.des = des
        self.start()
        while self.pos > des:
            time.sleep(0.0001)
        self.stop()

    def moveTo(self, angle):
        """Move dial to position angle (0–100%)."""
        des = min(
            math.floor((self.maxPos / 100) * angle),
            self.maxPos - self.maxError,
        )
        self.desPerc = angle

        delta_direct = abs(self.pos - des)
        delta_wrap   = min(
            abs((des + self.maxPos) - self.pos),
            abs((self.maxPos + self.pos) - des),
        )

        if delta_direct <= delta_wrap:
            if des > self.pos:
                self._move_up(des)
            else:
                self._move_down(des)
        else:
            if des < self.pos:
                self.pos -= self.maxPos
                self._move_up(des)
            else:
                self._move_down(des - self.maxPos)

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self):
        """Spin one full cycle to measure maxPos, then settle at position 10."""
        print("[furby] Calibrating...")
        self.des = 0
        self._set_direction(True)
        self.start()
        time.sleep(5)
        self.stop()
        time.sleep(1)
        # Exercise range to confirm positions
        for angle in (10, 50, 80, 90, 10):
            self.moveTo(angle)
        print(f"[furby] Calibrated. MaxPos={self.maxPos}")

    def cleanup(self):
        GPIO.cleanup()


# ---------------------------------------------------------------------------
# Manual test (run directly on Pi)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        f = Furby()
        f.calibrate()
        print(f"pos={f.pos}  maxPos={f.maxPos}")

        for angle in (10, 50, 90):
            input(f"Press Enter to move to {angle}%...")
            f.moveTo(angle)

    except KeyboardInterrupt:
        print("Interrupted.")
    finally:
        GPIO.cleanup()
