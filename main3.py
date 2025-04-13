from kivy.app import App
from kivy.uix.widget import Widget
from kivy.graphics import Line, Color, Ellipse, Rectangle, Triangle
from kivy.clock import Clock
from kivy.uix.floatlayout import FloatLayout
from kivy.core.text import Label as CoreLabel
import math
import random
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
# Add MPU6050 imports
import smbus2 as smbus
import time

# MPU6050 Class for handling sensor data
class MPU6050:
    def __init__(self):
        # MPU6050 device address
        self.device_address = 0x68
        # Power management registers
        self.power_mgmt_1 = 0x6b
        self.power_mgmt_2 = 0x6c
        
        # Initialize I2C bus
        try:
            self.bus = smbus.SMBus(1)
            # Wake up the MPU6050
            self.bus.write_byte_data(self.device_address, self.power_mgmt_1, 0)
            print("MPU6050 initialized successfully")
            self.sensor_available = True
        except Exception as e:
            print(f"Failed to initialize MPU6050: {e}")
            self.sensor_available = False
    
    def read_word(self, register):
        """Read a word from the MPU6050"""
        if not self.sensor_available:
            return 0
        try:
            high = self.bus.read_byte_data(self.device_address, register)
            low = self.bus.read_byte_data(self.device_address, register + 1)
            value = (high << 8) + low
            if value >= 0x8000:
                return -((65535 - value) + 1)
            else:
                return value
        except Exception as e:
            print(f"Error reading from sensor: {e}")
            return 0
    
    def read_accel_data(self):
        """Read accelerometer data"""
        if not self.sensor_available:
            return {'x': 0, 'y': 0, 'z': 0}
        try:
            accel_x = self.read_word(0x3b) / 16384.0  # Divide by sensitivity scale factor for ±2g
            accel_y = self.read_word(0x3d) / 16384.0
            accel_z = self.read_word(0x3f) / 16384.0
            return {'x': accel_x, 'y': accel_y, 'z': accel_z}
        except Exception as e:
            print(f"Error reading accelerometer data: {e}")
            return {'x': 0, 'y': 0, 'z': 0}
    
    def read_gyro_data(self):
        """Read gyroscope data"""
        if not self.sensor_available:
            return {'x': 0, 'y': 0, 'z': 0}
        try:
            gyro_x = self.read_word(0x43) / 131.0  # Divide by sensitivity scale factor for ±250°/s
            gyro_y = self.read_word(0x45) / 131.0
            gyro_z = self.read_word(0x47) / 131.0
            return {'x': gyro_x, 'y': gyro_y, 'z': gyro_z}
        except Exception as e:
            print(f"Error reading gyroscope data: {e}")
            return {'x': 0, 'y': 0, 'z': 0}
    
    def read_temp_data(self):
        """Read temperature data"""
        if not self.sensor_available:
            return 0
        try:
            temp = self.read_word(0x41) / 340.0 + 36.53  # Formula from datasheet
            return temp
        except Exception as e:
            print(f"Error reading temperature data: {e}")
            return 0
    
    def get_rotation_angles(self):
        """Calculate pitch and roll from accelerometer data"""
        if not self.sensor_available:
            return {'pitch': 0, 'roll': 0, 'yaw': 0}
        try:
            accel = self.read_accel_data()
            gyro = self.read_gyro_data()
            
            # Simple complementary filter for more stable readings would be implemented here
            # This is a simplified calculation
            roll = math.atan2(accel['y'], accel['z']) * 180/math.pi
            pitch = math.atan2(-accel['x'], math.sqrt(accel['y']*accel['y'] + accel['z']*accel['z'])) * 180/math.pi
            
            # We use the gyro value directly for yaw, as the MPU6050 can't determine absolute heading
            # In a real implementation, you'd want to integrate the gyro_z value over time
            yaw = gyro['z']  # This is just the rotation rate, not absolute position
            
            return {'pitch': pitch, 'roll': roll, 'yaw': yaw}
        except Exception as e:
            print(f"Error calculating rotation angles: {e}")
            return {'pitch': 0, 'roll': 0, 'yaw': 0}
    
    def estimate_speed(self):
        """Estimate relative speed from accelerometer data - very approximate"""
        if not self.sensor_available:
            return 0
        try:
            accel = self.read_accel_data()
            # This is a very simplified approximation - actual speed calculation 
            # would require integration of acceleration over time
            magnitude = math.sqrt(accel['x']**2 + accel['y']**2 + accel['z']**2)
            # Map the magnitude to a speed range (0-200 km/h)
            # This is purely demonstrative and not accurate
            speed = (magnitude - 1.0) * 100  # 1g is baseline
            return max(0, min(200, speed))  # Clamp between 0-200
        except Exception as e:
            print(f"Error estimating speed: {e}")
            return 0

class StarkHUDWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.heading = 0
        self.altitude = 100
        self.speed = 0
        self.power = 87
        self.pitch = 0   # Attitude pitch in degrees
        self.roll = 0    # Attitude roll in degrees
        self.yaw = 0     # Attitude yaw in degrees 
        self.target_locked = False
        self.scanning = True
        self.system_status = "ALL SYSTEMS NOMINAL"
        self.scan_angle = 0
        self.data_points = []
        
        # Initialize the MPU6050 sensor
        self.mpu = MPU6050()
        
        # Initialize data points for visualization
        for _ in range(30):
            self.data_points.append(0.5)  # Start with neutral values
            
        Clock.schedule_interval(self.update, 1/30)  # 30 FPS update rate
        
    def update(self, dt):
        # Get data from MPU6050
        angles = self.mpu.get_rotation_angles()
        self.pitch = angles['pitch']
        self.roll = angles['roll']
        
        # Update heading based on MPU6050 yaw rate
        # In a real application, you would need to integrate the yaw rate over time
        # This is simplified for demonstration
        yaw_rate = angles['yaw']
        self.yaw += yaw_rate * dt
        self.heading = self.yaw % 360  # Keep heading between 0-360
        
        # Update speed estimation
        self.speed = self.mpu.estimate_speed()
        
        # Update scan animation
        self.scan_angle = (self.scan_angle + 5) % 360
        
        # Update data visualization with newest sensor data
        accel = self.mpu.read_accel_data()
        gyro = self.mpu.read_gyro_data()
        
        # Update data points with normalized sensor values
        new_point = (abs(accel['x']) + abs(accel['y']) + abs(accel['z'])) / 6.0  # Normalize to 0-1 range
        self.data_points.append(new_point)
        self.data_points.pop(0)  # Remove oldest point
        
        self.canvas.clear()
        self.draw_elements()
        
    def draw_elements(self):
        center_x = self.width / 2
        center_y = self.height / 2
        
        with self.canvas:
            # Background elements - hexagonal grid pattern
            Color(0, 0.7, 0.9, 0.1)  # Iron Man blue with low opacity
            self.draw_hex_grid(20, 20, center_x, center_y)
            
            # Main targeting reticle
            self.draw_targeting_reticle(center_x, center_y)
            
            # Top arc with heading
            self.draw_heading_arc(center_x, self.height - 50)
            
            # Bottom status display
            self.draw_status_bar(center_x, 50)
            
            # Left side power display
            self.draw_power_indicator(60, center_y)
            
            # Right side altitude indicator
            self.draw_altitude_indicator(self.width - 60, center_y)
            
            # Pitch and Roll attitude indicator
            self.draw_attitude_indicator(center_x, center_y)
            
            # Data visualization on edges
            self.draw_data_visualization()

    def draw_hex_grid(self, rows, cols, center_x, center_y):
        hex_size = 30
        width = hex_size * cols * 1.5
        height = hex_size * rows * 0.866 * 2
        
        start_x = center_x - width/2
        start_y = center_y - height/2
        
        for row in range(rows):
            for col in range(cols):
                # Stagger every other row
                offset_x = hex_size * 0.75 if row % 2 else 0
                
                x = start_x + col * hex_size * 1.5 + offset_x
                y = start_y + row * hex_size * 1.732
                
                # Only draw if in visible area and not in center (to keep center cleaner)
                dist_from_center = math.sqrt((x - center_x)**2 + (y - center_y)**2)
                if 0 < x < self.width and 0 < y < self.height and dist_from_center > 100:
                    self.draw_hexagon(x, y, hex_size/3)

    def draw_hexagon(self, x, y, size):
        points = []
        for i in range(6):
            angle = math.radians(60 * i + 30)
            points.extend([
                x + size * math.cos(angle),
                y + size * math.sin(angle)
            ])
        Line(points=points, width=1, close=True)

    def draw_targeting_reticle(self, x, y):
        # Main targeting reticle - Iron Man style circular elements
        reticle_size = 120
        
        # Outer circle
        Color(0, 0.7, 0.9, 0.8)  # Iron Man blue
        Line(circle=(x, y, reticle_size), width=1.5)
        
        # Inner rotating elements
        Color(0, 0.7, 0.9, 0.6)
        
        # Inner circle
        Line(circle=(x, y, reticle_size * 0.7), width=1)
        
        # Dynamic rotating elements
        PushMatrix()
        Rotate(origin=(x, y), angle=self.scan_angle)
        
        # Tick marks around inner circle
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            inner_r = reticle_size * 0.7
            outer_r = reticle_size * 0.8
            x1 = x + inner_r * math.cos(rad)
            y1 = y + inner_r * math.sin(rad)
            x2 = x + outer_r * math.cos(rad)
            y2 = y + outer_r * math.sin(rad)
            Line(points=[x1, y1, x2, y2], width=1)
        
        # Crosshairs
        Line(points=[x - reticle_size*0.5, y, x - reticle_size*0.2, y], width=1)
        Line(points=[x + reticle_size*0.2, y, x + reticle_size*0.5, y], width=1)
        Line(points=[x, y - reticle_size*0.5, x, y - reticle_size*0.2], width=1)
        Line(points=[x, y + reticle_size*0.2, x, y + reticle_size*0.5], width=1)
        PopMatrix()
        
        # Central dynamic element
        Color(1, 1, 1, 0.9)
        reticle_inner = 15
        Line(circle=(x, y, reticle_inner), width=1)
        
        # Small triangles at cardinal points
        triangle_size = 5
        for angle in [0, 90, 180, 270]:
            rad = math.radians(angle)
            tx = x + reticle_inner * math.cos(rad)
            ty = y + reticle_inner * math.sin(rad)
            
            # Triangle points
            p1x = tx - triangle_size/2
            p1y = ty - triangle_size/2
            p2x = tx + triangle_size/2
            p2y = ty - triangle_size/2
            p3x = tx
            p3y = ty + triangle_size/2
            
            # Rotate points based on angle
            if angle == 0:  # Right
                p1x, p1y = tx, ty - triangle_size/2
                p2x, p2y = tx, ty + triangle_size/2
                p3x, p3y = tx + triangle_size, ty
            elif angle == 90:  # Top
                p1x, p1y = tx - triangle_size/2, ty
                p2x, p2y = tx + triangle_size/2, ty
                p3x, p3y = tx, ty + triangle_size
            elif angle == 180:  # Left
                p1x, p1y = tx, ty - triangle_size/2
                p2x, p2y = tx, ty + triangle_size/2
                p3x, p3y = tx - triangle_size, ty
            else:  # Bottom
                p1x, p1y = tx - triangle_size/2, ty
                p2x, p2y = tx + triangle_size/2, ty
                p3x, p3y = tx, ty - triangle_size
            
            Triangle(points=[p1x, p1y, p2x, p2y, p3x, p3y])

    def draw_attitude_indicator(self, x, y):
        # Artificial horizon / attitude indicator
        attitude_size = 180  # Size of the attitude indicator
        
        # Outer frame
        Color(0, 0.7, 0.9, 0.7)
        Line(circle=(x, y, attitude_size), width=1.5)
        
        # Save state before rotation
        PushMatrix()
        # Apply roll rotation
        Rotate(origin=(x, y), angle=self.roll)
        
        # Calculate pitch offset (pixels per degree)
        pixels_per_degree = 2.5
        pitch_offset = self.pitch * pixels_per_degree
        
        # Horizon line
        Color(1, 1, 1, 0.8)
        Line(points=[x - attitude_size, y - pitch_offset, 
                     x + attitude_size, y - pitch_offset], width=2)
        
        # Pitch ladder (lines above and below horizon)
        for degrees in range(-90, 91, 10):
            if degrees == 0:  # Skip 0 degrees (horizon already drawn)
                continue
                
            # Calculate y position based on pitch
            ladder_y = y - pitch_offset + degrees * pixels_per_degree
            
            # Only draw if in visible range
            if y - attitude_size <= ladder_y <= y + attitude_size:
                # Determine line length based on angle
                line_length = attitude_size * 0.5 if degrees % 30 == 0 else attitude_size * 0.2
                
                Line(points=[x - line_length/2, ladder_y, 
                             x + line_length/2, ladder_y], width=1)
                             
                # Add degree numbers for major angles
                if degrees % 30 == 0:
                    degree_label = CoreLabel(text=f"{abs(degrees)}°", font_size=10)
                    degree_label.refresh()
                    texture = degree_label.texture
                    
                    # Position text at the end of the line
                    text_x = x - line_length/2 - texture.width - 5 if degrees > 0 else x + line_length/2 + 5
                    Rectangle(pos=(text_x, ladder_y - texture.height/2),
                              size=texture.size, texture=texture)
        
        PopMatrix()
        
        # Draw fixed reference marker (aircraft symbol)
        Color(1, 0.8, 0.0, 0.9)  # Restored bright gold/yellow
        
        # Central dot
        Line(circle=(x, y, 2), width=2)
        
        # Aircraft wings
        wing_width = 25
        Line(points=[x - wing_width, y, x - 10, y], width=2)
        Line(points=[x + 10, y, x + wing_width, y], width=2)
        
        # Vertical stabilizer
        Line(points=[x, y, x, y - 10], width=2)
        
        # Attitude values display
        value_x = x + attitude_size + 15
        value_y = y + 40
        spacing = 20
        
        Color(0, 0.7, 0.9, 0.9)
        
        # Pitch value
        pitch_text = f"PITCH: {self.pitch:.1f}°"
        label = CoreLabel(text=pitch_text, font_size=12)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(value_x, value_y), size=texture.size, texture=texture)
        
        # Roll value
        roll_text = f"ROLL: {self.roll:.1f}°"
        label = CoreLabel(text=roll_text, font_size=12)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(value_x, value_y - spacing), size=texture.size, texture=texture)
        
        # Yaw value
        yaw_text = f"YAW: {self.yaw:.1f}°"
        label = CoreLabel(text=yaw_text, font_size=12)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(value_x, value_y - spacing*2), size=texture.size, texture=texture)
        
        # Draw roll indicator at the top of the attitude indicator
        roll_indicator_radius = attitude_size + 15
        
        # Draw roll scale arc
        Color(0, 0.7, 0.9, 0.5)
        
        # Draw roll scale tick marks
        for roll_angle in range(-60, 61, 10):
            angle_rad = math.radians(roll_angle - 90)  # -90 to rotate to top
            tick_x = x + roll_indicator_radius * math.cos(angle_rad)
            tick_y = y + roll_indicator_radius * math.sin(angle_rad)
            
            # Longer ticks for major angles
            tick_length = 10 if roll_angle % 30 == 0 else 5
            
            inner_x = x + (roll_indicator_radius - tick_length) * math.cos(angle_rad)
            inner_y = y + (roll_indicator_radius - tick_length) * math.sin(angle_rad)
            
            Line(points=[inner_x, inner_y, tick_x, tick_y], width=1)
            
            # Add labels for major tick marks
            if roll_angle % 30 == 0 and roll_angle != 0:
                label = CoreLabel(text=f"{abs(roll_angle)}", font_size=10)
                label.refresh()
                texture = label.texture
                label_x = x + (roll_indicator_radius + 5) * math.cos(angle_rad) - texture.width/2
                label_y = y + (roll_indicator_radius + 5) * math.sin(angle_rad) - texture.height/2
                Rectangle(pos=(label_x, label_y), size=texture.size, texture=texture)
        
        # Draw the roll indicator arrow
        Color(1, 0.8, 0.0, 0.9)  # Restored bright gold/yellow
        roll_rad = math.radians(self.roll - 90)  # -90 to rotate to top
        arrow_x = x + roll_indicator_radius * math.cos(roll_rad)
        arrow_y = y + roll_indicator_radius * math.sin(roll_rad)
        
        # Arrow shape
        triangle_size = 8
        triangle_points = [
            arrow_x, arrow_y,
            arrow_x - triangle_size/2, arrow_y - triangle_size,
            arrow_x + triangle_size/2, arrow_y - triangle_size
        ]
        Triangle(points=triangle_points)

    def draw_heading_arc(self, x, y):
        arc_width = 400
        arc_height = 60
        
        # Draw arc background
        Color(0, 0.7, 0.9, 0.2)
        Rectangle(pos=(x - arc_width/2, y - arc_height/2),
                  size=(arc_width, arc_height))
        
        # Draw heading markers
        Color(0, 0.7, 0.9, 0.7)
        for deg in range(0, 360, 10):
            rel_pos = ((deg - self.heading) % 360) / 360
            if 0.1 <= rel_pos <= 0.9:  # Only show portion of compass
                marker_x = x - arc_width/2 + rel_pos * arc_width
                marker_height = arc_height/4 if deg % 30 == 0 else arc_height/8
                Line(points=[marker_x, y - marker_height/2, marker_x, y + marker_height/2], width=1)
                
                if deg % 30 == 0:
                    # Add degree text
                    label = CoreLabel(text=f"{deg}°", font_size=10)
                    label.refresh()
                    texture = label.texture
                    Rectangle(pos=(marker_x - texture.width/2, y + marker_height), 
                              size=texture.size, texture=texture)
        
        # Draw center heading indicator (triangle)
        Color(1, 1, 1, 0.9)
        triangle_size = 10
        triangle_points = [
            x, y + arc_height/2 + triangle_size,  # Top
            x - triangle_size/2, y + arc_height/2,  # Bottom left
            x + triangle_size/2, y + arc_height/2   # Bottom right
        ]
        Line(points=triangle_points, width=1.5, close=True)
        
        # Current heading text
        heading_text = f"HDG {int(self.heading)}°"
        label = CoreLabel(text=heading_text, font_size=16)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(x - texture.width/2, y - 30), size=texture.size, texture=texture)

    def draw_status_bar(self, x, y):
        bar_width = 500
        bar_height = 30
        
        # Status bar background
        Color(0, 0.7, 0.9, 0.2)
        Rectangle(pos=(x - bar_width/2, y - bar_height/2),
                  size=(bar_width, bar_height))
        
        # Status text
        Color(1, 1, 1, 0.9)
        label = CoreLabel(text=self.system_status, font_size=14)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(x - texture.width/2, y - texture.height/2), 
                  size=texture.size, texture=texture)
        
        # Speed indicator on the left
        speed_x = x - bar_width/2 - 80
        speed_text = f"SPD: {self.speed} KM/H"
        speed_label = CoreLabel(text=speed_text, font_size=14)
        speed_label.refresh()
        texture = speed_label.texture
        Rectangle(pos=(speed_x - texture.width/2, y - texture.height/2), 
                  size=texture.size, texture=texture)

    def draw_power_indicator(self, x, y):
        indicator_height = 300
        indicator_width = 40
        
        # Background
        Color(0, 0.7, 0.9, 0.2)
        Rectangle(pos=(x - indicator_width/2, y - indicator_height/2),
                  size=(indicator_width, indicator_height))
        
        # Power level
        Color(0, 0.7, 0.9, 0.6)
        power_height = (self.power / 100) * indicator_height
        Rectangle(pos=(x - indicator_width/2, y - indicator_height/2),
                  size=(indicator_width, power_height))
        
        # Ticks
        Color(1, 1, 1, 0.7)
        for i in range(11):  # 0% to 100% in steps of 10%
            tick_y = y - indicator_height/2 + (i/10) * indicator_height
            tick_width = indicator_width if i % 5 == 0 else indicator_width * 0.7
            Line(points=[x - tick_width/2, tick_y, x + tick_width/2, tick_y], width=1)
            
            if i % 2 == 0:
                # Add percentage text
                label = CoreLabel(text=f"{i*10}%", font_size=10)
                label.refresh()
                texture = label.texture
                Rectangle(pos=(x - indicator_width/2 - texture.width - 5, tick_y - texture.height/2), 
                          size=texture.size, texture=texture)
        
        # Power text at top
        label = CoreLabel(text="POWER", font_size=12)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(x - texture.width/2, y + indicator_height/2 + 5), 
                  size=texture.size, texture=texture)

    def draw_altitude_indicator(self, x, y):
        indicator_height = 300
        indicator_width = 40
        
        # Background
        Color(0, 0.7, 0.9, 0.2)
        Rectangle(pos=(x - indicator_width/2, y - indicator_height/2),
                  size=(indicator_width, indicator_height))
        
        # Altitude ticks
        Color(1, 1, 1, 0.7)
        for i in range(11):  # 0m to 200m in steps of 20m
            tick_y = y - indicator_height/2 + (i/10) * indicator_height
            tick_width = indicator_width if i % 5 == 0 else indicator_width * 0.7
            Line(points=[x - tick_width/2, tick_y, x + tick_width/2, tick_y], width=1)
            
            if i % 2 == 0:
                # Add altitude text
                alt_value = i * 20  # 0, 40, 80, etc.
                label = CoreLabel(text=f"{alt_value}m", font_size=10)
                label.refresh()
                texture = label.texture
                Rectangle(pos=(x + indicator_width/2 + 5, tick_y - texture.height/2), 
                          size=texture.size, texture=texture)
        
        # Current altitude marker - restored to orange
        marker_y = y - indicator_height/2 + (self.altitude / 200) * indicator_height
        Color(1, 0.5, 0, 0.9)  # Restored orange-yellow
        triangle_size = 8
        triangle_points = [
            x - indicator_width/2 - triangle_size, marker_y,  # Left
            x - indicator_width/2, marker_y + triangle_size/2,  # Top
            x - indicator_width/2, marker_y - triangle_size/2   # Bottom
        ]
        Triangle(points=triangle_points)
        
        # Altitude text at top
        Color(1, 1, 1, 0.9)
        label = CoreLabel(text="ALTITUDE", font_size=12)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(x - texture.width/2, y + indicator_height/2 + 5), 
                  size=texture.size, texture=texture)
        
        # Current altitude
        alt_text = f"{self.altitude}m"
        label = CoreLabel(text=alt_text, font_size=14)
        label.refresh()
        texture = label.texture
        Rectangle(pos=(x - texture.width/2, y - indicator_height/2 - 25), 
                  size=texture.size, texture=texture)

    def draw_data_visualization(self):
        # Data visualization bars along the edges
        Color(0, 0.7, 0.9, 0.4)
        
        # Left edge
        bar_width = 5
        bar_spacing = 10
        num_bars = min(len(self.data_points), 20)
        
        for i in range(num_bars):
            height = self.data_points[i] * 50
            x = 10 + i * (bar_width + bar_spacing)
            y = 120
            Rectangle(pos=(x, y), size=(bar_width, height))
            
        # Right edge
        for i in range(num_bars):
            height = self.data_points[(i+10) % len(self.data_points)] * 50
            x = self.width - 10 - (i+1) * (bar_width + bar_spacing)
            y = 120
            Rectangle(pos=(x, y), size=(bar_width, height))

class StarkHUDApp(App):
    def build(self):
        root = FloatLayout()
        hud = StarkHUDWidget()
        root.add_widget(hud)
        return root

if __name__ == '__main__':
    StarkHUDApp().run()