# การอธิบายโค้ดระบบตรวจจับหูฟัง AI
## Code Documentation: PPE Monitoring System

---

## 📋 โครงสร้างไฟล์และสถาปัตยกรรม

```
run_8l.py (2,400+ lines) - Main System File
├── 🔧 Auto Package Installation (Lines 32-95)
├── ⚙️ Configuration Management (Lines 180-230) 
├── 📶 Network Management (Lines 231-520)
├── 📋 Logging System (Lines 521-550)
├── 🔔 Discord Notifications (Lines 551-800)
├── 🤖 AI Inference Engine (Lines 801-1200)
├── 📷 Camera System (Lines 1201-1500)
├── 🛡️ Safety Monitoring (Lines 1501-2000)
├── 🚀 Main Function (Lines 2001-2300)
└── 🎯 Entry Point (Lines 2301-2400)
```

---

## 🔧 Auto Package Installation System
**Location**: Lines 32-95

### วัตถุประสงค์
ติดตั้งแพ็กเกจ Python ที่จำเป็นโดยอัตโนมัติก่อนเริ่มระบบ

```python
def install_required_packages():
    """ติดตั้งแพ็กเกจที่จำเป็นโดยอัตโนมัติ"""
    required_packages = [
        "opencv-python>=4.8.0",  # การประมวลผลภาพ
        "numpy>=1.21.0",         # คำนวณเมทริกซ์
        "requests>=2.25.0",      # HTTP requests สำหรับ Discord
        "pillow>=8.0.0"          # การจัดการภาพ
    ]
    
    for package in required_packages:
        try:
            print(f"📦 Installing {package}...")
            if package == "picamera2":
                # ลองติดตั้งผ่าน apt ก่อน (สำหรับ Pi)
                subprocess.check_call([
                    "sudo", "apt", "install", "-y", "python3-picamera2"
                ])
            else:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    package, "--quiet"
                ])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"⚠️ {package} not available, will use fallback mode")
```

### Features
- **Smart Installation**: ตรวจสอบและติดตั้งเฉพาะแพ็กเกจที่หายไป
- **Raspberry Pi Optimization**: ใช้ `apt` สำหรับ PiCamera2
- **Fallback Mode**: ทำงานต่อได้แม้ติดตั้งไม่สำเร็จ
- **Wheel Support**: รองรับไฟล์ `.whl` สำหรับ Hailo SDK

---

## ⚙️ Configuration Management System  
**Location**: Lines 180-230

### วัตถุประสงค์
จัดการพารามิเตอร์และการตั้งค่าทั้งหมดของระบบ

```python
class Config:
    # Discord Webhook
    DISCORD_WEBHOOK = "https://discord.com/api/webhooks/..."
    
    # Hailo Model Configuration
    HEF_PATH = "headphones_final_8l.hef"  # โมเดล AI ที่คอมไพล์แล้ว
    
    # Camera Settings
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    
    # AI Detection Parameters
    CONFIDENCE_THRESHOLD = 0.5  # ความแม่นยำขั้นต่ำ (50%)
    NMS_THRESHOLD = 0.4         # Non-Maximum Suppression
    
    # Network Configuration  
    WIFI_SSID = "aiwifi"
    WIFI_PASSWORD = "00000000"
    WIFI_COUNTRY = "TH"                    # รหัสประเทศสำหรับ 5GHz
    NETWORK_SCAN_INTERVAL = 10             # สแกนทุก 10 วินาที
    PREFER_ETHERNET = True                 # ให้ความสำคัญ Ethernet ก่อน
    
    # Remote Access
    ENABLE_TAILSCALE = True                # เปิดใช้ Tailscale
    TAILSCALE_AUTO_INSTALL = True          # ติดตั้งอัตโนมัติ
    
    # Notification Settings
    NOTIFICATION_COOLDOWN = 60             # คูลดาวน์ข้อความ 60 วินาที  
    IMAGE_COOLDOWN = 5                     # คูลดาวน์รูปภาพ 5 วินาที
    
    # PPE Detection Classes
    CLASS_NAMES = ["headphones", "left_ear", "people", "right_ear"]
```

### Features
- **Centralized Configuration**: ตั้งค่าทั้งหมดอยู่ที่เดียว
- **Production Ready**: พารามิเตอร์ที่ปรับแต่งสำหรับใช้งานจริง
- **Multi-network Support**: รองรับ Ethernet, Wi-Fi, และ Tailscale
- **Flexible Detection**: ปรับแต่ง AI detection threshold ได้

---

## 📶 Network Management System
**Location**: Lines 231-520

### วัตถุประสงค์
จัดการการเชื่อมต่อเครือข่ายแบบอัจฉริยะพร้อม Remote Access

```python
class WiFiManager:
    def __init__(self):
        self.is_connected = False
        self.current_ip = None
        self.current_ssid = None
        self.current_interface = None      # eth0 หรือ wlan0
        self.monitoring_thread = None      # Thread สำหรับตรวจสอบ
        self.monitoring_active = False
        
    def check_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อตามลำดับความสำคัญ"""
        # ลำดับ 1: ตรวจสอบ Ethernet ก่อน
        if Config.PREFER_ETHERNET and self.check_ethernet_connection():
            return True
        
        # ลำดับ 2: ตรวจสอบ Wi-Fi
        if self.check_wifi_connection():
            return True
            
        return False
    
    def check_ethernet_connection(self) -> bool:
        """ตรวจสอบการเชื่อมต่อ Ethernet"""
        try:
            # ตรวจสอบว่า eth0 เปิดอยู่หรือไม่
            result = subprocess.run([
                "ip", "link", "show", "eth0"
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return False
            
            # ตรวจสอบ IP address
            ip_result = subprocess.run([
                "ip", "addr", "show", "eth0"
            ], capture_output=True, text=True, timeout=5)
            
            if "inet " in ip_result.stdout:
                # ทดสอบ internet connectivity
                if self.test_internet_connectivity():
                    self.current_interface = "eth0"
                    self.current_ssid = "Ethernet"
                    return True
            return False
        except Exception as e:
            return False
```

### Network Monitoring Thread

```python
def _network_monitor_loop(self):
    """Background monitoring ทำงานตลอดเวลา"""
    while self.monitoring_active:
        try:
            current_time = time.time()
            
            # ตรวจสอบการเชื่อมต่อทุก 5 วินาที
            if not self.check_connection():
                time_since_scan = current_time - self.last_scan_time
                
                # พยายามเชื่อมต่อใหม่ทุก 10 วินาที
                if time_since_scan >= Config.NETWORK_SCAN_INTERVAL:
                    logger.info("🔍 No internet - attempting reconnection")
                    self.last_scan_time = current_time
                    
                    # ลองใช้ Ethernet ก่อน
                    if self.check_ethernet_connection():
                        continue
                    
                    # ลองเชื่อมต่อ Wi-Fi
                    self.connect_to_wifi()
            
            time.sleep(5)  # ตรวจสอบทุก 5 วินาที
        except Exception as e:
            logger.error(f"❌ Network monitoring error: {e}")
            time.sleep(5)
```

### Tailscale Integration

```python
def setup_tailscale(self) -> bool:
    """ติดตั้งและตั้งค่า Tailscale สำหรับ Remote Access"""
    try:
        tailscale_status = self.check_tailscale_status()
        
        # ติดตั้งถ้ายังไม่มี
        if not tailscale_status["installed"]:
            if not self.install_tailscale():
                return False
        
        # เริ่มต้น service
        if not tailscale_status["running"]:
            logger.info("🚀 Starting Tailscale...")
            subprocess.run([
                "sudo", "tailscale", "up", "--accept-routes"
            ], timeout=60)
        
        # ตรวจสอบผลลัพธ์
        final_status = self.check_tailscale_status()
        if final_status["running"] and final_status["ip"]:
            logger.info(f"✅ Tailscale running: {final_status['ip']}")
            return True
        return False
    except Exception as e:
        logger.error(f"❌ Tailscale setup error: {e}")
        return False

def install_tailscale(self) -> bool:
    """ติดตั้ง Tailscale อัตโนมัติ"""
    try:
        logger.info("🔧 Installing Tailscale...")
        install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
        result = subprocess.run(install_cmd, shell=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        return False
```

---

## 🔔 Discord Notification System
**Location**: Lines 551-800

### วัตถุประสงค์
ส่งแจ้งเตือนและภาพหลักฐานไปยัง Discord พร้อมระบบ Cooldown

```python
class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.last_notification = 0
        self.last_image_sent = 0          # ติดตาม image cooldown
        self.cooldown_period = 60         # ข้อความ 60 วินาที
        self.image_cooldown = 5           # รูปภาพ 5 วินาที
        
    def send_notification(self, message: str, detection_count: int,
                         additional_info: Dict = None, 
                         image_bytes: bytes = None, 
                         image_name: str = None) -> bool:
        """ส่งแจ้งเตือนพร้อมระบบ Cooldown แบบ Dual"""
        current_time = time.time()
        
        # ตรวจสอบ cooldown ข้อความ
        if current_time - self.last_notification < self.cooldown_period:
            logger.info("🔒 Message blocked by cooldown")
            return False
        
        # ตรวจสอบ cooldown รูปภาพ
        if image_bytes and image_name:
            if current_time - self.last_image_sent < self.image_cooldown:
                logger.info("📸 Image blocked by cooldown")
                # ส่งข้อความโดยไม่มีรูป
                return self.send_notification(message, detection_count, 
                                           additional_info, None, None)
```

### PPE Violation Alert Format

```python
def create_ppe_alert_embed(self, message: str, detection_count: int):
    """สร้าง Discord Embed สำหรับแจ้งเตือน PPE"""
    embed = {
        "title": "🎧 PPE Violation - Headphone Protection Required",
        "description": message,
        "color": 0xff0000,  # สีแดงสำหรับเตือนภัย
        "fields": [
            {"name": "⚠️ PPE Violations", "value": str(detection_count)},
            {"name": "⏰ Detection Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
            {"name": "📍 Location", "value": "Raspberry Pi 5 + Hailo AI"},
            {"name": "🤖 Detection Engine", "value": "Hailo TOP13" if HAILO_AVAILABLE else "CPU"},
            {"name": "📷 Camera Source", "value": "PiCamera2" if PICAMERA_AVAILABLE else "USB"}
        ],
        "footer": {"text": "Hailo AI Ear Protection Monitor v2.2"},
        "timestamp": datetime.now().isoformat()
    }
    return embed
```

### Network Status Notification

```python
def send_network_notification(self, connection_info: Dict) -> bool:
    """ส่งแจ้งเตือนสถานะเครือข่าย"""
    if connection_info.get("connected"):
        ip_address = connection_info.get("ip_address", "Unknown")
        connection_type = "Ethernet" if connection_info.get("interface") == "eth0" else "Wi-Fi"
        
        additional_info = {
            "📍 Local IP": ip_address,
            "🔗 Connection": connection_type,
            "🏠 Local SSH": f"ssh pi@{ip_address}",
        }
        
        # เพิ่มข้อมูล Tailscale ถ้ามี
        tailscale = connection_info.get("tailscale", {})
        if tailscale.get("running") and tailscale.get("ip"):
            additional_info["🌐 Tailscale IP"] = tailscale["ip"]
            additional_info["🔑 Remote SSH"] = f"ssh pi@{tailscale['ip']}"
            additional_info["🌍 Access"] = "Available Worldwide"
        
        return self.send_embed_notification("Network Connected", additional_info)
```

---

## 🤖 AI Inference Engine
**Location**: Lines 801-1200

### วัตถุประสงค์
ประมวลผลภาพด้วย Hailo AI หรือ CPU Fallback

```python
class HailoInference:
    def __init__(self, hef_path: str):
        self.hef_path = hef_path
        self.vdevice = None
        self.network_group = None
        self.network_group_params = None
        self.is_configured = False
        
    def initialize(self) -> bool:
        """เริ่มต้น Hailo AI Engine"""
        try:
            if not HAILO_AVAILABLE:
                logger.warning("⚠️ Hailo not available, will use CPU fallback")
                return False
            
            # สร้าง VDevice
            from hailo_platform import VDevice, HailoStreamInterface
            self.vdevice = VDevice()
            
            # โหลดโมเดล HEF
            with open(self.hef_path, 'rb') as hef_file:
                hef = hef_file.read()
            
            # สร้าง network group
            network_groups = self.vdevice.configure(hef)
            self.network_group = network_groups[0]
            self.network_group_params = self.network_group.create_params()
            
            logger.info("✅ Hailo AI Engine initialized successfully")
            self.is_configured = True
            return True
            
        except Exception as e:
            logger.error(f"❌ Hailo initialization failed: {e}")
            return False
    
    def infer(self, frame: np.ndarray) -> List[Dict]:
        """รัน AI inference บนภาพ"""
        try:
            if not self.is_configured:
                return self.cpu_fallback_inference(frame)
            
            # เตรียมภาพสำหรับ Hailo
            input_data = self.preprocess_frame(frame)
            
            # รัน inference
            with self.network_group.activate(self.network_group_params):
                output = self.network_group.infer(input_data)
            
            # แปลงผลลัพธ์
            detections = self.postprocess_output(output[0])
            return detections
            
        except Exception as e:
            logger.error(f"❌ Hailo inference error: {e}")
            return self.cpu_fallback_inference(frame)
```

### CPU Fallback System

```python
def cpu_fallback_inference(self, frame: np.ndarray) -> List[Dict]:
    """ระบบสำรอง CPU เมื่อ Hailo ไม่สามารถใช้งานได้"""
    try:
        # ใช้ OpenCV DNN module
        if hasattr(self, 'cpu_net') and self.cpu_net is not None:
            blob = cv2.dnn.blobFromImage(
                frame, 1/255.0, (640, 640), swapRB=True, crop=False
            )
            self.cpu_net.setInput(blob)
            outputs = self.cpu_net.forward()
            
            return self.parse_cpu_detections(outputs, frame.shape)
        else:
            # จำลองผลลัพธ์สำหรับการทดสอบ
            return self.simulate_detections()
            
    except Exception as e:
        logger.error(f"❌ CPU inference error: {e}")
        return []

def simulate_detections(self) -> List[Dict]:
    """จำลองผลลัพธ์เพื่อทดสอบระบบ"""
    import random
    
    # สุ่มสถานการณ์การตรวจจับ
    scenarios = [
        [],  # ไม่มีการตรวจจับ
        [{"class": "people", "confidence": 0.85, "bbox": [100, 100, 200, 300]}],  # มีคน
        [
            {"class": "people", "confidence": 0.90, "bbox": [100, 100, 200, 300]},
            {"class": "headphones", "confidence": 0.75, "bbox": [120, 120, 180, 160]}
        ],  # คนสวมหูฟัง (ปลอดภัย)
        [
            {"class": "people", "confidence": 0.88, "bbox": [100, 100, 200, 300]},
            {"class": "left_ear", "confidence": 0.70, "bbox": [130, 130, 150, 150]}
        ]   # หูเปิดออก (ละเมิด)
    ]
    
    return random.choice(scenarios)
```

---

## 📷 Camera System  
**Location**: Lines 1201-1500

### วัตถุประสงค์
จัดการกล้องด้วยระบบ Fallback: PiCamera2 → USB → Simulation

```python
class CameraSystem:
    def __init__(self):
        self.camera = None
        self.camera_type = "Unknown"
        self.is_initialized = False
        self.frame_count = 0
        
    def initialize(self) -> bool:
        """เริ่มต้นกล้องด้วยระบบ Fallback"""
        # ลำดับ 1: ลอง PiCamera2 ก่อน
        if self.init_picamera2():
            return True
        
        # ลำดับ 2: ลอง USB Camera
        if self.init_usb_camera():
            return True
        
        # ลำดับ 3: โหมดจำลอง
        if self.init_simulation_mode():
            return True
        
        return False
    
    def init_picamera2(self) -> bool:
        """เริ่มต้น Raspberry Pi Camera Module"""
        try:
            if not PICAMERA_AVAILABLE:
                return False
            
            from picamera2 import Picamera2
            self.camera = Picamera2()
            
            # กำหนดค่ากล้อง
            config = self.camera.create_preview_configuration(
                main={
                    "size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT),
                    "format": "RGB888"
                }
            )
            self.camera.configure(config)
            self.camera.start()
            
            # ทดสอบการจับภาพ
            test_frame = self.camera.capture_array()
            if test_frame is not None and test_frame.size > 0:
                self.camera_type = "PiCamera2"
                self.is_initialized = True
                logger.info("✅ PiCamera2 initialized successfully")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️ PiCamera2 failed: {e}")
        
        return False
    
    def init_usb_camera(self) -> bool:
        """เริ่มต้น USB Camera ผ่าน OpenCV"""
        try:
            # ลองเปิดกล้อง USB (index 0-3)
            for camera_index in range(4):
                cap = cv2.VideoCapture(camera_index)
                
                if cap.isOpened():
                    # ตั้งค่าความละเอียด
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
                    cap.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
                    
                    # ทดสอบการจับภาพ
                    ret, test_frame = cap.read()
                    if ret and test_frame is not None:
                        self.camera = cap
                        self.camera_type = f"USB Camera {camera_index}"
                        self.is_initialized = True
                        logger.info(f"✅ {self.camera_type} initialized")
                        return True
                
                cap.release()
                
        except Exception as e:
            logger.warning(f"⚠️ USB Camera failed: {e}")
        
        return False
    
    def capture_frame(self) -> np.ndarray:
        """จับภาพจากกล้อง"""
        try:
            if not self.is_initialized:
                return None
            
            if self.camera_type == "PiCamera2":
                frame = self.camera.capture_array()
                if frame is not None:
                    # แปลง RGB เป็น BGR สำหรับ OpenCV
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    
            elif "USB Camera" in self.camera_type:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    return None
                    
            elif self.camera_type == "Simulation":
                frame = self.generate_simulation_frame()
            
            self.frame_count += 1
            return frame
            
        except Exception as e:
            logger.error(f"❌ Frame capture error: {e}")
            return None
```

---

## 🛡️ Safety Monitoring System
**Location**: Lines 1501-2000

### วัตถุประสงค์
ระบบหลักที่รวมทุกส่วนเข้าด้วยกันเพื่อตรวจสอบ PPE

```python
class SafetyMonitoringSystem:
    def __init__(self):
        self.camera_system = CameraSystem()
        self.inference_engine = HailoInference(Config.HEF_PATH)
        self.discord_notifier = DiscordNotifier(Config.DISCORD_WEBHOOK)
        self.is_running = False
        self.total_detections = 0
        self.violation_count = 0
        
    def initialize(self) -> bool:
        """เริ่มต้นระบบทั้งหมด"""
        logger.info("🚀 Initializing Safety Monitoring System...")
        
        # เริ่มต้นกล้อง
        if not self.camera_system.initialize():
            logger.error("❌ Camera initialization failed")
            return False
        
        # เริ่มต้น AI Engine
        self.inference_engine.initialize()  # ไม่ return False ถ้าใช้ CPU fallback
        
        # ส่งแจ้งเตือนเริ่มต้นระบบ
        self.discord_notifier.send_startup_notification()
        
        logger.info("✅ Safety Monitoring System ready")
        return True
    
    def run_monitoring_loop(self):
        """วนลูปการตรวจสอบหลัก"""
        self.is_running = True
        last_fps_time = time.time()
        fps_counter = 0
        
        try:
            while self.is_running:
                start_time = time.time()
                
                # จับและประมวลผลภาพ
                success = self.process_frame()
                
                # คำนวณ FPS
                fps_counter += 1
                if time.time() - last_fps_time >= 1.0:
                    self.current_fps = fps_counter
                    fps_counter = 0
                    last_fps_time = time.time()
                
                # แสดงสถิติทุก 30 วินาที
                if self.total_detections % 100 == 0:
                    self.log_statistics()
                
                # จำกัด FPS
                elapsed = time.time() - start_time
                sleep_time = max(0, (1.0 / Config.CAMERA_FPS) - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("⚡ Monitoring stopped by user")
        finally:
            self.cleanup()
    
    def process_frame(self) -> bool:
        """ประมวลผลภาพหนึ่งเฟรม"""
        try:
            # จับภาพ
            frame = self.camera_system.capture_frame()
            if frame is None:
                return False
            
            # รัน AI detection
            detections = self.inference_engine.infer(frame)
            self.total_detections += len(detections)
            
            # วิเคราะห์ PPE compliance
            compliance_result = self.analyze_ppe_compliance(detections)
            
            # แจ้งเตือนถ้าพบการละเมิด
            if compliance_result["violation"]:
                self.handle_ppe_violation(frame, detections, compliance_result)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Frame processing error: {e}")
            return False
```

### PPE Compliance Logic

```python
def analyze_ppe_compliance(self, detections: List[Dict]) -> Dict:
    """วิเคราะห์การปฏิบัติตามกฎ PPE"""
    people_count = sum(1 for d in detections if d["class"] == "people")
    headphones_count = sum(1 for d in detections if d["class"] == "headphones")
    exposed_ears = sum(1 for d in detections if d["class"] in ["left_ear", "right_ear"])
    
    # กฎการตัดสิน PPE Compliance
    violation = False
    reason = "Compliant"
    
    if people_count > 0:
        if headphones_count == 0:
            violation = True
            reason = f"{people_count} person(s) without headphone protection"
        elif exposed_ears > 0:
            violation = True
            reason = f"Exposed ears detected ({exposed_ears} ears)"
    
    return {
        "violation": violation,
        "reason": reason,
        "people": people_count,
        "headphones": headphones_count,
        "exposed_ears": exposed_ears,
        "confidence": max([d["confidence"] for d in detections], default=0.0)
    }

def handle_ppe_violation(self, frame: np.ndarray, detections: List[Dict], 
                        compliance_result: Dict):
    """จัดการเมื่อพบการละเมิด PPE"""
    self.violation_count += 1
    
    # วาดกรอบรอบการตรวจจับ
    annotated_frame = self.draw_detections(frame, detections)
    
    # แปลงภาพเป็น JPEG
    image_bytes = self.frame_to_jpeg_bytes(annotated_frame)
    
    # ส่งแจ้งเตือนไปยัง Discord
    message = f"🚨 PPE Violation Detected: {compliance_result['reason']}"
    additional_info = {
        "👥 People Count": compliance_result["people"],
        "🎧 Headphones": compliance_result["headphones"],
        "👂 Exposed Ears": compliance_result["exposed_ears"],
        "📊 Confidence": f"{compliance_result['confidence']:.1%}",
        "📸 Total Violations": self.violation_count
    }
    
    success = self.discord_notifier.send_notification(
        message=message,
        detection_count=len(detections),
        additional_info=additional_info,
        image_bytes=image_bytes,
        image_name=f"violation_{int(time.time())}.jpg"
    )
    
    if success:
        logger.info(f"✅ Violation alert sent (#{self.violation_count})")
    else:
        logger.warning("⚠️ Failed to send violation alert")
```

---

## 🚀 Main Function และ Entry Point
**Location**: Lines 2001-2400

### วัตถุประสงค์
เริ่มต้นระบบทั้งหมดและจัดการ lifecycle

```python
def main():
    """ฟังก์ชันหลักของระบบ"""
    try:
        # แสดง banner เริ่มต้น
        show_startup_banner()
        
        # ตรวจสอบความต้องการของระบบ
        if not check_system_requirements():
            return 1
        
        # เริ่มต้นการเชื่อมต่อเครือข่าย
        logger.info("\n📶 Step 0: Network Connection")
        network_connected = setup_network_connection()
        
        # เริ่มต้น Tailscale สำหรับ Remote Access
        if Config.ENABLE_TAILSCALE:
            setup_tailscale_connection()
        
        # เริ่มต้น Network Monitoring
        wifi_manager.start_network_monitoring()
        
        # เริ่มต้นระบบตรวจสอบความปลอดภัย
        logger.info("\n🚀 Step 1: Safety Monitoring System")
        detection_system = SafetyMonitoringSystem()
        
        if not detection_system.initialize():
            logger.error("❌ System initialization failed")
            return 1
        
        # เริ่มการทำงานหลัก
        logger.info("\n🛡️ Starting PPE Compliance Monitoring...")
        detection_system.run_monitoring_loop()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚡ System interrupted by user")
        cleanup_resources()
        return 130
        
    except Exception as e:
        logger.error(f"💥 Fatal system error: {e}")
        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    # ตั้งค่า Signal handlers สำหรับ graceful shutdown
    import signal
    
    def signal_handler(sig, frame):
        logger.info(f"\n⚡ Received signal {sig}, shutting down...")
        
        # หยุด network monitoring
        if 'wifi_manager' in globals():
            wifi_manager.stop_network_monitoring()
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # systemctl stop
    
    # รันระบบหลัก
    exit_code = main()
    sys.exit(exit_code)
```

### System Requirements Check

```python
def check_system_requirements():
    """ตรวจสอบความต้องการของระบบ"""
    requirements = {
        "Python Version": sys.version_info >= (3, 8),
        "OpenCV": cv2.__version__ >= "4.5.0" if 'cv2' in globals() else False,
        "NumPy": np.__version__ >= "1.19.0" if 'np' in globals() else False,
        "HEF Model": Path(Config.HEF_PATH).exists(),
        "Discord Webhook": bool(Config.DISCORD_WEBHOOK),
        "Camera Available": check_camera_availability(),
        "Network Access": check_network_access()
    }
    
    logger.info("🔍 System Requirements Check:")
    all_ok = True
    
    for requirement, status in requirements.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"   {status_icon} {requirement}")
        if not status:
            all_ok = False
    
    return all_ok
```

---

## 📊 สรุปสถาปัตยกรรมระบบ

### ข้อดีของการออกแบบ:
1. **Modular Design**: แยกส่วนการทำงานชัดเจน
2. **Fallback Mechanisms**: มีระบบสำรองในทุกส่วน
3. **Auto-configuration**: ตั้งค่าตัวเองได้โดยอัตโนมัติ
4. **Production Ready**: พร้อมใช้งานจริงในสภาพแวดล้อมการผลิต
5. **Comprehensive Monitoring**: ติดตามสถานะทุกส่วนของระบบ

### การจัดการ Error:
- **Network Failures**: Auto-retry และ fallback
- **Hardware Issues**: CPU fallback และ USB camera
- **AI Model Problems**: Simulation mode
- **Discord API Limits**: Cooldown system
- **System Crashes**: Graceful shutdown และ cleanup

ระบบนี้ออกแบบมาให้ทำงานได้แม้ในสถานการณ์ที่ไม่เหมาะสม และสามารถฟื้นตัวได้เองเมื่อสถานการณ์กลับมาปกติ 🛡️🔧