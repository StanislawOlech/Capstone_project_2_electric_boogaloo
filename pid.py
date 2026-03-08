# VIBE CODED SECTION STARTS
class PID:
    def __init__(self, kp, ki, kd, limit=None):
        self.kp = kp
        self.ki = ki
        self.kd = kd

        self.prev_error = 0
        self.integral = 0
        self.limit = limit

    def update(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0

        output = (
            self.kp * error +
            self.ki * self.integral +
            self.kd * derivative
        )

        self.prev_error = error

        if self.limit is not None:
            output = max(-self.limit, min(self.limit, output))

        return int(output)
# VIBE CODED SECTION ENDS