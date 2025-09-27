import streamlit as st
from ultralytics import YOLO
import cv2
import numpy as np
import yt_dlp
import time
import os
import sys
import subprocess
import tempfile # Added for local file handling

# --- Environment Setup for SUMO ---
sumo_home_path = None
if 'SUMO_HOME' in os.environ:
    sumo_home_path = os.environ['SUMO_HOME']
    st.sidebar.success(f"SUMO_HOME detected from environment: {sumo_home_path}")
else:
    # Hardcode SUMO_HOME path from the provided image for debugging
    sumo_home_path = r"C:\Program Files (x86)\Eclipse\Sumo"
    st.sidebar.warning(f"SUMO_HOME not found in environment, using hardcoded path: {sumo_home_path}")

if sumo_home_path:
    tools = os.path.join(sumo_home_path, 'tools')
    if tools not in sys.path:
        sys.path.append(tools)
    st.sidebar.success(f"SUMO tools path added to sys.path: {tools}")
else:
    st.error("SUMO_HOME path could not be determined. Please set it or ensure the hardcoded path is correct.")

try:
    import traci
    st.sidebar.success("TraCI imported successfully.")
except ImportError:
    st.sidebar.error("TraCI library not found. Please install it using: pip install traci")
    st.error("TraCI library not found. Please install it using: pip install traci")

# --- Constants ---
MIN_GREEN_TIME = 15
MAX_GREEN_TIME = 60
TIME_PER_VEHICLE = 2
YELLOW_TIME = 3
ALL_RED_TIME = 2
CONFIDENCE_THRESHOLD = 0.5
VEHICLE_CLASSES = ['car', 'motorcycle', 'bus', 'truck']

# --- Model Loading ---
@st.cache_resource
def load_model():
    model = YOLO('yolo11n-seg.pt')
    return model

# --- Helper Functions ---
def get_stream_url(yt_url):
    try:
        ydl_opts = {'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best', 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(yt_url, download=False)
            return info_dict.get('url', None)
    except Exception as e:
        st.sidebar.error(f"Error fetching URL {yt_url}: {e}")
        return None

def get_adaptive_font_params(frame_height):
    # Base font scale for a 720p height video
    base_font_scale = 1.0
    base_height = 720
    
    # Calculate font scale proportional to frame height
    font_scale = base_font_scale * (frame_height / base_height)
    
    # Calculate thickness proportional to font scale, with a minimum of 1
    thickness = max(1, int(font_scale * 2)) # Adjust multiplier as needed
    
    return font_scale, thickness

def draw_signal(image, state, border_thickness=10):
    if image is None: return None
    height, width, _ = image.shape
    color = {'Green': (0, 255, 0), 'Yellow': (0, 255, 255), 'Red': (0, 0, 255)}.get(state, (0, 0, 0))
    
    # Draw a rectangle border
    cv2.rectangle(image, (0, 0), (width, height), color, border_thickness)
    return image

def start_sumo():
    # Use the sumo_home_path determined globally
    global sumo_home_path
    if not sumo_home_path:
        st.error("SUMO_HOME path is not set. Cannot start SUMO.")
        return False
    
    # The traci import check is already handled at the top of the script
    # and will display an error in the sidebar if not found.
    # We only need to check if it's actually imported here.
    if 'traci' not in sys.modules:
        st.error("TraCI library is not available. Please ensure it's installed and SUMO_HOME is correctly configured.")
        return False
        
    sumo_binary = os.path.join(sumo_home_path, "bin", "sumo-gui.exe") # Specify full path to sumo-gui
    if not os.path.exists(sumo_binary):
        st.error(f"SUMO GUI executable not found at: {sumo_binary}. Please check your SUMO installation.")
        return False

    config_path = "intersection.sumocfg"
    if not os.path.exists(config_path):
        st.error(f"SUMO config file not found: {config_path}. Please ensure it's in the same directory as the script.")
        return False
        
    sumo_cmd = [sumo_binary, "-c", config_path, "--step-length", "1", "--remote-port", "8813"]
    try:
        # Ensure any previous TraCI connection is closed before initializing a new one
        if 'traci' in sys.modules and traci.is_connected(): # Corrected typo: is_connected()
            traci.close()
            st.sidebar.info("Closed existing TraCI connection.")

        subprocess.Popen(sumo_cmd)
        time.sleep(2) # Give SUMO GUI time to start
        traci.init(8813)
        return True
    except Exception as e:
        st.error(f"Failed to start SUMO or connect with TraCI: {e}. Ensure SUMO is correctly installed and configured and no other SUMO instances are running.")
        return False

# --- Main Simulation Functions ---

def run_youtube_simulation():
    st.sidebar.header("YouTube Stream Configuration")
    
    # Add confidence slider
    confidence = st.sidebar.slider(
        "Confidence Threshold", 0.0, 1.0, CONFIDENCE_THRESHOLD, 0.05
    )

    num_streams = st.sidebar.selectbox("Select Number of Junctions", [2, 3, 4], index=2, key="yt_streams")
    
    default_urls = [
        "https://www.youtube.com/watch?v=ScMMguS-KG4", "https://www.youtube.com/watch?v=2_S2p_L2gjs",
        "https://www.youtube.com/watch?v=MNs4w-F-Q2E", "https://www.youtube.com/watch?v=FijO0a5m3W8"
    ]
    urls = [st.sidebar.text_input(f"YouTube URL {i+1}", default_urls[i]) for i in range(num_streams)]

    start_button = st.sidebar.button("Start YouTube Simulation")
    stop_button = st.sidebar.button("Stop YouTube Simulation")

    # Initialize state
    if 'yt_running' not in st.session_state: st.session_state.yt_running = False
    if 'stop_processing' not in st.session_state: st.session_state.stop_processing = False

    # Add a slider for frame skipping to boost FPS
    frame_skip_interval = st.sidebar.slider(
        "Frame Skip Interval", 1, 10, 1, 1 # Min 1, Max 10, Default 1 (no skip), Step 1
    )

    if start_button:
        st.session_state.yt_running = True
        st.session_state.stop_processing = False # Reset stop flag
        st.rerun()

    if stop_button:
        st.session_state.yt_running = False
        st.session_state.stop_processing = True # Set stop flag
        st.info("YouTube simulation stopped.")
        st.rerun()

    if not st.session_state.yt_running:
        st.warning("YouTube simulation not running.")
        return

    model = load_model()
    
    # Create columns and placeholders once outside the loop
    cols = st.columns(num_streams)
    video_placeholders = [col.empty() for col in cols]
    subheader_placeholders = [col.empty() for col in cols]
    # Add placeholders for vehicle count and signal state
    vehicle_count_placeholders = [col.empty() for col in cols]
    signal_state_placeholders = [col.empty() for col in cols]

    caps = []
    stream_urls = []

    for i, url in enumerate(urls):
        stream_url = get_stream_url(url)
        if stream_url:
            stream_urls.append(stream_url)
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                st.error(f"Error: Could not open video stream from URL {url}")
                caps.append(None)
            else:
                caps.append(cap)
        else:
            caps.append(None)

    if not any(caps):
        st.error("No valid video streams could be opened. Stopping simulation.")
        st.session_state.yt_running = False
        st.session_state.stop_processing = True
        st.rerun()
        return

    st.info("YouTube simulation running...")

    # Initialize frame count for skipping
    if 'frame_count' not in st.session_state:
        st.session_state.frame_count = 0

    last_annotated_frames = [None] * num_streams # To hold the last processed frame for each stream

    while st.session_state.yt_running and not st.session_state.stop_processing:
        st.session_state.frame_count += 1
        frames_to_display = [None] * num_streams

        for i, cap in enumerate(caps):
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    st.warning(f"Stream {i+1} ended or error occurred. Re-fetching URL.")
                    cap.release()
                    stream_url = get_stream_url(urls[i])
                    if stream_url:
                        new_cap = cv2.VideoCapture(stream_url)
                        if new_cap.isOpened():
                            caps[i] = new_cap
                            ret, frame = new_cap.read()
                            if not ret:
                                continue # Skip this frame if re-fetch failed
                        else:
                            continue # Skip this frame if re-fetch failed
                    else:
                        continue # Skip this frame if re-fetch failed
                
                # Process frame only if it's time to skip
                if st.session_state.frame_count % frame_skip_interval == 0:
                    # Perform YOLO inference
                    results = model(frame, conf=confidence, classes=[0, 1, 2, 3, 5, 7]) # Car, motorcycle, bus, truck, bicycle, train
                    annotated_frame = results[0].plot()

                    # --- Vehicle Counting ---
                    vehicle_count = 0
                    # Assuming standard COCO dataset vehicle classes
                    vehicle_classes = ['car', 'motorcycle', 'bus', 'truck']
                    boxes = results[0].boxes
                    for box in boxes:
                        class_id = int(box.cls)
                        class_name = model.names[class_id]
                        if class_name in vehicle_classes:
                            vehicle_count += 1
                    
                    # Add vehicle count to the annotated frame
                    height, width, _ = annotated_frame.shape
                    font_scale, thickness = get_adaptive_font_params(height)
                    cv2.putText(annotated_frame, f"Vehicles: {vehicle_count}", (int(width * 0.05), int(height * 0.1)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
                    # --- End Vehicle Counting ---
                    last_annotated_frames[i] = annotated_frame # Update the last processed frame
                
                # Display the last processed frame or the original if no processing has happened yet
                if last_annotated_frames[i] is not None:
                    frames_to_display[i] = last_annotated_frames[i]
                else:
                    # If no frame has been processed yet, display the original frame
                    frames_to_display[i] = frame
            else:
                frames_to_display[i] = None

        for i, frame in enumerate(frames_to_display):
            subheader_placeholders[i].subheader(f"Stream {i+1}") # Update subheader in place
            if frame is not None:
                video_placeholders[i].image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
                # Update vehicle count and signal state in their respective placeholders
                vehicle_count_placeholders[i].write(f"Vehicles: {current_vehicle_counts[i]}")
                # For YouTube, there's no signal state, so we can just clear it or write a default
                signal_state_placeholders[i].write("Signal: N/A") 
            else:
                video_placeholders[i].write(f"Stream {i+1} not available.")
                vehicle_count_placeholders[i].empty()
                signal_state_placeholders[i].empty()
        
        time.sleep(0.01) # Small delay to prevent excessive CPU usage

    # Release all video capture objects when simulation stops
    for cap in caps:
        if cap:
            cap.release()
    st.info("YouTube simulation stopped.")


def run_sumo_simulation():
    st.sidebar.header("SUMO Configuration")
    start_button = st.sidebar.button("Start SUMO Simulation")
    stop_button = st.sidebar.button("Stop SUMO Simulation")

    if 'sumo_running' not in st.session_state: st.session_state.sumo_running = False
    if 'sumo_vehicle_counts' not in st.session_state: st.session_state.sumo_vehicle_counts = [0] * 4
    if 'sumo_signal_states' not in st.session_state: st.session_state.sumo_signal_states = ['Red'] * 4
    if 'sumo_active_phase' not in st.session_state: st.session_state.sumo_active_phase = -1
    if 'sumo_phase_end' not in st.session_state: st.session_state.sumo_phase_end = 0

    if start_button and not st.session_state.sumo_running:
        if start_sumo():
            st.session_state.sumo_running = True
            st.session_state.sumo_active_phase = -1
            st.session_state.sumo_phase_end = time.time() + ALL_RED_TIME
            st.session_state.sumo_signal_states = ['Red'] * 4
            st.rerun()

    if stop_button and st.session_state.sumo_running:
        st.session_state.sumo_running = False
        try:
            traci.close()
        except Exception as e:
            pass # Ignore error if connection is already closed
        st.info("SUMO simulation stopped.")
        st.rerun()

    if not st.session_state.sumo_running:
        st.warning("SUMO simulation not running.")
        return

    # Create columns and placeholders once outside the loop
    # Initialize or re-initialize placeholders if num_streams changes (though for SUMO it's fixed at 4)
    if 'sumo_image_placeholders' not in st.session_state or len(st.session_state.sumo_image_placeholders) != 4:
        cols = st.columns(4)
        st.session_state.sumo_image_placeholders = [col.empty() for col in cols]
        st.session_state.sumo_subheader_placeholders = [col.empty() for col in cols]
        st.session_state.sumo_vehicle_count_placeholders = [col.empty() for col in cols]
        st.session_state.sumo_signal_state_placeholders = [col.empty() for col in cols]
    
    image_placeholders = st.session_state.sumo_image_placeholders
    subheader_placeholders = st.session_state.sumo_subheader_placeholders
    vehicle_count_placeholders = st.session_state.sumo_vehicle_count_placeholders
    signal_state_placeholders = st.session_state.sumo_signal_state_placeholders

    # --- Main SUMO Loop ---
    try:
        if traci.simulation.getMinExpectedNumber() <= 0:
            st.success("SUMO simulation ended.")
            st.session_state.sumo_running = False
            traci.close()
            st.rerun()
            return

        traci.simulationStep()

        # Get vehicle counts from detectors
        detector_ids = ["det_W", "det_E", "det_N", "det_S"]
        for i, det_id in enumerate(detector_ids):
            st.session_state.sumo_vehicle_counts[i] = traci.inductionloop.getLastStepVehicleNumber(det_id)

        # Traffic light logic
        if time.time() >= st.session_state.sumo_phase_end:
            # ... (Your traffic light state machine logic here)
            # This is a simplified version
            current_phase = st.session_state.sumo_active_phase
            if current_phase != -1: st.session_state.sumo_signal_states[current_phase] = 'Red'
            next_phase = (current_phase + 1) % 4
            st.session_state.sumo_active_phase = next_phase
            st.session_state.sumo_signal_states[next_phase] = 'Green'
            green_time = MIN_GREEN_TIME + (st.session_state.sumo_vehicle_counts[next_phase] * TIME_PER_VEHICLE)
            green_time = min(green_time, MAX_GREEN_TIME) # Apply MAX_GREEN_TIME cap
            st.session_state.sumo_phase_end = time.time() + green_time
            
            # Map your state to SUMO's traffic light phase strings
            phase_map = ["GrrrGrrr", "rGrrrGrr", "rrGrrrGr", "rrrGrrrG"] # Simplified phases
            # A more realistic mapping is needed based on intersection.net.xml
            # traci.trafficlight.setRedYellowGreenState("J", new_phase_string)


        # Display visuals
        for i in range(4):
            subheader_placeholders[i].subheader(f"Camera {i+1}") # Update subheader in place
            traci.gui.switchView("View #0") # Correct view switching needed
            img_path = f"temp_view_{i}.png"
            traci.gui.screenshot("View #0", img_path, width=640, height=480)
            image = cv2.imread(img_path)
            
            # Apply border if this is the active green phase
            if i == st.session_state.sumo_active_phase:
                image = draw_signal(image, 'Green')
                
                # Calculate and display countdown timer
                remaining_time = max(0, int(st.session_state.sumo_phase_end - time.time()))
                height, width, _ = image.shape
                font_scale, thickness = get_adaptive_font_params(height)
                cv2.putText(image, f"Green: {remaining_time}s", (int(width * 0.02), int(height * 0.06)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)

            image_placeholders[i].image(image, channels="BGR")
            vehicle_count_placeholders[i].write(f"Vehicles: {st.session_state.sumo_vehicle_counts[i]}")
            signal_state_placeholders[i].write(f"Signal: {st.session_state.sumo_signal_states[i]}")

        st.rerun()

    except traci.TraCIException as e:
        st.error(f"TraCI connection lost: {e}. Stopping simulation.")
        st.session_state.sumo_running = False
        st.rerun()

# --- New Simulation Function for Local Files ---
def run_local_file_simulation():
    st.sidebar.header("Local File Configuration")

    confidence = st.sidebar.slider(
        "Confidence Threshold", 0.0, 1.0, CONFIDENCE_THRESHOLD, 0.05, key="local_conf"
    )

    num_streams = st.sidebar.selectbox("Select Number of Local Video Streams", [1, 2, 3, 4], index=0, key="local_streams_num")
    uploaded_files = [st.sidebar.file_uploader(f"Upload Local Video {i+1}", type=["mp4", "avi", "mov"], key=f"local_file_uploader_{i}") for i in range(num_streams)]

    start_button = st.sidebar.button("Start Local Simulation", key="start_local_sim")
    stop_button = st.sidebar.button("Stop Local Simulation", key="stop_local_sim")

    if 'local_running' not in st.session_state: st.session_state.local_running = False
    # Initialize state variables for local simulation
    if 'local_running' not in st.session_state: st.session_state.local_running = False
    # Initialize local_caps and local_temp_files to empty lists
    if 'local_caps' not in st.session_state: st.session_state.local_caps = []
    if 'local_temp_files' not in st.session_state: st.session_state.local_temp_files = []
    # Initialize other state variables based on the actual number of active streams
    if 'local_vehicle_counts' not in st.session_state: st.session_state.local_vehicle_counts = []
    if 'local_signal_states' not in st.session_state: st.session_state.local_signal_states = []
    if 'local_active_phase' not in st.session_state: st.session_state.local_active_phase = -1
    if 'local_phase_end' not in st.session_state: st.session_state.local_phase_end = 0

    if start_button:
        st.session_state.local_running = True
        st.session_state.local_active_phase = -1
        st.session_state.local_phase_end = time.time() + ALL_RED_TIME
        
        # Clear previous caps and temp files
        for cap in st.session_state.local_caps:
            if cap: cap.release()
        for tfile_name in st.session_state.local_temp_files:
            if tfile_name and os.path.exists(tfile_name): os.unlink(tfile_name)
        
        st.session_state.local_caps = [None] * num_streams
        st.session_state.local_temp_files = [None] * num_streams
        st.session_state.local_vehicle_counts = [0] * num_streams
        st.session_state.local_signal_states = ['Red'] * num_streams

        # Initialize video captures and temp files
        for i, uploaded_file in enumerate(uploaded_files):
            if uploaded_file is not None:
                tfile = tempfile.NamedTemporaryFile(delete=False)
                tfile.write(uploaded_file.read())
                st.session_state.local_temp_files[i] = tfile.name
                try:
                    cap = cv2.VideoCapture(tfile.name)
                    if not cap.isOpened():
                        st.error(f"Error: Could not open video file {uploaded_file.name} at {tfile.name}. Check file format and OpenCV codecs.")
                        st.session_state.local_caps[i] = None
                    else:
                        st.session_state.local_caps[i] = cap
                except Exception as e:
                    st.error(f"Exception opening video file {uploaded_file.name} at {tfile.name}: {e}")
                    st.session_state.local_caps[i] = None
            else:
                st.session_state.local_caps[i] = None
        st.rerun()

    if stop_button:
        st.session_state.local_running = False
        # Release all video capture objects and clean up temp files
        for i, cap in enumerate(st.session_state.local_caps):
            if cap:
                cap.release()
            if st.session_state.local_temp_files[i] and os.path.exists(st.session_state.local_temp_files[i]):
                os.unlink(st.session_state.local_temp_files[i])
        st.session_state.local_caps = []
        st.session_state.local_temp_files = []
        st.session_state.local_vehicle_counts = []
        st.session_state.local_signal_states = []
        st.info("Local simulation stopped.")
        st.rerun()

    if not st.session_state.local_running:
        st.warning("Local simulation not running. Please upload video files and click 'Start Local Simulation'.")
        return

    model = load_model()
    
    # Create columns and placeholders once outside the loop
    # Ensure the number of columns matches the actual number of active streams
    active_streams_count = len(st.session_state.local_caps)
    cols = st.columns(active_streams_count)
    video_placeholders = [col.empty() for col in cols]
    subheader_placeholders = [col.empty() for col in cols]
    # Add placeholders for vehicle count and signal state
    vehicle_count_placeholders = [col.empty() for col in cols]
    signal_state_placeholders = [col.empty() for col in cols]

    st.info("Local simulation running...")

    while st.session_state.local_running:
        # Use the actual number of active streams for array sizing
        current_active_streams = len(st.session_state.local_caps)
        frames_to_display = [None] * current_active_streams
        current_vehicle_counts = [0] * current_active_streams

        # Read frames and perform inference
        for i in range(current_active_streams):
            cap = st.session_state.local_caps[i]
            if cap and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    # Loop video if it ends
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret:
                        st.warning(f"Could not re-read video stream {i+1}. Skipping.")
                        frames_to_display[i] = None
                        continue

                results = model(frame, conf=confidence, classes=[0, 1, 2, 3, 5, 7])
                annotated_frame = results[0].plot()

                vehicle_count = 0
                boxes = results[0].boxes
                for box in boxes:
                    class_id = int(box.cls)
                    class_name = model.names[class_id]
                    if class_name in VEHICLE_CLASSES:
                        vehicle_count += 1
                
                current_vehicle_counts[i] = vehicle_count
                height, width, _ = annotated_frame.shape
                font_scale, thickness = get_adaptive_font_params(height)
                cv2.putText(annotated_frame, f"Vehicles: {vehicle_count}", (int(width * 0.05), int(height * 0.1)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)
                frames_to_display[i] = annotated_frame
            else:
                frames_to_display[i] = None
        
        st.session_state.local_vehicle_counts = current_vehicle_counts

        # Traffic light logic for local videos
        if time.time() >= st.session_state.local_phase_end:
            current_phase = st.session_state.local_active_phase
            if current_phase != -1:
                # Ensure index is within bounds of current_active_streams
                if current_phase < current_active_streams:
                    st.session_state.local_signal_states[current_phase] = 'Red'
            
            # Only proceed if there are active streams to manage
            if current_active_streams > 0:
                next_phase = (current_phase + 1) % current_active_streams
                st.session_state.local_active_phase = next_phase
                
                # Ensure local_signal_states is correctly sized before assignment
                if len(st.session_state.local_signal_states) != current_active_streams:
                    st.session_state.local_signal_states = ['Red'] * current_active_streams
                st.session_state.local_signal_states[next_phase] = 'Green'
                
                # Ensure local_vehicle_counts is correctly sized before access
                if len(st.session_state.local_vehicle_counts) != current_active_streams:
                    st.session_state.local_vehicle_counts = [0] * current_active_streams
                
                green_time = MIN_GREEN_TIME + (st.session_state.local_vehicle_counts[next_phase] * TIME_PER_VEHICLE)
                green_time = min(green_time, MAX_GREEN_TIME)
                st.session_state.local_phase_end = time.time() + green_time
            else:
                # No active streams, reset phase
                st.session_state.local_active_phase = -1
                st.session_state.local_phase_end = 0
                st.session_state.local_signal_states = []


        # Display visuals
        for i in range(current_active_streams): # Iterate based on current_active_streams
            col = cols[i] # Access the correct column
            with col:
                subheader_placeholders[i].subheader(f"Local Stream {i+1}") # Update subheader in place
                frame = frames_to_display[i]
                if frame is not None:
                    # Apply border if this is the active green phase
                    if i == st.session_state.local_active_phase:
                        frame = draw_signal(frame, 'Green')
                        
                        # Calculate and display countdown timer
                        remaining_time = max(0, int(st.session_state.local_phase_end - time.time()))
                        height, width, _ = frame.shape
                        font_scale, thickness = get_adaptive_font_params(height)
                        cv2.putText(frame, f"Green: {remaining_time}s", (int(width * 0.02), int(height * 0.06)), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 255, 0), thickness, cv2.LINE_AA)

                    video_placeholders[i].image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
                else:
                    video_placeholders[i].write(f"Local Stream {i+1} not available.")
                # Update vehicle count and signal state in their respective placeholders
                # Ensure indices are within bounds
                if i < len(st.session_state.local_vehicle_counts):
                    vehicle_count_placeholders[i].write(f"Vehicles: {st.session_state.local_vehicle_counts[i]}")
                else:
                    vehicle_count_placeholders[i].empty()
                
                if i < len(st.session_state.local_signal_states):
                    signal_state_placeholders[i].write(f"Signal: {st.session_state.local_signal_states[i]}")
                else:
                    signal_state_placeholders[i].empty()
        
        time.sleep(0.01) # Small delay to prevent excessive CPU usage

if __name__ == "__main__":
    st.set_page_config(page_title="AI Traffic Manager", layout="wide")
    st.title("🚦 AI Traffic Manager")

    sim_mode = st.sidebar.radio("Select Simulation Source", ("YouTube Simulation", "SUMO Simulation", "Local File Simulation"), key="sim_mode_radio")

    if sim_mode == "YouTube Simulation":
        st.header("YouTube Simulation Mode")
        run_youtube_simulation()
    
    elif sim_mode == "SUMO Simulation":
        st.header("SUMO Simulation Mode")
        run_sumo_simulation()
    
    elif sim_mode == "Local File Simulation":
        st.header("Local File Simulation Mode")
        run_local_file_simulation()
