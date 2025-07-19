#!/usr/bin/env python3
"""
Dual Target Power Pulse Tester
Two moveable and resizable circles that pulse based on independent power targets
Real-time CPU priority for maximum precision
"""

import tkinter as tk
from tkinter import ttk
import time
import threading
import os
import sys
import math

# Try to set real-time priority
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

def set_realtime_priority():
    """Set the process to real-time priority"""
    try:
        # Set process priority to real-time/highest
        if HAS_PSUTIL:
            # Use psutil for cross-platform priority setting
            process = psutil.Process(os.getpid())
            if sys.platform == "win32":
                process.nice(psutil.REALTIME_PRIORITY_CLASS)
            else:
                process.nice(-20)  # Highest priority on Unix
            print("✓ Set process to real-time priority")
        else:
            # Fallback to os.nice() on Unix systems
            if hasattr(os, 'nice'):
                os.nice(-20)  # Highest priority
                print("✓ Set process to high priority")
            
        # Try to set real-time scheduling policy on Linux
        if sys.platform.startswith('linux'):
            try:
                import sched
                # This requires root privileges
                os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(99))
                print("✓ Set real-time FIFO scheduling")
            except (AttributeError, OSError, PermissionError):
                print("⚠ Real-time scheduling requires root privileges")
                
    except (PermissionError, OSError) as e:
        print(f"⚠ Could not set real-time priority: {e}")
        print("  Run as administrator/root for best timing precision")
    except Exception as e:
        print(f"⚠ Priority setting failed: {e}")

# Set real-time priority immediately
set_realtime_priority()

class MovableCircle:
    def __init__(self, canvas, x, y, radius, color, label):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.radius = radius
        self.color = color
        self.label = label
        self.is_pulsing = False
        
        # Create circle
        self.circle_id = self.canvas.create_oval(
            x - radius, y - radius, x + radius, y + radius,
            fill='black', outline=color, width=2
        )
        
        # Create label
        self.text_id = self.canvas.create_text(
            x, y, text=label, fill='white', font=('Arial', 12, 'bold')
        )
        
        # Mouse interaction state
        self.dragging = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_mode = False
        
        # Bind mouse events
        self.canvas.tag_bind(self.circle_id, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.circle_id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.circle_id, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.circle_id, "<Button-3>", self.on_right_click)  # Right click for resize
        self.canvas.tag_bind(self.circle_id, "<B3-Motion>", self.on_resize)
        
        self.canvas.tag_bind(self.text_id, "<Button-1>", self.on_click)
        self.canvas.tag_bind(self.text_id, "<B1-Motion>", self.on_drag)
        self.canvas.tag_bind(self.text_id, "<ButtonRelease-1>", self.on_release)
        self.canvas.tag_bind(self.text_id, "<Button-3>", self.on_right_click)
        self.canvas.tag_bind(self.text_id, "<B3-Motion>", self.on_resize)
    
    def on_click(self, event):
        self.dragging = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_right_click(self, event):
        self.resize_mode = True
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_drag(self, event):
        if self.dragging:
            dx = event.x - self.drag_start_x
            dy = event.y - self.drag_start_y
            
            self.x += dx
            self.y += dy
            
            # Move circle and text
            self.canvas.move(self.circle_id, dx, dy)
            self.canvas.move(self.text_id, dx, dy)
            
            self.drag_start_x = event.x
            self.drag_start_y = event.y
    
    def on_resize(self, event):
        if self.resize_mode:
            # Calculate distance from center to mouse
            dx = event.x - self.x
            dy = event.y - self.y
            new_radius = max(10, math.sqrt(dx*dx + dy*dy))
            
            if abs(new_radius - self.radius) > 2:  # Only update if significant change
                self.radius = new_radius
                
                # Update circle
                self.canvas.coords(
                    self.circle_id,
                    self.x - self.radius, self.y - self.radius,
                    self.x + self.radius, self.y + self.radius
                )
    
    def on_release(self, event):
        self.dragging = False
        self.resize_mode = False
    
    def pulse(self, duration_ms=50):
        """Make the circle pulse fully white briefly"""
        if not self.is_pulsing:
            self.is_pulsing = True
            
            # Flash full white fill
            self.canvas.itemconfig(self.circle_id, fill='white')
            
            # Return to black fill after specified duration
            self.canvas.after(duration_ms, lambda: self._return_to_black())
    
    def _return_to_black(self):
        self.canvas.itemconfig(self.circle_id, fill='black')
        self.is_pulsing = False

class DualPulseTester:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Dual Target Power Pulse Tester")
        self.root.geometry("1000x700")
        self.root.configure(bg='black')
        
        # Constants
        self.PULSE_DURATION_MS = 10  # milliseconds
        self.PULSE_ENERGY_WH = 1     # Wh per pulse (1000 imp/kWh)
        self.JOULES_PER_WH = 3600    # J/Wh
        
        # Variables for two targets
        self.target_watts_1 = 2000
        self.target_watts_2 = 5000
        self.running = False
        self.pulse_thread = None
        
        # Pulse timing
        self.next_pulse_time_1 = 0
        self.next_pulse_time_2 = 0
        self.pulse_count_1 = 0
        self.pulse_count_2 = 0
        self.start_time = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Control frame
        control_frame = tk.Frame(self.root, bg='black')
        control_frame.pack(pady=10)
        
        # Target 1 controls
        target1_frame = tk.Frame(control_frame, bg='black')
        target1_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(target1_frame, text="Target 1 Power:", 
                fg='red', bg='black', font=('Arial', 12, 'bold')).pack()
        
        self.power_var_1 = tk.StringVar(value=str(self.target_watts_1))
        self.power_entry_1 = tk.Entry(target1_frame, textvariable=self.power_var_1, 
                                     width=10, font=('Arial', 12))
        self.power_entry_1.pack(pady=5)
        self.power_entry_1.bind('<Return>', self.update_power_1)
        
        tk.Label(target1_frame, text="W", 
                fg='red', bg='black', font=('Arial', 12)).pack()
        
        # Target 2 controls
        target2_frame = tk.Frame(control_frame, bg='black')
        target2_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(target2_frame, text="Target 2 Power:", 
                fg='blue', bg='black', font=('Arial', 12, 'bold')).pack()
        
        self.power_var_2 = tk.StringVar(value=str(self.target_watts_2))
        self.power_entry_2 = tk.Entry(target2_frame, textvariable=self.power_var_2, 
                                     width=10, font=('Arial', 12))
        self.power_entry_2.pack(pady=5)
        self.power_entry_2.bind('<Return>', self.update_power_2)
        
        tk.Label(target2_frame, text="W", 
                fg='blue', bg='black', font=('Arial', 12)).pack()
        
        # Pulse width controls
        pulse_width_frame = tk.Frame(control_frame, bg='black')
        pulse_width_frame.pack(side=tk.LEFT, padx=20)
        
        tk.Label(pulse_width_frame, text="Pulse Width:", 
                fg='white', bg='black', font=('Arial', 12, 'bold')).pack()
        
        self.pulse_width_var = tk.StringVar(value=str(self.PULSE_DURATION_MS))
        self.pulse_width_entry = tk.Entry(pulse_width_frame, textvariable=self.pulse_width_var, 
                                         width=8, font=('Arial', 12))
        self.pulse_width_entry.pack(pady=5)
        self.pulse_width_entry.bind('<Return>', self.update_pulse_width)
        
        tk.Label(pulse_width_frame, text="ms", 
                fg='white', bg='black', font=('Arial', 12)).pack()
        
        # Control buttons
        button_frame = tk.Frame(control_frame, bg='black')
        button_frame.pack(side=tk.LEFT, padx=20)
        
        self.start_button = tk.Button(button_frame, text="Start", 
                                     command=self.start_pulsing, 
                                     font=('Arial', 12), width=10)
        self.start_button.pack(pady=2)
        
        self.stop_button = tk.Button(button_frame, text="Stop", 
                                    command=self.stop_pulsing, 
                                    font=('Arial', 12), width=10)
        self.stop_button.pack(pady=2)
        
        # Instructions
        instructions = tk.Label(self.root, 
                               text="Left click + drag to move circles • Right click + drag to resize circles", 
                               fg='white', bg='black', font=('Arial', 10))
        instructions.pack(pady=5)
        
        # Canvas for circles
        self.canvas = tk.Canvas(self.root, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create movable circles
        self.circle_1 = MovableCircle(self.canvas, 200, 200, 50, 'red', 'Target 1')
        self.circle_2 = MovableCircle(self.canvas, 400, 200, 70, 'blue', 'Target 2')
        
        # Status displays
        status_frame = tk.Frame(self.root, bg='black')
        status_frame.pack(pady=10)
        
        self.status_label_1 = tk.Label(status_frame, text="Target 1: Ready", 
                                      fg='red', bg='black', font=('Arial', 10))
        self.status_label_1.pack(side=tk.LEFT, padx=20)
        
        self.status_label_2 = tk.Label(status_frame, text="Target 2: Ready", 
                                      fg='blue', bg='black', font=('Arial', 10))
        self.status_label_2.pack(side=tk.LEFT, padx=20)
        
        # Pulse rate displays
        rate_frame = tk.Frame(self.root, bg='black')
        rate_frame.pack(pady=5)
        
        self.rate_label_1 = tk.Label(rate_frame, text="Rate 1: -- pulses/min", 
                                    fg='red', bg='black', font=('Arial', 10))
        self.rate_label_1.pack(side=tk.LEFT, padx=20)
        
        self.rate_label_2 = tk.Label(rate_frame, text="Rate 2: -- pulses/min", 
                                    fg='blue', bg='black', font=('Arial', 10))
        self.rate_label_2.pack(side=tk.LEFT, padx=20)
        
    def calculate_interval_ms(self, watts):
        """Calculate interval between pulses in milliseconds"""
        return (self.JOULES_PER_WH * 1000) / watts
        
    def update_power_1(self, event=None):
        """Update target power 1 from input field"""
        try:
            new_watts = float(self.power_var_1.get())
            if new_watts > 0:
                self.target_watts_1 = new_watts
                self.status_label_1.config(text=f"Target 1: {self.target_watts_1}W")
        except ValueError:
            pass
            
    def update_power_2(self, event=None):
        """Update target power 2 from input field"""
        try:
            new_watts = float(self.power_var_2.get())
            if new_watts > 0:
                self.target_watts_2 = new_watts
                self.status_label_2.config(text=f"Target 2: {self.target_watts_2}W")
        except ValueError:
            pass
            
    def update_pulse_width(self, event=None):
        """Update pulse width from input field"""
        try:
            new_width = int(self.pulse_width_var.get())
            if 1 <= new_width <= 1000:  # Reasonable range 1ms to 1000ms
                self.PULSE_DURATION_MS = new_width
        except ValueError:
            pass
            
    def pulse_thread_func(self):
        """Main pulsing thread - runs with precise timing for both targets"""
        current_time = time.time()
        self.next_pulse_time_1 = current_time
        self.next_pulse_time_2 = current_time
        self.start_time = current_time
        self.pulse_count_1 = 0
        self.pulse_count_2 = 0
        
        while self.running:
            current_time = time.time()
            
            # Handle Target 1 pulses
            if current_time >= self.next_pulse_time_1:
                self.root.after(0, lambda: self.circle_1.pulse(self.PULSE_DURATION_MS))
                
                interval_s = self.calculate_interval_ms(self.target_watts_1) / 1000.0
                self.next_pulse_time_1 += interval_s
                
                # Catch up if we've fallen behind
                if current_time > self.next_pulse_time_1 + interval_s:
                    self.next_pulse_time_1 = current_time + interval_s
                
                self.pulse_count_1 += 1
            
            # Handle Target 2 pulses
            if current_time >= self.next_pulse_time_2:
                self.root.after(0, lambda: self.circle_2.pulse(self.PULSE_DURATION_MS))
                
                interval_s = self.calculate_interval_ms(self.target_watts_2) / 1000.0
                self.next_pulse_time_2 += interval_s
                
                # Catch up if we've fallen behind
                if current_time > self.next_pulse_time_2 + interval_s:
                    self.next_pulse_time_2 = current_time + interval_s
                
                self.pulse_count_2 += 1
            
            # Update pulse rates
            elapsed_time = current_time - self.start_time
            if elapsed_time > 1.0:  # Update every second
                rate_1 = (self.pulse_count_1 / elapsed_time) * 60
                rate_2 = (self.pulse_count_2 / elapsed_time) * 60
                
                self.root.after(0, lambda r1=rate_1, r2=rate_2: self.update_rates(r1, r2))
            
            # Sleep for a short time to avoid busy waiting
            time.sleep(0.001)  # 1ms sleep
            
    def update_rates(self, rate_1, rate_2):
        """Update the rate display labels"""
        self.rate_label_1.config(text=f"Rate 1: {rate_1:.1f} pulses/min")
        self.rate_label_2.config(text=f"Rate 2: {rate_2:.1f} pulses/min")
            
    def start_pulsing(self):
        """Start the pulse generation for both targets"""
        if not self.running:
            self.update_power_1()
            self.update_power_2()
            self.running = True
            self.pulse_thread = threading.Thread(target=self.pulse_thread_func)
            self.pulse_thread.daemon = True
            self.pulse_thread.start()
            
            self.start_button.config(state='disabled')
            self.stop_button.config(state='normal')
            self.status_label_1.config(text=f"Target 1: Pulsing at {self.target_watts_1}W")
            self.status_label_2.config(text=f"Target 2: Pulsing at {self.target_watts_2}W")
            
    def stop_pulsing(self):
        """Stop the pulse generation"""
        self.running = False
        if self.pulse_thread and self.pulse_thread.is_alive():
            self.pulse_thread.join(timeout=1.0)
            
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label_1.config(text="Target 1: Stopped")
        self.status_label_2.config(text="Target 2: Stopped")
        self.rate_label_1.config(text="Rate 1: -- pulses/min")
        self.rate_label_2.config(text="Rate 2: -- pulses/min")
        
    def run(self):
        """Start the GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()
        
    def on_closing(self):
        """Handle window closing"""
        self.stop_pulsing()
        self.root.destroy()

if __name__ == "__main__":
    app = DualPulseTester()
    app.run() 