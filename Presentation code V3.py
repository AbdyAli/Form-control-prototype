# Setup and import modules
import os
import time
import tkinter as tk
from threading import Thread
import cv2
import numpy as np
import mediapipe as mp
from picamera2 import Picamera2

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Finger data
# Assigns specific landmarks finger names corresponding to that finger for readability
fingertip_ids = [4, 8, 12, 16, 20]
finger_names = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
sequence = list(range(5)) + list(reversed(range(1, 5)))

# Global camera reference
global_picam = None

# Creates UI window and frames
# GUI Setup
root = tk.Tk()
root.title("Form Control")
root.attributes('-fullscreen', True)
root.configure(bg="black")
# Create Frames
main_frame = tk.Frame(root, bg="black")
settings_frame = tk.Frame(root, bg="black")
timer_frame = tk.Frame(root, bg="black")

#Loops over the frames
for frame in (main_frame, settings_frame, timer_frame):
    frame.place(relwidth=1, relheight=1)

# Function pulls the current frame to the front
def show_frame(frame):
    frame.tkraise()

# Safe camera closing
def safe_close_camera():
    global global_picam
    try:
        if global_picam:
            global_picam.close()
            global_picam = None
    except:
        pass

# Start Exercise
def start_exercise():
    def run():
        
        # Closes any actiev picam windows
        global global_picam
        safe_close_camera()

 # State for stepping and debouncing
        # Index into sequence
        current_step = 0            
        # Require release before next tap
        waiting_for_tap = True      
        # Timestamp for debounce
        last_tap_time = 0           


        # Camera configure/start
        # Preview is used over a baked in window due to software issues
        global_picam = Picamera2()
        global_picam.preview_configuration.main.size = (640, 480)
        global_picam.preview_configuration.main.format = "RGB888"
        global_picam.preview_configuration.align()
        global_picam.configure("preview")
        global_picam.start()


        # MediaPipe Hands setup
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        while True:
            # Mirrors frame it so onscreen movement feels natural
            frame = cv2.flip(global_picam.capture_array(), 1)  
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame_rgb)

            h, w, _ = frame.shape


            # Provides the prompt text for the current step
            # Loops through the sequence using all fingers for the example exercise
            if current_step < len(sequence):
                finger_name = finger_names[sequence[current_step]]
                instruction = f"Tap your {finger_name} finger to its base"
                cv2.putText(frame, instruction, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 3)
            else:
                # Displays all steps done and breaks out of the loop
                cv2.putText(frame, "Exercise Complete!", (80, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 200, 255), 3)
                break

            # If a hand is detected by camera, draws landmarks and test for a tap
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    landmarks = hand_landmarks.landmark
                    base_map = {4: 2, 8: 5, 12: 9, 16: 13, 20: 17}
                    
                    # Sets the values to the active fingertip for this step and its base joint
                    finger_id = fingertip_ids[sequence[current_step]] if current_step < len(sequence) else 0
                    tip = landmarks[finger_id]
                    base = landmarks[base_map[finger_id]]

                    # Uses Euclidean distance (I have no idea if this actually works or not, just rolling with it)
                    dist = np.sqrt((tip.x - base.x) ** 2 + (tip.y - base.y) ** 2)
                    tapped = dist < 0.08 

                    # Debouncees, require user to untap finger to transition before next step
                    if tapped:
                        if waiting_for_tap:
                            print(f"{finger_name} tap detected!")
                            current_step += 1
                            waiting_for_tap = False
                            last_tap_time = time.time()
                    else:
                        if time.time() - last_tap_time > 0.5:
                            waiting_for_tap = True

            # Show the annotated stream 
            cv2.imshow("Finger Tap Routine", frame)
            # Quits with 'Q' press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Cleanup in case of bugs
        safe_close_camera()
        cv2.destroyAllWindows()

    Thread(target=run).start()

# Preview Mode
def start_preview():
    def run():
        global global_picam
        safe_close_camera()

        # Sets up camera config
        global_picam = Picamera2()
        global_picam.preview_configuration.main.size = (640, 480)
        global_picam.preview_configuration.main.format = "RGB888"
        global_picam.preview_configuration.align()
        global_picam.configure("preview")
        global_picam.start()

        # Sets up Mediapipe config
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        hands = mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)

        # Displays a preview of the cameras vision
        while True:
            frame = cv2.flip(global_picam.capture_array(), 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = hands.process(frame_rgb)

            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            cv2.imshow("Camera Preview", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        # Cleanup in case of bugs
        safe_close_camera()
        cv2.destroyAllWindows()

    Thread(target=run).start()

# Timer displays onscreen timer for 5 seconds
def run_circular_timer(duration_seconds=5):
    show_frame(timer_frame)

    # Full-bleed canvas on the timer screen
    canvas = tk.Canvas(timer_frame, bg="black", highlightthickness=0)
    canvas.pack(expand=True, fill='both')

    # Draws an arc that sweeps clockwise as time elapses
    arc = canvas.create_arc(300, 100, 700, 500, start=90, extent=0,
                            width=20, outline='#6699ff', style='arc')

    # displays digital time in the center (MM:SS)
    time_text = canvas.create_text(500, 300, text="", fill="white", font=("Helvetica", 48))

    def update_timer(seconds_left):
        angle = (duration_seconds - seconds_left) / duration_seconds * 360
        canvas.itemconfig(arc, extent=-angle)
        m, s = divmod(seconds_left, 60)
        canvas.itemconfig(time_text, text=f"{m}:{s:02d}")

        if seconds_left > 0:
            root.after(1000, lambda: update_timer(seconds_left - 1))
        else:
            # lCears canvas and begins exercise
            canvas.delete("all")
            start_exercise()

    update_timer(duration_seconds)

# Function to start timer
def start_timer():
    Thread(target=run_circular_timer).start()

# Function to start the preview
def launch_preview():
    start_preview()

# Main Menu
# Simple logo to resemble the branding concept
logo_canvas = tk.Canvas(main_frame, width=250, height=250, bg="black", highlightthickness=0)
logo_canvas.pack(pady=20)
logo_canvas.create_rectangle(50, 30, 90, 220, fill="white", outline="white")
logo_canvas.create_rectangle(90, 30, 180, 70, fill="white", outline="white")
logo_canvas.create_rectangle(90, 110, 150, 150, fill="white", outline="white")

# Text segments identifying the buttons and thier purposes
title_label = tk.Label(main_frame, text="FORM CONTROL", font=("Helvetica", 30), bg="black", fg="white")
title_label.pack(pady=10)

button_frame = tk.Frame(main_frame, bg="black")
button_frame.pack(pady=40)

start_btn = tk.Button(button_frame, text="Start Timer", font=("Helvetica", 20), command=start_timer, width=15)
start_btn.grid(row=0, column=0, padx=20)

settings_btn = tk.Button(button_frame, text="Settings", font=("Helvetica", 20), command=lambda: show_frame(settings_frame), width=15)
settings_btn.grid(row=0, column=1, padx=20)

preview_btn = tk.Button(button_frame, text="Preview", font=("Helvetica", 20), command=launch_preview, width=32)
preview_btn.grid(row=1, column=0, columnspan=2, pady=20)

# Settings
tk.Label(settings_frame, text="Settings", font=("Helvetica", 40), bg="black", fg="white").pack(pady=50)
tk.Button(settings_frame, text="Return", font=("Helvetica", 20), command=lambda: show_frame(main_frame)).pack()

# Exit on Esc
root.bind('<Escape>', lambda e: root.destroy())

# Launch
show_frame(main_frame)
root.mainloop()
