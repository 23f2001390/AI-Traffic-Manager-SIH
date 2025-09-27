# 🚦 AI Traffic Manager

An intelligent traffic management system that combines YOLO object detection with real-time traffic simulation. This Streamlit application can process video streams from multiple sources to detect vehicles and optimize traffic light timing.

## 🌟 Features

### Core Functionality
- **Multi-Source Video Processing**: Handle YouTube streams, local video files, and SUMO simulation
- **Real-time Vehicle Detection**: Uses YOLO11n-seg model to detect cars, motorcycles, buses, and trucks
- **Intelligent Traffic Light Control**: Dynamic signal timing based on vehicle count and density
- **Adaptive UI**: Responsive font scaling and display optimization for different video resolutions

### Simulation Modes
1. **YouTube Simulation**: Process live YouTube video streams for real-time traffic analysis
2. **SUMO Integration**: Connect with SUMO traffic simulator for comprehensive urban mobility simulation
3. **Local File Processing**: Analyze uploaded video files with vehicle detection and traffic management

### Advanced Features
- **Frame Skip Optimization**: Configurable frame skipping to improve performance
- **Confidence Threshold Control**: Adjustable detection sensitivity
- **Multi-Junction Support**: Handle up to 4 simultaneous video streams
- **Real-time Metrics**: Live vehicle counting and signal state monitoring
- **Visual Signal Indicators**: Color-coded borders and countdown timers

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- SUMO (Simulation of Urban MObility) installed
- Webcam or video files for testing

### Required Python Packages
```bash
pip install streamlit
pip install ultralytics
pip install opencv-python
pip install yt-dlp
pip install traci
```

### SUMO Setup
1. Download and install SUMO from [sumo.dlr.de](https://sumo.dlr.de)
2. Set the `SUMO_HOME` environment variable to your SUMO installation path
3. Ensure SUMO binaries are in your system PATH

### YOLO Model
The application uses `yolo11n-seg.pt` by default. Make sure this model file is present in the working directory or update the model path in the code.

## 🚀 Usage

### Running the Application
```bash
streamlit run "yolo1 copy 3.py"
```

### Configuration Files
- `intersection.sumocfg`: SUMO simulation configuration
- `intersection.net.xml`: Road network definition
- `intersection.rou.xml`: Vehicle routes and flow definitions

### Simulation Modes

#### 1. YouTube Simulation
- Select "YouTube Simulation" from the sidebar
- Enter YouTube URLs for traffic camera feeds
- Adjust confidence threshold and frame skip interval
- Click "Start YouTube Simulation" to begin processing

#### 2. SUMO Simulation
- Select "SUMO Simulation" from the sidebar
- Ensure SUMO is properly configured and running
- Click "Start SUMO Simulation" to begin the simulation
- View real-time traffic light states and vehicle counts

#### 3. Local File Simulation
- Select "Local File Simulation" from the sidebar
- Upload MP4, AVI, or MOV video files
- Configure number of streams and detection parameters
- Click "Start Local Simulation" to process uploaded videos

## ⚙️ Configuration

### Traffic Light Parameters
- **MIN_GREEN_TIME**: Minimum green light duration (15 seconds)
- **MAX_GREEN_TIME**: Maximum green light duration (60 seconds)
- **TIME_PER_VEHICLE**: Additional time per detected vehicle (2 seconds)
- **YELLOW_TIME**: Yellow light duration (3 seconds)
- **ALL_RED_TIME**: All-red clearance time (2 seconds)

### Detection Parameters
- **CONFIDENCE_THRESHOLD**: Default detection confidence (0.5)
- **VEHICLE_CLASSES**: Supported vehicle types: car, motorcycle, bus, truck

### Performance Optimization
- **Frame Skip Interval**: Skip frames to improve performance (1-10)
- **Adaptive Font Scaling**: Automatic text size adjustment based on video resolution

## 📊 Output Features

### Real-time Information Display
- **Vehicle Count**: Live count of detected vehicles per stream
- **Signal State**: Current traffic light status (Red/Yellow/Green)
- **Green Time Remaining**: Countdown timer for active green phases
- **Visual Indicators**: Color-coded borders around active signal phases

### Multi-Stream Support
- Support for 2-4 simultaneous video streams
- Individual vehicle counting per junction
- Independent traffic light control per intersection
- Synchronized display with real-time updates

## 🔧 Troubleshooting

### Common Issues

**SUMO Connection Issues:**
- Ensure `SUMO_HOME` environment variable is set correctly
- Check that SUMO binaries are in system PATH
- Verify `intersection.sumocfg` file exists and is properly configured

**Video Stream Issues:**
- Check internet connection for YouTube streams
- Ensure video files are in supported formats (MP4, AVI, MOV)
- Verify OpenCV codecs are installed for local video processing

**YOLO Detection Issues:**
- Ensure `yolo11n-seg.pt` model file is present
- Check GPU availability for faster processing
- Adjust confidence threshold if detection is too sensitive/restrictive

**Performance Issues:**
- Increase frame skip interval to reduce processing load
- Reduce number of simultaneous streams
- Lower video resolution if processing is too slow

## 📁 Project Structure

```
SIH/
├── yolo1 copy 3.py          # Main application file
├── intersection.sumocfg     # SUMO configuration
├── intersection.net.xml     # Road network definition
├── intersection.rou.xml     # Vehicle routes
├── yolo11n-seg.pt          # YOLO segmentation model
├── README.md               # This file
└── output/                 # Processed video outputs
```

## 🔬 Technical Details

### Architecture
- **Frontend**: Streamlit web interface
- **Computer Vision**: OpenCV + YOLO11n-seg
- **Traffic Simulation**: SUMO with TraCI interface
- **Video Processing**: Multi-threaded stream handling

### Key Components
- **Vehicle Detection**: YOLO deep learning model for object detection
- **Traffic State Management**: Dynamic signal timing algorithm
- **Multi-source Integration**: Unified interface for different video sources
- **Real-time Processing**: Optimized frame processing pipeline

### Dependencies
- Streamlit: Web application framework
- Ultralytics YOLO: Object detection and segmentation
- OpenCV: Computer vision and image processing
- yt-dlp: YouTube video stream extraction
- TraCI: SUMO traffic control interface

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with different video sources
5. Submit a pull request

## 📄 License

This project is part of SIH 2025 (Smart India Hackathon) and follows the contest guidelines and regulations.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section above
2. Verify all dependencies are properly installed
3. Ensure SUMO is correctly configured
4. Test with sample video files before using live streams

## 🎯 Future Enhancements

- [ ] Integration with live traffic cameras
- [ ] Machine learning-based traffic prediction
- [ ] Multi-city traffic coordination
- [ ] Advanced vehicle classification
- [ ] Emergency vehicle detection and prioritization
- [ ] Historical traffic pattern analysis
- [ ] Integration with smart city infrastructure

---

**Note**: This application requires proper configuration of SUMO and YOLO model files. Ensure all dependencies are installed and paths are correctly set before running the simulation.
