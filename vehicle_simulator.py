import pygame
import numpy as np
from collections import deque
import threading
import time

pygame.init()
try:
    pygame.joystick.init()
    joystick_count = pygame.joystick.get_count()
except Exception:
    joystick_count = 0


class VehicleSimulator:
    """
    Simulates vehicle inputs from:
    1. Steering wheel / joystick controller
    2. Keyboard fallback (arrow keys + space)
    """

    def __init__(self):
        self.joystick         = None
        self.steering_angle   = 0.0    # -1.0 to 1.0
        self.brake_pressed    = False
        self.throttle         = 0.0
        self.speed            = 0.0    # simulated speed km/h

        # History for micro-correction analysis
        self.steering_history = deque(maxlen=100)
        self.brake_history    = deque(maxlen=60)
        self.speed_history    = deque(maxlen=60)

        self.brake_events     = 0
        self.brake_start      = time.time()
        self.running          = False
        self._init_controller()

    def _init_controller(self):
        """Initialize steering wheel or joystick"""
        if joystick_count > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
            print(f"[INFO] Controller: {self.joystick.get_name()}")
        else:
            print("[INFO] No controller found — using keyboard simulation")

    def update(self, keys=None):
        """Update vehicle inputs from controller or keyboard"""
        pygame.event.pump()

        if self.joystick:
            # ── Steering wheel / joystick ─────────────────────────────────────
            # Axis 0 = steering, Axis 2 = throttle, Axis 3 = brake (varies by controller)
            try:
                self.steering_angle = self.joystick.get_axis(0)
                throttle_raw        = self.joystick.get_axis(1)
                self.throttle       = max(0, -throttle_raw)

                # Check brake button or axis
                if self.joystick.get_numaxes() > 2:
                    brake_raw         = self.joystick.get_axis(2)
                    self.brake_pressed = brake_raw > 0.3
                else:
                    self.brake_pressed = self.joystick.get_button(0)

            except Exception:
                self.steering_angle = 0.0

        elif keys is not None:
            # ── Keyboard fallback ─────────────────────────────────────────────
            if keys[pygame.K_LEFT]:
                self.steering_angle = max(-1.0, self.steering_angle - 0.05)
            elif keys[pygame.K_RIGHT]:
                self.steering_angle = min(1.0, self.steering_angle + 0.05)
            else:
                self.steering_angle *= 0.85  # return to centre

            self.throttle       = 0.3 if keys[pygame.K_UP] else 0.0
            self.brake_pressed  = keys[pygame.K_SPACE] or keys[pygame.K_DOWN]

        # ── Update speed simulation ───────────────────────────────────────────
        if self.brake_pressed:
            self.speed = max(0, self.speed - 8)
        elif self.throttle > 0:
            self.speed = min(130, self.speed + self.throttle * 5)
        else:
            self.speed = max(0, self.speed - 0.5)

        # ── Log to history ────────────────────────────────────────────────────
        self.steering_history.append(self.steering_angle)
        self.brake_history.append(1 if self.brake_pressed else 0)
        self.speed_history.append(self.speed)

        # Count brake events
        if self.brake_pressed:
            self.brake_events += 1

    def get_steering_variance(self):
        """
        Steering micro-correction variance.
        High variance = erratic driving = high cognitive load.
        """
        if len(self.steering_history) < 10:
            return 0.0
        arr  = np.array(self.steering_history)
        diff = np.diff(arr)
        return float(np.var(diff))

    def get_brake_frequency(self):
        """Brakes per minute"""
        elapsed = max(1, time.time() - self.brake_start)
        return (self.brake_events / elapsed) * 60

    def get_metrics(self):
        return {
            "steering_angle":    self.steering_angle,
            "steering_variance": self.get_steering_variance(),
            "brake_frequency":   self.get_brake_frequency(),
            "brake_pressed":     self.brake_pressed,
            "speed":             self.speed,
            "throttle":          self.throttle,
        }