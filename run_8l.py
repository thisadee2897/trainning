#!/usr/bin/env python3
"""
🎧 Raspberry Pi 5 + Hailo AI TOP13 + Camera Module 🎧
All-in-One Headphones Detection System
- Auto Package Installation
- Real-time Detection  
- Discord Notifications
- Logging System
- Single File Solution

Author: Your Name
Date: December 2025
Version: 2.0.0
"""

import os
import sys
import subprocess
import time
import json
import requests
import logging
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# ===============================
# 🔧 AUTO PACKAGE INSTALLATION
# ===============================

def install_packages():
    """Auto-install required packages with enhanced error handling"""
    print("🚀 Checking and installing required packages...")
    
    # Core packages (essential)
    core_packages = [
        "numpy",  # Install numpy first without version constraint
        "opencv-python", 
        "requests",
        "pillow"
    ]
    
    # Optional packages
    optional_packages = [
        "picamera2",  # May not work on all systems
        "hailo-platform"  # May not be available
    ]
    
    # Install core packages first
    for package in core_packages:
        try:
            print(f"📦 Installing {package}...")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package, 
                "--upgrade", "--quiet"
            ])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            if package in ["numpy", "opencv-python"]:  # Critical packages
                print(f"⚠️  {package} is required but failed to install!")
                return False
    
    # Install optional packages
    for package in optional_packages:
        try:
            print(f"📦 Installing {package}...")
            # Use different strategies for different packages
            if package == "picamera2":
                # Try system package first for picamera2
                try:
                    subprocess.check_call(["sudo", "apt", "install", "-y", "python3-picamera2"], 
                                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"✅ {package} installed via apt")
                    continue
                except:
                    pass
            
            subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--quiet"])
            print(f"✅ {package} installed successfully")
        except subprocess.CalledProcessError:
            print(f"⚠️  {package} not available, will use fallback mode")
    
    # Install from wheel if available
    wheel_file = "hailo_dataflow_compiler-3.27.0-py3-none-linux_x86_64.whl"
    if Path(wheel_file).exists():
        try:
            print(f"🎯 Installing {wheel_file}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", wheel_file, "--quiet"])
            print(f"✅ Hailo compiler installed from wheel")
        except subprocess.CalledProcessError:
            print(f"⚠️  Failed to install wheel file")
    
    print("📦 Package installation completed!")
    return True

# Auto-install packages on first run
if not install_packages():
    print("❌ Failed to install critical packages")
    sys.exit(1)

# Import packages after installation
try:
    import cv2
    import numpy as np
    print(f"✅ Core packages imported - OpenCV: {cv2.__version__}, NumPy: {np.__version__}")
except ImportError as e:
    print(f"❌ Critical packages missing: {e}")
    print("🔄 Trying alternative installation...")
    try:
        # Try installing without version constraints
        subprocess.check_call([sys.executable, "-m", "pip", "install", "opencv-python", "numpy", "--force-reinstall", "--quiet"])
        import cv2
        import numpy as np
        print("✅ Core packages installed and imported successfully")
    except Exception as e2:
        print(f"❌ Still failed: {e2}")
        sys.exit(1)

# Try to import Hailo packages
HAILO_AVAILABLE = False
PICAMERA_AVAILABLE = False

# Try to fix numpy/simplejpeg compatibility issue
try:
    print("🔧 Fixing numpy/simplejpeg compatibility...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", "numpy", "--quiet"])
    print("✅ NumPy reinstalled")
except:
    print("⚠️  NumPy reinstall failed, continuing anyway...")

try:
    from picamera2 import Picamera2, Preview
    PICAMERA_AVAILABLE = True
    print("✅ PiCamera2 imported successfully")
except ImportError as e:
    print(f"⚠️  PiCamera2 not available: {e}")
    print("🔄 Will use USB camera or simulation mode")
    PICAMERA_AVAILABLE = False
except ValueError as e:
    print(f"⚠️  PiCamera2 binary compatibility issue: {e}")
    print("🔄 Trying alternative import...")
    try:
        # Try to install compatible simplejpeg
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "simplejpeg", "--quiet"])
        from picamera2 import Picamera2, Preview
        PICAMERA_AVAILABLE = True
        print("✅ PiCamera2 imported after fixing simplejpeg")
    except Exception as e2:
        print(f"⚠️  PiCamera2 still not available: {e2}")
        print("🔄 Will use USB camera or simulation mode")
        PICAMERA_AVAILABLE = False

try:
    from hailo_platform import (HEF, VDevice, HailoSchedulingAlgorithm, 
                               ConfigureParams, InferVStreams, InputVStreamParams, 
                               OutputVStreamParams, FormatType, HailoStreamInterface)
    HAILO_AVAILABLE = True
    print("✅ Hailo Platform imported successfully")
except ImportError:
    print("⚠️  Hailo Platform not available - will use CPU inference fallback")
    HAILO_AVAILABLE = False

# Check if running in headless mode (no display)
HEADLESS_MODE = False
try:
    import os
    if not os.environ.get('DISPLAY'):
        HEADLESS_MODE = True
        print("⚠️  No DISPLAY detected - running in headless mode")
except:
    pass

# ===============================
# ⚙️ CONFIGURATION
# ===============================

class Config:
    # Discord Webhook
    DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1447260795359596598/z0AycOqXHn3Douayq5BRKbZj_p3GdvrWncBbJ6hZAzFRzzwK9LpyVkmH9wNFvO0dP2RU"
    
    # Hailo Model
    HEF_PATH = "headphones_final_8l.hef"
    
    # Camera Settings
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    CAMERA_FPS = 30
    
    # Detection Settings
    CONFIDENCE_THRESHOLD = 0.5
    NMS_THRESHOLD = 0.4
    
    # Notification Settings
    NOTIFICATION_COOLDOWN = 60  # seconds between notifications (increased to prevent spam)
    MAX_DETECTIONS_PER_FRAME = 10
    
    # Network Configuration
    # Priority: Ethernet -> Wi-Fi -> Scan for networks
    WIFI_SSID = "aiwifi"
    WIFI_PASSWORD = "00000000"
    WIFI_COUNTRY = "TH"  # Thailand country code for proper 5GHz support
    ENABLE_WIFI_5GHZ = True  # Enable 5GHz Wi-Fi support
    NETWORK_SCAN_INTERVAL = 10  # seconds between network scans when disconnected
    PREFER_ETHERNET = True  # Prefer Ethernet over Wi-Fi
    
    # Remote Access Configuration
    ENABLE_TAILSCALE = True  # Enable Tailscale for remote access
    TAILSCALE_AUTO_INSTALL = True  # Auto-install Tailscale if not available
    
    # Class Names - Updated to match data.yaml configuration
    CLASS_NAMES = ["headphones", "left_ear", "people", "right_ear"]
    
    # Colors for bounding boxes (BGR format)
    COLORS = [(0, 255, 0), (0, 0, 255), (255, 0, 0), (0, 0, 255)]  # Green, Red, Blue, Red
    
    # Logging
    LOG_LEVEL = logging.INFO
    LOG_FILE = "hailo_detection.log"
    
    # Simulation mode (if no camera/hailo available)
    SIMULATION_MODE = False
    DEMO_VIDEO_PATH = None  # Path to demo video file
    
    # Headless mode (no GUI display)
    HEADLESS_MODE = HEADLESS_MODE
    SAVE_DETECTION_IMAGES = False  # Images sent to Discord only, not saved locally

# ===============================
# � WI-FI CONNECTIVITY
# ===============================

class WiFiManager:
    """Enhanced Wi-Fi management with 5GHz support"""
    
    def __init__(self):
        self.is_connected = False
        self.current_ip = None
        self.current_ssid = None
        self.current_interface = None  # Track active interface (eth0/wlan0)
        self.connection_attempts = 0
        self.max_attempts = 3
        self.monitoring_thread = None
        self.monitoring_active = False
        self.last_scan_time = 0
        
    def setup_wifi_country(self) -> bool:
        """Setup Wi-Fi country code for proper 5GHz support"""
        try:
            logger.info(f"🌍 Setting Wi-Fi country code to {Config.WIFI_COUNTRY}")
            
            # Check if raspi-config is available
            result = subprocess.run(["sudo", "raspi-config", "nonint", "do_wifi_country", Config.WIFI_COUNTRY], 
                                  capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info("✅ Wi-Fi country code set successfully")
                return True
            else:
                logger.warning(f"⚠️  Failed to set country code: {result.stderr}")
                # Try alternative method using wpa_cli
                try:
                    subprocess.run(["sudo", "wpa_cli", "set", "country", Config.WIFI_COUNTRY], 
                                 capture_output=True, timeout=10)
                    logger.info("✅ Wi-Fi country set via wpa_cli")
                    return True
                except:
                    logger.warning("⚠️  Could not set Wi-Fi country, continuing anyway")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error setting Wi-Fi country: {e}")
            return False
    
    def check_ethernet_connection(self) -> bool:
        """Check if Ethernet cable is connected and has internet"""
        try:
            # Check if eth0 interface is up
            result = subprocess.run(["ip", "link", "show", "eth0"], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode != 0:
                return False
            
            # Check if eth0 has an IP address
            ip_result = subprocess.run(["ip", "addr", "show", "eth0"], 
                                     capture_output=True, text=True, timeout=5)
            
            if "inet " not in ip_result.stdout:
                return False
            
            # Extract IP address from eth0
            lines = ip_result.stdout.split('\n')
            for line in lines:
                if "inet " in line and "127.0.0.1" not in line:
                    ip_info = line.strip().split()
                    if ip_info:
                        eth_ip = ip_info[1].split('/')[0]
                        
                        # Test internet connectivity
                        if self.test_internet_connectivity():
                            logger.info(f"✅ Ethernet connected with IP: {eth_ip}")
                            self.current_ip = eth_ip
                            self.current_interface = "eth0"
                            self.current_ssid = "Ethernet"
                            self.is_connected = True
                            return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Ethernet check error: {e}")
            return False
    
    def test_internet_connectivity(self) -> bool:
        """Test actual internet connectivity"""
        test_hosts = ["8.8.8.8", "1.1.1.1", "google.com"]
        
        for host in test_hosts:
            try:
                result = subprocess.run(["ping", "-c", "1", "-W", "3", host], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    return True
            except:
                continue
        
        return False
    
    def scan_wifi_networks(self) -> List[Dict]:
        """Scan for available Wi-Fi networks with 5GHz detection"""
        try:
            logger.info("🔍 Scanning for Wi-Fi networks...")
            
            # Use iwlist to scan networks
            result = subprocess.run(["sudo", "iwlist", "wlan0", "scan"], 
                                  capture_output=True, text=True, timeout=15)
            
            if result.returncode != 0:
                logger.warning("⚠️  Failed to scan networks")
                return []
            
            networks = []
            lines = result.stdout.split('\n')
            current_network = {}
            
            for line in lines:
                line = line.strip()
                if "Cell " in line and "Address:" in line:
                    if current_network:
                        networks.append(current_network)
                    current_network = {}
                elif "ESSID:" in line:
                    essid = line.split('ESSID:')[1].strip('"')
                    current_network['ssid'] = essid
                elif "Frequency:" in line:
                    freq = line.split('Frequency:')[1].split()[0]
                    current_network['frequency'] = freq
                    # Detect 5GHz (5.0+ GHz)
                    try:
                        freq_float = float(freq)
                        current_network['is_5ghz'] = freq_float >= 5.0
                    except:
                        current_network['is_5ghz'] = False
                elif "Quality=" in line:
                    quality = line.split('Quality=')[1].split()[0]
                    current_network['quality'] = quality
            
            if current_network:
                networks.append(current_network)
            
            # Filter and log networks
            target_networks = [n for n in networks if n.get('ssid') == Config.WIFI_SSID]
            
            if target_networks:
                for network in target_networks:
                    freq_info = f"{network.get('frequency', 'Unknown')} {'(5GHz)' if network.get('is_5ghz', False) else '(2.4GHz)'}"
                    logger.info(f"📶 Found target network: {network.get('ssid')} - {freq_info}")
            
            return networks
            
        except Exception as e:
            logger.error(f"❌ Error scanning Wi-Fi networks: {e}")
            return []
    
    def connect_to_wifi(self) -> bool:
        """Connect to Wi-Fi with 5GHz preference"""
        try:
            self.connection_attempts += 1
            logger.info(f"🔗 Attempting Wi-Fi connection (attempt {self.connection_attempts}/{self.max_attempts})")
            
            # Setup country code first
            self.setup_wifi_country()
            
            # Scan networks to check availability
            networks = self.scan_wifi_networks()
            target_networks = [n for n in networks if n.get('ssid') == Config.WIFI_SSID]
            
            if not target_networks:
                logger.warning(f"⚠️  Target network '{Config.WIFI_SSID}' not found")
                if self.connection_attempts < self.max_attempts:
                    logger.info("🔄 Retrying in 10 seconds...")
                    time.sleep(10)
                    return self.connect_to_wifi()
                return False
            
            # Prefer 5GHz network if available
            preferred_network = None
            for network in target_networks:
                if Config.ENABLE_WIFI_5GHZ and network.get('is_5ghz', False):
                    preferred_network = network
                    break
            
            if not preferred_network:
                preferred_network = target_networks[0]
            
            freq_info = f"{preferred_network.get('frequency', 'Unknown')} {'(5GHz)' if preferred_network.get('is_5ghz', False) else '(2.4GHz)'}"
            logger.info(f"🎯 Connecting to: {Config.WIFI_SSID} - {freq_info}")
            
            # Create wpa_supplicant configuration
            wpa_config = f"""
country={Config.WIFI_COUNTRY}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid="{Config.WIFI_SSID}"
    psk="{Config.WIFI_PASSWORD}"
    key_mgmt=WPA-PSK
}}
"""
            
            # Write configuration
            with open('/tmp/wpa_supplicant_temp.conf', 'w') as f:
                f.write(wpa_config)
            
            # Copy to system location
            subprocess.run(["sudo", "cp", "/tmp/wpa_supplicant_temp.conf", "/etc/wpa_supplicant/wpa_supplicant.conf"], 
                         timeout=10)
            
            # Restart networking
            logger.info("🔄 Restarting Wi-Fi interface...")
            subprocess.run(["sudo", "ifconfig", "wlan0", "down"], timeout=10)
            time.sleep(2)
            subprocess.run(["sudo", "ifconfig", "wlan0", "up"], timeout=10)
            time.sleep(5)
            
            # Restart wpa_supplicant
            subprocess.run(["sudo", "systemctl", "restart", "wpa_supplicant"], timeout=15)
            time.sleep(5)
            
            # Request DHCP
            subprocess.run(["sudo", "dhclient", "wlan0"], timeout=15)
            
            # Wait for connection
            logger.info("⏳ Waiting for connection...")
            for i in range(30):  # Wait up to 30 seconds
                if self.check_connection():
                    logger.info(f"✅ Wi-Fi connected successfully to {self.current_ssid}")
                    logger.info(f"📍 IP Address: {self.current_ip}")
                    return True
                time.sleep(1)
            
            logger.warning("⚠️  Wi-Fi connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error connecting to Wi-Fi: {e}")
            return False
    
    def check_connection(self) -> bool:
        """Check current network connection status with Ethernet priority"""
        try:
            # Priority 1: Check Ethernet first
            if Config.PREFER_ETHERNET and self.check_ethernet_connection():
                return True
            
            # Priority 2: Check Wi-Fi connection
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                self.current_ssid = result.stdout.strip()
                self.current_interface = "wlan0"
                
                # Get IP address and test connectivity
                ip_result = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5)
                if ip_result.returncode == 0 and ip_result.stdout.strip():
                    self.current_ip = ip_result.stdout.strip().split()[0]  # First IP
                    
                    # Verify internet connectivity
                    if self.test_internet_connectivity():
                        self.is_connected = True
                        return True
            
            # No connection found
            self.is_connected = False
            self.current_ip = None
            self.current_ssid = None
            self.current_interface = None
            return False
            
        except Exception as e:
            logger.error(f"❌ Error checking connection: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get detailed connection information"""
        if not self.check_connection():
            return {"connected": False}
        
        try:
            # Get additional network info
            info = {
                "connected": True,
                "ssid": self.current_ssid,
                "ip_address": self.current_ip
            }
            
            # Get signal strength
            try:
                signal_result = subprocess.run(["iwconfig", "wlan0"], capture_output=True, text=True, timeout=5)
                if "Signal level" in signal_result.stdout:
                    signal_line = [line for line in signal_result.stdout.split('\n') if "Signal level" in line]
                    if signal_line:
                        info["signal_strength"] = signal_line[0].split("Signal level=")[1].split()[0]
            except:
                pass
            
            # Get frequency
            try:
                freq_result = subprocess.run(["iwlist", "wlan0", "frequency"], capture_output=True, text=True, timeout=5)
                if "Current Frequency" in freq_result.stdout:
                    freq_line = [line for line in freq_result.stdout.split('\n') if "Current Frequency" in line]
                    if freq_line:
                        freq_info = freq_line[0]
                        info["frequency"] = freq_info
                        info["is_5ghz"] = "5." in freq_info
            except:
                pass
            
            # Add Tailscale information
            if Config.ENABLE_TAILSCALE:
                info["tailscale"] = self.check_tailscale_status()
            
            return info
            
        except Exception as e:
            logger.error(f"❌ Error getting connection info: {e}")
            return {"connected": self.is_connected, "ip_address": self.current_ip}
    
    def start_network_monitoring(self):
        """Start continuous network monitoring thread"""
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._network_monitor_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info(f"🔄 Network monitoring started (scan every {Config.NETWORK_SCAN_INTERVAL}s)")
    
    def stop_network_monitoring(self):
        """Stop network monitoring"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=2)
        logger.info("⏹️ Network monitoring stopped")
    
    def _network_monitor_loop(self):
        """Background network monitoring loop"""
        while self.monitoring_active:
            try:
                current_time = time.time()
                
                # Check current connection
                if not self.check_connection():
                    # No connection - attempt to reconnect
                    time_since_scan = current_time - self.last_scan_time
                    
                    if time_since_scan >= Config.NETWORK_SCAN_INTERVAL:
                        logger.info("🔍 No internet connection - attempting reconnection")
                        self.last_scan_time = current_time
                        
                        # Try Ethernet first
                        if Config.PREFER_ETHERNET and self.check_ethernet_connection():
                            logger.info("✅ Ethernet connection established")
                            continue
                        
                        # Try Wi-Fi connection
                        if self.connect_to_wifi():
                            logger.info("✅ Wi-Fi connection re-established")
                        else:
                            logger.warning("⚠️ Failed to reconnect - will retry in 10 seconds")
                
                # Monitor every 5 seconds, scan/retry every 10 seconds
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ Network monitoring error: {e}")
                time.sleep(5)
    
    def get_network_priority_status(self) -> Dict[str, Any]:
        """Get detailed network priority and status information"""
        status = {
            "ethernet_available": self.check_ethernet_connection() if Config.PREFER_ETHERNET else False,
            "wifi_available": False,
            "active_interface": self.current_interface,
            "connection_priority": "Ethernet -> Wi-Fi -> Scan" if Config.PREFER_ETHERNET else "Wi-Fi -> Scan",
            "monitoring_active": self.monitoring_active,
            "last_scan": self.last_scan_time
        }
        
        # Check Wi-Fi separately
        try:
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5)
            status["wifi_available"] = result.returncode == 0 and result.stdout.strip()
        except:
            pass
        
        return status
    
    def check_tailscale_status(self) -> Dict[str, Any]:
        """Check if Tailscale is installed and running"""
        try:
            # Check if tailscale is installed
            result = subprocess.run(["which", "tailscale"], capture_output=True, timeout=5)
            if result.returncode != 0:
                return {"installed": False, "running": False, "ip": None}
            
            # Check if tailscale is running
            status_result = subprocess.run(["sudo", "tailscale", "status", "--json"], 
                                         capture_output=True, text=True, timeout=10)
            
            if status_result.returncode != 0:
                return {"installed": True, "running": False, "ip": None}
            
            # Parse tailscale status
            try:
                import json
                status_data = json.loads(status_result.stdout)
                
                # Get tailscale IP
                tailscale_ip = None
                if "Self" in status_data and "TailscaleIPs" in status_data["Self"]:
                    tailscale_ips = status_data["Self"]["TailscaleIPs"]
                    if tailscale_ips:
                        tailscale_ip = tailscale_ips[0]  # First IP
                
                return {
                    "installed": True,
                    "running": status_data.get("BackendState") == "Running",
                    "ip": tailscale_ip,
                    "hostname": status_data.get("Self", {}).get("HostName", "unknown"),
                    "online": status_data.get("Self", {}).get("Online", False)
                }
                
            except json.JSONDecodeError:
                return {"installed": True, "running": False, "ip": None}
                
        except Exception as e:
            logger.debug(f"Tailscale status check error: {e}")
            return {"installed": False, "running": False, "ip": None}
    
    def install_tailscale(self) -> bool:
        """Install Tailscale automatically"""
        try:
            logger.info("🔧 Installing Tailscale for remote access...")
            
            # Download and install tailscale
            install_cmd = "curl -fsSL https://tailscale.com/install.sh | sh"
            result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                logger.error(f"❌ Tailscale installation failed: {result.stderr}")
                return False
            
            logger.info("✅ Tailscale installed successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error installing Tailscale: {e}")
            return False
    
    def setup_tailscale(self) -> bool:
        """Setup and start Tailscale"""
        try:
            tailscale_status = self.check_tailscale_status()
            
            # Install if not available and auto-install is enabled
            if not tailscale_status["installed"] and Config.TAILSCALE_AUTO_INSTALL:
                if not self.install_tailscale():
                    return False
                # Recheck status after installation
                tailscale_status = self.check_tailscale_status()
            
            if not tailscale_status["installed"]:
                logger.warning("⚠️ Tailscale not installed and auto-install disabled")
                return False
            
            # Start tailscale if not running
            if not tailscale_status["running"]:
                logger.info("🚀 Starting Tailscale...")
                up_result = subprocess.run(["sudo", "tailscale", "up", "--accept-routes"], 
                                         capture_output=True, text=True, timeout=60)
                
                if up_result.returncode != 0:
                    logger.error(f"❌ Failed to start Tailscale: {up_result.stderr}")
                    # Show helpful instructions
                    if "Logged out" in up_result.stderr or "authentication" in up_result.stderr.lower():
                        logger.info("📋 To complete setup, run: sudo tailscale up")
                        logger.info("📋 Then follow the login URL in the output")
                    return False
            
            # Verify final status
            final_status = self.check_tailscale_status()
            if final_status["running"] and final_status["ip"]:
                logger.info(f"✅ Tailscale running with IP: {final_status['ip']}")
                return True
            else:
                logger.warning("⚠️ Tailscale setup incomplete - may need manual authentication")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error setting up Tailscale: {e}")
            return False



# ===============================
# �📋 LOGGING SYSTEM
# ===============================

def setup_logging():
    """Setup comprehensive logging system"""
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging with both file and console output
    log_format = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Setup root logger
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_dir / Config.LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create logger
    logger = logging.getLogger('HailoAI')
    
    # Log system info
    logger.info("=" * 60)
    logger.info("🎧 HAILO AI DETECTION SYSTEM STARTED")
    logger.info("=" * 60)
    logger.info(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"💻 Platform: {sys.platform}")
    logger.info(f"📦 OpenCV: {cv2.__version__}")
    logger.info(f"📦 NumPy: {np.__version__}")
    logger.info(f"🤖 Hailo Available: {HAILO_AVAILABLE}")
    logger.info(f"📷 PiCamera Available: {PICAMERA_AVAILABLE}")
    
    return logger

# Initialize logging
logger = setup_logging()

# Initialize Wi-Fi manager (after logger setup)
wifi_manager = WiFiManager()

# ===============================
# 🔔 DISCORD NOTIFICATIONS
# ===============================

class DiscordNotifier:
    """Enhanced Discord notification system with comprehensive logging"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.last_notification = 0
        self.last_image_sent = 0  # Track last image send time
        self.cooldown_period = Config.NOTIFICATION_COOLDOWN
        self.image_cooldown = 5  # 5-second cooldown for images
        self.notification_count = 0
        self.failed_count = 0
        
        logger.info(f"🔔 Discord Notifier initialized with {self.cooldown_period}s cooldown, {self.image_cooldown}s image cooldown")
        
    def send_notification(self, message: str, detection_count: int, 
                         additional_info: Optional[Dict] = None, image_bytes: Optional[bytes] = None, image_name: Optional[str] = None) -> bool:
        """Send enhanced notification to Discord with detailed logging"""
        current_time = time.time()
        
        # Strict cooldown check
        time_since_last = current_time - self.last_notification
        if time_since_last < self.cooldown_period:
            logger.info(f"🔒 Notification blocked by cooldown ({time_since_last:.1f}s < {self.cooldown_period}s)")
            return False
        
        # Additional image cooldown check
        if image_bytes and image_name:
            time_since_last_image = current_time - self.last_image_sent
            if time_since_last_image < self.image_cooldown:
                remaining_time = self.image_cooldown - time_since_last_image
                logger.info(f"📸 Image sending blocked by cooldown (wait {remaining_time:.1f}s more)")
                logger.info(f"📢 Sending notification without image due to cooldown")
                # Send notification without image if image is blocked by cooldown
                return self.send_notification(message, detection_count, additional_info, None, None)
        
        try:
            # Prepare enhanced embed
            embed = {
                "title": "🎧 PPE Violation - Headphone Protection Required",
                "description": message,
                "color": 0xff0000,  # Red for safety alert
                "fields": [
                    {"name": "⚠️ PPE Violations", "value": str(detection_count), "inline": True},
                    {"name": "⏰ Detection Time", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": True},
                    {"name": "📍 Location", "value": "Raspberry Pi 5 + Hailo AI", "inline": True},
                    {"name": "📊 Total Alerts", "value": str(self.notification_count + 1), "inline": True},
                    {"name": "🤖 Detection Engine", "value": "Hailo TOP13" if HAILO_AVAILABLE else "CPU Fallback", "inline": True},
                    {"name": "📷 Camera Source", "value": "PiCamera2" if PICAMERA_AVAILABLE else "USB/Simulation", "inline": True}
                ],
                "footer": {"text": "Hailo AI Ear Protection Monitor v2.1"},
                "timestamp": datetime.now().isoformat()
            }
            
            # Add additional info if provided
            if additional_info:
                for key, value in additional_info.items():
                    embed["fields"].append({
                        "name": str(key), 
                        "value": str(value), 
                        "inline": True
                    })
            
            # Prepare payload with image support
            files = None
            payload = {
                "username": "⚠️ Safety Monitor Bot",
                "payload_json": json.dumps({"embeds": [embed]})
            }
            
            # Add image if provided as bytes
            if image_bytes and image_name:
                try:
                    from io import BytesIO
                    files = {'file': (image_name, BytesIO(image_bytes), 'image/jpeg')}
                    embed["image"] = {"url": f"attachment://{image_name}"}
                    payload["payload_json"] = json.dumps({"embeds": [embed]})
                    logger.info(f"📸 Adding evidence image: {image_name}")
                except Exception as img_error:
                    logger.warning(f"⚠️ Failed to prepare image bytes: {img_error}")
                    files = None
            
            logger.info(f"📤 Sending Discord safety alert (attempt {self.notification_count + 1})")
            
            # Send notification with limited retry to prevent duplicates
            max_retries = 1  # Reduced from 3 to 1 to prevent duplicate sends
            for attempt in range(max_retries):
                try:
                    if files:
                        response = requests.post(
                            self.webhook_url, 
                            data=payload,
                            files=files, 
                            timeout=15
                        )
                    else:
                        response = requests.post(
                            self.webhook_url, 
                            json={"username": payload["username"], "embeds": [embed]}, 
                            timeout=15,
                            headers={'Content-Type': 'application/json'}
                        )
                    
                    if response.status_code == 204:
                        self.last_notification = current_time
                        if files:  # If image was sent, update image timestamp
                            self.last_image_sent = current_time
                            logger.info(f"📸 Image sent successfully, next image available in {self.image_cooldown}s")
                        self.notification_count += 1
                        logger.info(f"✅ Discord safety alert sent successfully (#{self.notification_count})")
                        if image_name:
                            logger.info(f"📸 Evidence image uploaded: {image_name} (from memory)")
                        return True
                    elif response.status_code == 429:  # Rate limited
                        logger.warning(f"⏰ Discord rate limited, waiting...")
                        time.sleep(2)
                        continue
                    else:
                        logger.error(f"❌ Discord notification failed: HTTP {response.status_code}")
                        logger.error(f"Response: {response.text}")
                        
                except requests.exceptions.Timeout:
                    logger.warning(f"⏰ Discord notification timeout (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                except requests.exceptions.RequestException as e:
                    logger.error(f"🌐 Network error: {e}")
                    break
            
            self.failed_count += 1
            logger.error(f"❌ All notification attempts failed (total failures: {self.failed_count})")
            return False
                
        except Exception as e:
            self.failed_count += 1
            logger.error(f"💥 Unexpected error in Discord notification: {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
        finally:
            # Clean up BytesIO handles
            if files:
                try:
                    if hasattr(files['file'][1], 'close'):
                        files['file'][1].close()
                except:
                    pass
    
    def send_startup_notification(self) -> bool:
        """Send system startup notification"""
        message = "�️ Safety Monitoring System is now online and monitoring for PPE compliance!"
        additional_info = {
            "🔧 System Status": "Active Monitoring",
            "🎯 Detection Model": Config.HEF_PATH if HAILO_AVAILABLE else "CPU Fallback",
            "📏 Resolution": f"{Config.CAMERA_WIDTH}x{Config.CAMERA_HEIGHT}",
            "⚡ Detection Threshold": f"{Config.CONFIDENCE_THRESHOLD:.1%}",
            "🛡️ Monitoring": "PPE Headphones Compliance"
        }
        
        return self.send_notification(message, 0, additional_info)
    
    def send_network_notification(self, connection_info: Dict[str, Any]) -> bool:
        """Send network connection notification with IP address"""
        if not connection_info.get("connected", False):
            message = "📶 Network Status: Disconnected"
            additional_info = {
                "🔧 Status": "Wi-Fi Disconnected",
                "⚠️ Issue": "Unable to connect to network",
                "🔄 Action": "Attempting reconnection"
            }
        else:
            ip_address = connection_info.get("ip_address", "Unknown")
            ssid = connection_info.get("ssid", Config.WIFI_SSID)
            
            # Determine connection type
            freq_info = connection_info.get("frequency", "")
            is_5ghz = connection_info.get("is_5ghz", False)
            connection_type = "5GHz Wi-Fi" if is_5ghz else "2.4GHz Wi-Fi"
            
            message = f"📶 Network Connected: {ssid} ({connection_type})"
            additional_info = {
                "📍 Local IP": ip_address,
                "📶 Network": ssid,
                "🔗 Connection Type": connection_type,
                "📡 Frequency": freq_info if freq_info else "Unknown",
                "📊 Signal Strength": connection_info.get("signal_strength", "Unknown"),
                "✅ Status": "Connected",
                "🏠 Local SSH": f"ssh pi@{ip_address}" if ip_address != "Unknown" else "N/A"
            }
            
            # Add Tailscale information if available
            tailscale_info = connection_info.get("tailscale", {})
            if tailscale_info.get("running") and tailscale_info.get("ip"):
                additional_info["🌐 Tailscale IP"] = tailscale_info["ip"]
                additional_info["🔑 Remote SSH"] = f"ssh pi@{tailscale_info['ip']}"
                additional_info["🌍 Remote Access"] = "Available Worldwide"
            elif tailscale_info.get("installed"):
                additional_info["🌐 Tailscale"] = "Installed (Not Running)"
            else:
                additional_info["🌐 Tailscale"] = "Not Available"
        
        embed = {
            "title": "🌐 Network Status Update",
            "description": message,
            "color": 0x00ff00 if connection_info.get("connected") else 0xff0000,
            "fields": [],
            "footer": {"text": "Hailo AI Network Monitor"},
            "timestamp": datetime.now().isoformat()
        }
        
        # Add fields
        for key, value in additional_info.items():
            embed["fields"].append({
                "name": str(key),
                "value": str(value),
                "inline": True
            })
        
        try:
            payload = {
                "username": "🌐 Network Monitor Bot",
                "embeds": [embed]
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=15,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 204:
                logger.info("✅ Network notification sent to Discord")
                return True
            else:
                logger.warning(f"⚠️ Discord network notification failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to send network notification: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        current_time = time.time()
        return {
            "total_sent": self.notification_count,
            "total_failed": self.failed_count,
            "success_rate": (self.notification_count / (self.notification_count + self.failed_count) * 100) if (self.notification_count + self.failed_count) > 0 else 0,
            "last_sent": self.last_notification,
            "last_image_sent": self.last_image_sent,
            "next_notification_in": max(0, self.cooldown_period - (current_time - self.last_notification)),
            "next_image_in": max(0, self.image_cooldown - (current_time - self.last_image_sent))
        }

# ===============================
# 🤖 AI INFERENCE ENGINE
# ===============================

class HailoInference:
    """Enhanced Hailo AI inference with CPU fallback support"""
    
    def __init__(self, hef_path: str):
        self.hef_path = hef_path
        self.device = None
        self.network_group = None
        self.input_vstreams = None
        self.output_vstreams = None
        self.input_shape = None
        self.output_shapes = None
        self.inference_count = 0
        self.successful_inferences = 0
        self.failed_inferences = 0
        self.use_fallback = not HAILO_AVAILABLE
        
        logger.info(f"🤖 Initializing AI inference engine...")
        logger.info(f"📁 Model path: {hef_path}")
        logger.info(f"⚡ Using {'Hailo AI' if not self.use_fallback else 'CPU Fallback'} mode")
        
    def initialize(self) -> bool:
        """Initialize AI inference engine with fallback support"""
        
        # Check if model file exists
        if not Path(self.hef_path).exists():
            logger.warning(f"📁 Model file not found: {self.hef_path}")
            logger.warning("⚠️  Switching to simulation mode")
            self.use_fallback = True
            Config.SIMULATION_MODE = True
            return True
        
        if not HAILO_AVAILABLE:
            logger.info("💻 Using CPU fallback mode (Hailo platform not available)")
            self.use_fallback = True
            return True
        
        try:
            logger.info("🚀 Initializing Hailo AI hardware...")
            
            # Load HEF
            logger.info("📂 Loading HEF model...")
            hef = HEF(self.hef_path)
            
            # Create VDevice
            logger.info("🔌 Connecting to Hailo device...")
            try:
                # Try different VDevice initialization methods
                try:
                    self.device = VDevice()
                except TypeError:
                    # Try alternative initialization
                    from hailo_platform import Device
                    self.device = Device()
            except Exception as device_err:
                logger.error(f"Failed to create Hailo device: {device_err}")
                raise device_err
            
            # Configure network group
            logger.info("⚙️ Configuring network group...")
            configure_params = ConfigureParams.create_from_hef(hef, interface=HailoStreamInterface.PCIe)
            network_groups = self.device.configure(hef, configure_params)
            self.network_group = network_groups[0]
            
            # Get input/output information
            self.input_vstream_info = hef.get_input_vstream_infos()[0]
            self.output_vstream_infos = hef.get_output_vstream_infos()
            
            self.input_shape = self.input_vstream_info.shape
            self.output_shapes = [info.shape for info in self.output_vstream_infos]
            
            # Create VStreams
            logger.info("🌊 Setting up data streams...")
            input_params = InputVStreamParams.make_from_network_group(
                self.network_group, format_type=FormatType.UINT8)[0]
            output_params = OutputVStreamParams.make_from_network_group(
                self.network_group, format_type=FormatType.FLOAT32)
            
            self.input_vstreams = InferVStreams(self.device, input_params, [])
            self.output_vstreams = InferVStreams(self.device, [], output_params)
            
            logger.info("✅ Hailo AI initialized successfully!")
            logger.info(f"📊 Input shape: {self.input_shape}")
            logger.info(f"📊 Output shapes: {self.output_shapes}")
            
            self.use_fallback = False
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Hailo AI: {e}")
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
            logger.warning("⚠️  Switching to CPU fallback mode")
            self.use_fallback = True
            return True
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for inference"""
        if self.use_fallback:
            # Simple preprocessing for CPU fallback
            target_size = (640, 480)  # Default size
            resized = cv2.resize(image, target_size)
            return resized
        else:
            # Hailo-specific preprocessing
            h, w, c = self.input_shape
            resized = cv2.resize(image, (w, h))
            
            # Convert BGR to RGB if needed
            if c == 3:
                resized = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # Normalize to 0-255 (UINT8)
            processed = np.asarray(resized, dtype=np.uint8)
            return processed
    
    def cpu_fallback_inference(self, image: np.ndarray) -> List[Dict]:
        """CPU fallback inference to detect exposed ears (left_ear, right_ear)"""
        try:
            logger.debug("💻 Running exposed ear detection fallback...")
            
            # Convert to different color spaces for analysis
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # Use Haar cascade for person detection (if available)
            detections = []
            
            try:
                # Try to use OpenCV's built-in person detection
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for (x, y, w, h) in faces:
                    # First, add person detection
                    person_x = max(0, x - int(w * 0.2))
                    person_y = max(0, y - int(h * 0.1))
                    person_w = int(w * 1.4)
                    person_h = int(h * 2.0)  # Include body area
                    
                    detections.append({
                        'bbox': [person_x, person_y, person_x + person_w, person_y + person_h],
                        'confidence': 0.85,
                        'class_id': 2,  # people class_id
                        'class_name': 'people'
                    })
                    
                    # Check for headphones around head area using color/edge analysis
                    head_roi = gray[y:y+h, x:x+w]
                    
                    # Simple headphone detection - look for dark regions around ears
                    # This is a simplified heuristic
                    has_headphones = False
                    
                    # Check ear regions for dark objects (headphones)
                    left_ear_roi = gray[y+int(h*0.2):y+int(h*0.6), max(0, x-int(w*0.2)):x]
                    right_ear_roi = gray[y+int(h*0.2):y+int(h*0.6), x+w:min(gray.shape[1], x+w+int(w*0.2))]
                    
                    if left_ear_roi.size > 0 and right_ear_roi.size > 0:
                        # Check for consistent dark regions (headphones)
                        left_dark = np.mean(left_ear_roi) < 80  # Dark threshold
                        right_dark = np.mean(right_ear_roi) < 80
                        
                        # Also check for edges that might indicate headphones structure
                        left_edges = cv2.Canny(left_ear_roi, 50, 150)
                        right_edges = cv2.Canny(right_ear_roi, 50, 150)
                        
                        left_has_structure = np.sum(left_edges) > 100
                        right_has_structure = np.sum(right_edges) > 100
                        
                        # If both sides have dark regions or structural edges, likely headphones
                        if (left_dark and right_dark) or (left_has_structure and right_has_structure):
                            has_headphones = True
                    
                    if has_headphones:
                        # Add headphones detection
                        hp_x = max(0, x - int(w * 0.2))
                        hp_y = y + int(h * 0.1)
                        hp_w = int(w * 1.4)
                        hp_h = int(h * 0.8)
                        
                        detections.append({
                            'bbox': [hp_x, hp_y, hp_x + hp_w, hp_y + hp_h],
                            'confidence': 0.75,
                            'class_id': 0,  # headphones class_id
                            'class_name': 'headphones'
                        })
                    else:
                        # Only add exposed ears if NO headphones detected
                        left_ear_x = max(0, x - int(w * 0.15))
                        left_ear_y = y + int(h * 0.2)
                        left_ear_w = int(w * 0.25)
                        left_ear_h = int(h * 0.3)
                        
                        right_ear_x = x + int(w * 0.9)
                        right_ear_y = y + int(h * 0.2)
                        right_ear_w = int(w * 0.25)
                        right_ear_h = int(h * 0.3)
                        
                        # Add exposed ears
                        detections.append({
                            'bbox': [left_ear_x, left_ear_y, left_ear_x + left_ear_w, left_ear_y + left_ear_h],
                            'confidence': 0.8,
                            'class_id': 1,
                            'class_name': 'left_ear'
                        })
                        
                        detections.append({
                            'bbox': [right_ear_x, right_ear_y, right_ear_x + right_ear_w, right_ear_y + right_ear_h],
                            'confidence': 0.8,
                            'class_id': 3,
                            'class_name': 'right_ear'
                        })
                    
            except Exception as cascade_error:
                logger.debug(f"Haar cascade detection failed: {cascade_error}")
                
                # Fallback to edge-based detection for people and objects
                edges = cv2.Canny(gray, 50, 150)
                contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                # Sort contours by area (largest first)
                contours = sorted(contours, key=cv2.contourArea, reverse=True)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    
                    # Look for person-like shapes (large, vertical)
                    if area > 10000:  # Large area for person
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = w / h if h > 0 else 0
                        
                        # Person-like aspect ratio (taller than wide)
                        if 0.3 < aspect_ratio < 0.8:
                            detections.append({
                                'bbox': [x, y, x + w, y + h],
                                'confidence': 0.7,
                                'class_id': 2,
                                'class_name': 'people'
                            })
                    
                    # Look for ear-like shapes only if no people detected yet
                    elif area > 200 and area < 5000 and not any(d['class_name'] == 'people' for d in detections):
                        x, y, w, h = cv2.boundingRect(contour)
                        aspect_ratio = w / h if h > 0 else 0
                        
                        # Ear-like aspect ratio (roughly square to slightly oval)
                        if 0.6 < aspect_ratio < 1.4:
                            confidence = min(0.6, area / 2000)
                            
                            if confidence > Config.CONFIDENCE_THRESHOLD:
                                # Determine if it's likely left or right ear based on position
                                img_center = image.shape[1] // 2
                                if x < img_center:
                                    # Left side of image = left ear
                                    detections.append({
                                        'bbox': [x, y, x + w, y + h],
                                        'confidence': confidence,
                                        'class_id': 1,
                                        'class_name': 'left_ear'
                                    })
                                else:
                                    # Right side of image = right ear
                                    detections.append({
                                        'bbox': [x, y, x + w, y + h],
                                        'confidence': confidence,
                                        'class_id': 3,
                                        'class_name': 'right_ear'
                                    })
            
            # Simulate realistic PPE scenarios for demo purposes
            if Config.SIMULATION_MODE and len(detections) == 0:
                import random
                if random.random() < 0.15:  # 15% chance of simulation
                    h, w = image.shape[:2]
                    
                    # Always add a person first
                    person_w, person_h = int(w * 0.35), int(h * 0.7)
                    person_x = random.randint(int(w * 0.1), w - person_w - int(w * 0.1))
                    person_y = random.randint(int(h * 0.1), h - person_h - int(h * 0.1))
                    
                    detections.append({
                        'bbox': [person_x, person_y, person_x + person_w, person_y + person_h],
                        'confidence': random.uniform(0.85, 0.95),
                        'class_id': 2,
                        'class_name': 'people'
                    })
                    
                    # 70% chance person has headphones (compliant)
                    if random.random() < 0.7:
                        # Compliant scenario - person with headphones
                        hp_w, hp_h = int(person_w * 0.6), int(person_h * 0.25)
                        hp_x = person_x + int(person_w * 0.2)
                        hp_y = person_y + int(person_h * 0.05)
                        
                        detections.append({
                            'bbox': [hp_x, hp_y, hp_x + hp_w, hp_y + hp_h],
                            'confidence': random.uniform(0.75, 0.9),
                            'class_id': 0,
                            'class_name': 'headphones'
                        })
                        
                        logger.info(f"✅ Simulation: Person with headphones (COMPLIANT)")
                    else:
                        # Violation scenario - exposed ears without headphones
                        ear_w, ear_h = int(person_w * 0.15), int(person_h * 0.12)
                        
                        # Left ear
                        left_ear_x = person_x - int(ear_w * 0.3)
                        left_ear_y = person_y + int(person_h * 0.15)
                        
                        # Right ear  
                        right_ear_x = person_x + person_w - int(ear_w * 0.7)
                        right_ear_y = person_y + int(person_h * 0.15)
                        
                        detections.extend([
                            {
                                'bbox': [left_ear_x, left_ear_y, left_ear_x + ear_w, left_ear_y + ear_h],
                                'confidence': random.uniform(0.8, 0.9),
                                'class_id': 1,
                                'class_name': 'left_ear'
                            },
                            {
                                'bbox': [right_ear_x, right_ear_y, right_ear_x + ear_w, right_ear_y + ear_h],
                                'confidence': random.uniform(0.8, 0.9),
                                'class_id': 3,
                                'class_name': 'right_ear'
                            }
                        ])
                        
                        logger.warning(f"⚠️ Simulation: Person with exposed ears (VIOLATION)")
            
            return detections
            
        except Exception as e:
            logger.error(f"❌ CPU fallback inference error: {e}")
            return []
    
    def postprocess_output(self, outputs: List[np.ndarray], 
                          original_shape: Tuple[int, int]) -> List[Dict]:
        """Post-process Hailo output to get detections"""
        detections = []
        
        try:
            logger.debug(f"🔍 Processing {len(outputs)} output tensors")
            
            # Assuming YOLO-style output
            for idx, output in enumerate(outputs):
                logger.debug(f"   Output {idx} shape: {output.shape}")
                
                # Handle different output formats
                if len(output.shape) == 1:
                    # Calculate grid size based on output size
                    num_classes = len(Config.CLASS_NAMES)
                    elements_per_detection = 5 + num_classes  # x, y, w, h, conf + classes
                    
                    if output.shape[0] % elements_per_detection == 0:
                        num_detections = output.shape[0] // elements_per_detection
                        grid_size = int(np.sqrt(num_detections))
                        
                        if grid_size * grid_size == num_detections:
                            output = output.reshape((grid_size, grid_size, elements_per_detection))
                        else:
                            # Linear arrangement
                            output = output.reshape((num_detections, elements_per_detection))
                
                # Process detections
                if len(output.shape) == 3:  # Grid format
                    detections.extend(self._process_grid_output(output, original_shape))
                elif len(output.shape) == 2:  # Linear format
                    detections.extend(self._process_linear_output(output, original_shape))
            
            # Apply NMS
            detections = self.apply_nms(detections)
            logger.debug(f"✅ Final detections after NMS: {len(detections)}")
            
        except Exception as e:
            logger.error(f"❌ Error in postprocessing: {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        
        return detections
    
    def _process_grid_output(self, output: np.ndarray, original_shape: Tuple[int, int]) -> List[Dict]:
        """Process grid-format output"""
        detections = []
        h, w = original_shape
        grid_h, grid_w, channels = output.shape
        
        for i in range(grid_h):
            for j in range(grid_w):
                detection = output[i, j]
                
                # Extract confidence (objectness)
                confidence = detection[4]
                
                if confidence > Config.CONFIDENCE_THRESHOLD:
                    # Extract bounding box
                    x_center = (detection[0] + j) / grid_w
                    y_center = (detection[1] + i) / grid_h
                    box_w = detection[2]
                    box_h = detection[3]
                    
                    # Convert to pixel coordinates
                    x1 = int((x_center - box_w/2) * w)
                    y1 = int((y_center - box_h/2) * h)
                    x2 = int((x_center + box_w/2) * w)
                    y2 = int((y_center + box_h/2) * h)
                    
                    # Extract class probabilities
                    class_scores = detection[5:]
                    class_id = np.argmax(class_scores)
                    class_confidence = class_scores[class_id]
                    
                    final_confidence = confidence * class_confidence
                    
                    if final_confidence > Config.CONFIDENCE_THRESHOLD:
                        detections.append({
                            'bbox': [max(0, x1), max(0, y1), min(w, x2), min(h, y2)],
                            'confidence': final_confidence,
                            'class_id': class_id,
                            'class_name': Config.CLASS_NAMES[class_id] if class_id < len(Config.CLASS_NAMES) else 'unknown'
                        })
        
        return detections
    
    def _process_linear_output(self, output: np.ndarray, original_shape: Tuple[int, int]) -> List[Dict]:
        """Process linear-format output"""
        detections = []
        h, w = original_shape
        
        for detection in output:
            confidence = detection[4]
            
            if confidence > Config.CONFIDENCE_THRESHOLD:
                # Extract bounding box (assuming normalized coordinates)
                x_center = detection[0]
                y_center = detection[1]
                box_w = detection[2]
                box_h = detection[3]
                
                # Convert to pixel coordinates
                x1 = int((x_center - box_w/2) * w)
                y1 = int((y_center - box_h/2) * h)
                x2 = int((x_center + box_w/2) * w)
                y2 = int((y_center + box_h/2) * h)
                
                # Extract class probabilities
                class_scores = detection[5:]
                class_id = np.argmax(class_scores)
                class_confidence = class_scores[class_id]
                
                final_confidence = confidence * class_confidence
                
                if final_confidence > Config.CONFIDENCE_THRESHOLD:
                    detections.append({
                        'bbox': [max(0, x1), max(0, y1), min(w, x2), min(h, y2)],
                        'confidence': final_confidence,
                        'class_id': class_id,
                        'class_name': Config.CLASS_NAMES[class_id] if class_id < len(Config.CLASS_NAMES) else 'unknown'
                    })
        
        return detections
    
    def apply_nms(self, detections: List[Dict], iou_threshold: float = None) -> List[Dict]:
        """Apply Non-Maximum Suppression"""
        if not detections:
            return []
        
        if iou_threshold is None:
            iou_threshold = Config.NMS_THRESHOLD
        
        # Sort by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        
        keep = []
        while detections:
            current = detections.pop(0)
            keep.append(current)
            
            # Remove overlapping detections
            detections = [det for det in detections 
                         if self.calculate_iou(current['bbox'], det['bbox']) < iou_threshold]
        
        return keep[:Config.MAX_DETECTIONS_PER_FRAME]
    
    def calculate_iou(self, box1: List[int], box2: List[int]) -> float:
        """Calculate Intersection over Union"""
        x1_1, y1_1, x2_1, y2_1 = box1
        x1_2, y1_2, x2_2, y2_2 = box2
        
        # Calculate intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i <= x1_i or y2_i <= y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Calculate union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def inference(self, image: np.ndarray) -> List[Dict]:
        """Run inference on image with automatic fallback"""
        self.inference_count += 1
        
        try:
            if self.use_fallback:
                # Use CPU fallback
                detections = self.cpu_fallback_inference(image)
            else:
                # Use Hailo AI
                # Preprocess
                processed_image = self.preprocess_image(image)
                
                # Run inference
                input_data = [processed_image]
                output_data = self.network_group.infer(input_data)
                
                # Postprocess
                detections = self.postprocess_output(output_data, image.shape[:2])
            
            self.successful_inferences += 1
            
            if len(detections) > 0:
                logger.info(f"🎯 Inference #{self.inference_count}: Found {len(detections)} detections")
            
            return detections
            
        except Exception as e:
            self.failed_inferences += 1
            logger.error(f"❌ Inference #{self.inference_count} failed: {e}")
            
            # Try fallback if Hailo fails
            if not self.use_fallback:
                logger.warning("⚠️  Hailo inference failed, trying CPU fallback...")
                try:
                    return self.cpu_fallback_inference(image)
                except Exception as fallback_error:
                    logger.error(f"❌ CPU fallback also failed: {fallback_error}")
            
            return []
    
    def get_inference_stats(self) -> Dict[str, Any]:
        """Get inference statistics"""
        total = self.inference_count
        success_rate = (self.successful_inferences / total * 100) if total > 0 else 0
        
        return {
            "total_inferences": total,
            "successful": self.successful_inferences,
            "failed": self.failed_inferences,
            "success_rate": success_rate,
            "engine": "CPU Fallback" if self.use_fallback else "Hailo AI"
        }
    
    def cleanup(self):
        """Cleanup Hailo resources"""
        try:
            if self.network_group:
                self.network_group.release()
            if self.device:
                self.device.release()
            logger.info("Hailo resources cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

# ===============================
# 📷 CAMERA SYSTEM
# ===============================

class CameraSystem:
    """Enhanced camera system with multiple source support"""
    
    def __init__(self):
        self.camera = None
        self.camera_type = None
        self.frame_count = 0
        
    def initialize(self) -> bool:
        """Initialize camera with automatic fallback"""
        logger.info("📷 Initializing camera system...")
        
        # Try PiCamera2 first (only if available)
        if PICAMERA_AVAILABLE:
            try:
                logger.info("📷 Trying PiCamera2...")
                # Additional check for camera hardware
                try:
                    self.camera = Picamera2()
                    config = self.camera.create_preview_configuration(
                        main={"size": (Config.CAMERA_WIDTH, Config.CAMERA_HEIGHT)}
                    )
                    self.camera.configure(config)
                    self.camera.start()
                    self.camera_type = "picamera2"
                    logger.info("✅ PiCamera2 initialized successfully")
                    time.sleep(2)  # Allow camera to warm up
                    
                    # Test capture
                    test_frame = self.camera.capture_array()
                    if test_frame is not None:
                        logger.info(f"✅ PiCamera2 test capture successful: {test_frame.shape}")
                        return True
                    else:
                        raise Exception("Test capture returned None")
                        
                except Exception as camera_err:
                    logger.warning(f"⚠️  PiCamera2 hardware error: {camera_err}")
                    if self.camera:
                        try:
                            self.camera.stop()
                            self.camera.close()
                        except:
                            pass
                        self.camera = None
                    raise camera_err
                    
            except Exception as e:
                logger.warning(f"⚠️  PiCamera2 failed: {e}")
                logger.info("🔄 Falling back to USB camera...")
        
        # Try USB camera
        for camera_id in [0, 1, 2]:  # Try multiple camera IDs
            try:
                logger.info(f"📹 Trying USB camera {camera_id}...")
                self.camera = cv2.VideoCapture(camera_id)
                
                if self.camera.isOpened():
                    # Set camera properties
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
                    self.camera.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
                    
                    # Test capture
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        self.camera_type = f"usb_{camera_id}"
                        logger.info(f"✅ USB camera {camera_id} initialized successfully")
                        return True
                
                self.camera.release()
                self.camera = None
                
            except Exception as e:
                logger.warning(f"⚠️  USB camera {camera_id} failed: {e}")
        
        # Fallback to simulation mode
        logger.warning("⚠️  No physical camera found, using simulation mode")
        self.camera_type = "simulation"
        Config.SIMULATION_MODE = True
        return True
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture frame from camera"""
        try:
            if self.camera_type == "simulation":
                # Generate simulation frame
                frame = np.random.randint(0, 255, (Config.CAMERA_HEIGHT, Config.CAMERA_WIDTH, 3), dtype=np.uint8)
                # Add some pattern to make it look more realistic
                cv2.rectangle(frame, (50, 50), (Config.CAMERA_WIDTH-50, Config.CAMERA_HEIGHT-50), (100, 150, 200), 2)
                cv2.putText(frame, "SIMULATION MODE", (Config.CAMERA_WIDTH//2-100, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Frame {self.frame_count}", (10, Config.CAMERA_HEIGHT-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                self.frame_count += 1
                return frame
            
            elif self.camera_type == "picamera2":
                frame = self.camera.capture_array()
                # Convert RGB to BGR for OpenCV
                if len(frame.shape) == 3 and frame.shape[2] == 3:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                self.frame_count += 1
                return frame
            
            elif self.camera_type.startswith("usb_"):
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    self.frame_count += 1
                    return frame
                else:
                    logger.warning("⚠️  Failed to read from USB camera")
                    return None
            
        except Exception as e:
            logger.error(f"❌ Error capturing frame: {e}")
            return None
    
    def cleanup(self):
        """Cleanup camera resources"""
        try:
            if self.camera_type == "picamera2" and self.camera:
                self.camera.stop()
                self.camera.close()
            elif self.camera_type.startswith("usb_") and self.camera:
                self.camera.release()
            logger.info("✅ Camera cleanup completed")
        except Exception as e:
            logger.error(f"❌ Camera cleanup error: {e}")

# ===============================
# 🗥️ MAIN DETECTION SYSTEM
# ===============================

class SafetyMonitoringSystem:
    """Enhanced main detection system with comprehensive features"""
    
    def __init__(self):
        self.camera_system = None
        self.hailo_inference = None
        self.discord_notifier = None
        self.running = False
        self.frame_count = 0
        self.detection_count = 0
        self.total_detections = 0
        self.fps_counter = 0
        self.fps_start_time = time.time()
        self.current_fps = 0.0
        self.start_time = datetime.now()
        self.last_stats_log = time.time()
        self.last_notification_frame = -1  # Track last frame that sent notification
        
    def initialize(self) -> bool:
        """Initialize all system components with comprehensive error handling"""
        logger.info("🚀 Initializing Safety Monitoring System...")
        logger.info("=" * 50)
        
        # Initialize camera system
        logger.info("📷 Step 1: Camera System")
        self.camera_system = CameraSystem()
        if not self.camera_system.initialize():
            logger.error("❌ Failed to initialize camera system")
            return False
        
        # Initialize AI inference
        logger.info("\n🤖 Step 2: AI Inference Engine")
        self.hailo_inference = HailoInference(Config.HEF_PATH)
        if not self.hailo_inference.initialize():
            logger.error("❌ Failed to initialize AI inference")
            return False
        
        # Initialize Discord notifier
        logger.info("\n🔔 Step 3: Discord Notifications")
        self.discord_notifier = DiscordNotifier(Config.DISCORD_WEBHOOK)
        
        # Send startup notification
        startup_success = self.discord_notifier.send_startup_notification()
        if startup_success:
            logger.info("✅ Startup notification sent to Discord")
        else:
            logger.warning("⚠️  Startup notification failed (continuing anyway)")
        
        logger.info("\n" + "=" * 50)
        logger.info("🎉 System initialized successfully!")
        logger.info(f"📷 Camera: {self.camera_system.camera_type}")
        logger.info(f"🤖 AI Engine: {'Hailo AI' if not self.hailo_inference.use_fallback else 'CPU Fallback'}")
        logger.info(f"🔔 Discord: {'Enabled' if Config.DISCORD_WEBHOOK else 'Disabled'}")
        logger.info(f"📏 Resolution: {Config.CAMERA_WIDTH}x{Config.CAMERA_HEIGHT}")
        logger.info(f"⚡ Confidence: {Config.CONFIDENCE_THRESHOLD:.1%}")
        logger.info("=" * 50)
        
        return True
    
    def draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        """Draw bounding boxes and labels on frame"""
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            class_name = detection['class_name']
            class_id = detection['class_id']
            
            x1, y1, x2, y2 = bbox
            color = Config.COLORS[class_id % len(Config.COLORS)]
            
            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label with background
            label = f"{class_name}: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            
            # Background for text
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0] + 5, y1), color, -1)
            
            # Text
            cv2.putText(frame, label, (x1 + 2, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw center point
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            cv2.circle(frame, (center_x, center_y), 3, color, -1)
        
        return frame

    def draw_enhanced_info(self, frame: np.ndarray, current_detections: int) -> np.ndarray:
        """Draw comprehensive system information on frame"""
        h, w = frame.shape[:2]
        
        # Main info panel (top-left)
        info_text = [
            f"FPS: {self.current_fps:.1f}",
            f"Current: {current_detections}",
            f"Total: {self.total_detections}",
            f"Frame: {self.frame_count}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        # Draw background for info panel
        panel_height = len(info_text) * 25 + 10
        cv2.rectangle(frame, (5, 5), (250, panel_height), (0, 0, 0), -1)
        cv2.rectangle(frame, (5, 5), (250, panel_height), (0, 255, 255), 2)
        
        y_offset = 25
        for i, text in enumerate(info_text):
            y_pos = y_offset + (i * 25)
            cv2.putText(frame, text, (10, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        
        # System status panel (top-right)
        status_info = [
            f"{self.hailo_inference.get_inference_stats()['engine']}",
            f"{self.camera_system.camera_type.title()}",
            f"Discord: {'ON' if Config.DISCORD_WEBHOOK else 'OFF'}"
        ]
        
        status_x = w - 200
        cv2.rectangle(frame, (status_x, 5), (w - 5, 85), (0, 0, 0), -1)
        cv2.rectangle(frame, (status_x, 5), (w - 5, 85), (0, 255, 0), 2)
        
        for i, text in enumerate(status_info):
            y_pos = 25 + (i * 25)
            cv2.putText(frame, text, (status_x + 5, y_pos), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        # Runtime info (bottom)
        runtime = str(datetime.now() - self.start_time).split('.')[0]
        runtime_text = f"Runtime: {runtime}"
        
        text_size = cv2.getTextSize(runtime_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
        cv2.rectangle(frame, (5, h - 35), (text_size[0] + 15, h - 5), (0, 0, 0), -1)
        cv2.putText(frame, runtime_text, (10, h - 15), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return frame
    
    def log_statistics(self):
        """Log comprehensive system statistics"""
        runtime = datetime.now() - self.start_time
        avg_fps = self.frame_count / runtime.total_seconds() if runtime.total_seconds() > 0 else 0
        
        inference_stats = self.hailo_inference.get_inference_stats()
        discord_stats = self.discord_notifier.get_stats()
        
        logger.info("📊 SYSTEM STATISTICS")
        logger.info(f"   Runtime: {str(runtime).split('.')[0]}")
        logger.info(f"   Frames processed: {self.frame_count}")
        logger.info(f"   Average FPS: {avg_fps:.1f}")
        logger.info(f"   Current FPS: {self.current_fps:.1f}")
        logger.info(f"   Total detections: {self.total_detections}")
        logger.info(f"   AI Engine: {inference_stats['engine']}")
        logger.info(f"   AI Success rate: {inference_stats['success_rate']:.1f}%")
        next_notification = f", next in {discord_stats['next_notification_in']:.1f}s" if discord_stats['next_notification_in'] > 0 else ""
        next_image = f", next image in {discord_stats['next_image_in']:.1f}s" if discord_stats['next_image_in'] > 0 else ""
        logger.info(f"   Discord sent: {discord_stats['total_sent']} ({discord_stats['success_rate']:.1f}% success{next_notification}{next_image})")
        logger.info(f"   Camera: {self.camera_system.camera_type}")
        
        # Add network status with priority information
        if wifi_manager.check_connection():
            connection_info = wifi_manager.get_connection_info()
            connection_type = "5GHz" if connection_info.get("is_5ghz") else "2.4GHz" if wifi_manager.current_interface == "wlan0" else "Ethernet"
            logger.info(f"   Network: {wifi_manager.current_ssid} ({connection_type}) via {wifi_manager.current_interface} - {wifi_manager.current_ip}")
            logger.info(f"   Monitoring: {'✅ Active' if wifi_manager.monitoring_active else '❌ Inactive'}")
        else:
            logger.info(f"   Network: Disconnected (auto-retry every {Config.NETWORK_SCAN_INTERVAL}s)")
            logger.info(f"   Monitoring: {'✅ Active' if wifi_manager.monitoring_active else '❌ Inactive'}")
    
    def process_frame(self) -> bool:
        """Process single frame with comprehensive error handling and logging"""
        try:
            # Capture frame
            frame = self.camera_system.capture_frame()
            if frame is None:
                logger.warning("⚠️  Failed to capture frame")
                return False
            
            # Run inference
            detections = self.hailo_inference.inference(frame)
            
            # Analyze detections for PPE compliance
            people_detections = [d for d in detections if d['class_name'] == 'people']
            headphones_detections = [d for d in detections if d['class_name'] == 'headphones']
            exposed_ear_detections = [d for d in detections if d['class_name'] in ['left_ear', 'right_ear']]
            
            # Enhanced PPE compliance checking
            violation_detections = []
            is_compliant = False
            
            # PRIMARY RULE: If people detected WITH headphones = COMPLIANT
            if len(people_detections) > 0 and len(headphones_detections) > 0:
                is_compliant = True
                logger.info(f"✅ PPE COMPLIANT: {len(people_detections)} person(s) with {len(headphones_detections)} headphone(s)")
            
            # VIOLATION RULES (only if not compliant)
            elif not is_compliant:
                # Case 1: People detected but no headphones
                if len(people_detections) > 0 and len(headphones_detections) == 0:
                    violation_detections.extend(people_detections)
                    logger.warning(f"⚠️ VIOLATION: {len(people_detections)} person(s) without headphones")
                
                # Case 2: Exposed ears without headphones (no people detected)
                elif len(people_detections) == 0 and len(exposed_ear_detections) > 0 and len(headphones_detections) == 0:
                    violation_detections.extend(exposed_ear_detections)
                    logger.warning(f"⚠️ VIOLATION: {len(exposed_ear_detections)} exposed ear(s) without headphone coverage")
                
                # Case 3: Mixed detection - exposed ears + people but no headphones
                elif len(people_detections) > 0 and len(exposed_ear_detections) > 0 and len(headphones_detections) == 0:
                    violation_detections.extend(people_detections)
                    violation_detections.extend(exposed_ear_detections)
                    logger.warning(f"⚠️ VIOLATION: {len(people_detections)} person(s) + {len(exposed_ear_detections)} exposed ear(s) without headphones")
            
            # NO DETECTION case
            if len(people_detections) == 0 and len(headphones_detections) == 0 and len(exposed_ear_detections) == 0:
                logger.debug("ℹ️ No relevant objects detected in frame")
            
            # Count violations only if not compliant
            current_detection_count = 0 if is_compliant else len(violation_detections)
            
            # Update statistics only for violations
            if current_detection_count > 0 and not is_compliant:
                self.detection_count += current_detection_count
                self.total_detections += current_detection_count
                
                # Prevent duplicate notifications in same frame
                if self.last_notification_frame == self.frame_count:
                    logger.info(f"🔒 Notification already sent for frame {self.frame_count}, skipping")
                    # Still draw detections and continue processing
                    frame = self.draw_detections(frame, detections)
                    frame = self.draw_enhanced_info(frame, current_detection_count)
                    self.frame_count += 1
                    return True
                
                # Prepare evidence image in memory (no disk saving)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                evidence_filename = f"safety_violation_{timestamp}_frame_{self.frame_count}.jpg"
                
                # Draw violation detections on copy of frame
                evidence_frame = self.draw_detections(frame.copy(), violation_detections)
                evidence_frame = self.draw_enhanced_info(evidence_frame, current_detection_count)
                
                # Convert image to bytes for Discord (no file saving)
                success_encode, img_encoded = cv2.imencode('.jpg', evidence_frame)
                if success_encode:
                    image_bytes = img_encoded.tobytes()
                    logger.warning(f"⚠️ SAFETY VIOLATION DETECTED! Evidence prepared for Discord: {evidence_filename}")
                else:
                    image_bytes = None
                    logger.error("❌ Failed to encode evidence image")
                
                # Send Discord notification with image
                violation_types = [d['class_name'] for d in violation_detections]
                violation_summary = ', '.join(set(violation_types))
                message = f"🚨 PPE VIOLATION: {current_detection_count} person(s)/ear(s) without proper headphone protection! ({violation_summary})"                
                additional_info = {
                    "📊 Frame Number": str(self.frame_count + 1),
                    "🎯 Current FPS": f"{self.current_fps:.1f}",
                    "⚠️ Total Violations": str(self.total_detections),
                    "� People Detected": str(len(people_detections)),
                    "🎧 Headphones Detected": str(len(headphones_detections)),
                    "👂 Exposed Ears": str(len(exposed_ear_detections)),
                    "❌ Violations": violation_summary,
                    "⏱️ Runtime": str(datetime.now() - self.start_time).split('.')[0],
                    "📸 Evidence": "Image attached (not saved locally)",
                    "🔧 Action Required": "Ensure all personnel wear proper headphone PPE"
                }
                
                success = self.discord_notifier.send_notification(
                    message, current_detection_count, additional_info, image_bytes, evidence_filename
                )
                
                if success:
                    self.last_notification_frame = self.frame_count  # Mark frame as notified
                    logger.warning(f"🚨 Discord safety alert sent for {current_detection_count} violations")
                else:
                    logger.warning(f"❌ Failed to send Discord notification for frame {self.frame_count}")
                
                # Log comprehensive safety violation
                logger.warning(f"⚠️ PPE VIOLATION: {current_detection_count} person(s)/ear(s) without headphones - {violation_summary} (Frame {self.frame_count})")
                logger.info(f"📊 Detection Summary: {len(people_detections)} people, {len(headphones_detections)} headphones, {len(exposed_ear_detections)} exposed ears")
            
            # Draw detections
            frame = self.draw_detections(frame, detections)
            
            # Calculate FPS
            self.fps_counter += 1
            current_time = time.time()
            if current_time - self.fps_start_time >= 1.0:
                self.current_fps = self.fps_counter / (current_time - self.fps_start_time)
                self.fps_counter = 0
                self.fps_start_time = current_time
            
            # Draw enhanced info
            frame = self.draw_enhanced_info(frame, current_detection_count)
            
            # Display frame (no saving in headless mode)
            if Config.HEADLESS_MODE:
                # In headless mode, images are only sent to Discord (not saved locally)
                if current_detection_count > 0:
                    logger.info(f"📸 Evidence image sent to Discord (not saved locally)")
            else:
                # Normal display mode
                try:
                    cv2.imshow("🎧 Hailo AI - Headphones Detection v2.0", frame)
                except Exception as display_error:
                    logger.warning(f"⚠️  Display error: {display_error}")
                    logger.info("🔄 Switching to headless mode")
                    Config.HEADLESS_MODE = True
            
            self.frame_count += 1
            
            # Log statistics periodically (more frequent in headless mode)
            stats_interval = 10 if Config.HEADLESS_MODE else 30  # 10s in headless, 30s in GUI mode
            if current_time - self.last_stats_log >= stats_interval:
                self.log_statistics()
                self.last_stats_log = current_time
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error processing frame {self.frame_count}: {e}")
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def run(self):
        """Enhanced main detection loop with comprehensive error handling"""
        logger.info("🚀 Starting detection system...")
        if Config.HEADLESS_MODE:
            logger.info("Running in headless mode - use Ctrl+C to stop")
        else:
            logger.info("Press 'q' to quit, 's' for statistics, 'h' for help")
        logger.info("-" * 60)
        
        self.running = True
        consecutive_failures = 0
        max_consecutive_failures = 10
        
        try:
            while self.running:
                success = self.process_frame()
                
                if not success:
                    consecutive_failures += 1
                    logger.warning(f"⚠️  Frame processing failed ({consecutive_failures}/{max_consecutive_failures})")
                    
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error("❌ Too many consecutive failures, stopping system")
                        break
                    
                    time.sleep(0.1)  # Brief pause before retry
                    continue
                else:
                    consecutive_failures = 0  # Reset failure counter on success
                
                # Check for user input (only in GUI mode)
                if not Config.HEADLESS_MODE:
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info("👋 Exit key 'q' pressed")
                        break
                    elif key == ord('s'):
                        logger.info("📊 Statistics requested ('s' pressed)")
                        self.log_statistics()
                    elif key == ord('h'):
                        self.show_help()
                    elif key == 27:  # ESC key
                        logger.info("👋 ESC key pressed")
                        break
                else:
                    # In headless mode, add small delay
                    time.sleep(0.033)  # ~30 FPS equivalent delay
                    
        except KeyboardInterrupt:
            logger.info("⚡ System interrupted by user (Ctrl+C)")
        except Exception as e:
            logger.error(f"💥 Unexpected error in main loop: {e}")
            logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        finally:
            self.cleanup()
    
    def show_help(self):
        """Show help information"""
        if Config.HEADLESS_MODE:
            logger.info("🛡️ HELP - Safety Monitoring (Headless):")
            logger.info("   Monitoring for people without headphone PPE")
            logger.info("   Evidence images saved when violations detected")
            logger.info("   Discord alerts sent with photographic evidence")
            logger.info("   Use Ctrl+C to stop monitoring")
            logger.info("   Check logs for compliance statistics")
        else:
            logger.info("🛡️ HELP - Safety Monitor Controls:")
            logger.info("   'q' - Stop monitoring system")
            logger.info("   's' - Show compliance statistics")
            logger.info("   'h' - Show this help")
            logger.info("   'ESC' - Emergency stop monitoring")
    
    def cleanup(self):
        """Comprehensive cleanup of all system resources"""
        logger.info("🧼 Cleaning up system resources...")
        self.running = False
        
        # Log final statistics
        logger.info("📊 FINAL STATISTICS:")
        runtime = datetime.now() - self.start_time
        logger.info(f"   Total runtime: {str(runtime).split('.')[0]}")
        logger.info(f"   Total frames: {self.frame_count}")
        logger.info(f"   Total detections: {self.total_detections}")
        logger.info(f"   Average FPS: {self.frame_count / runtime.total_seconds():.1f}")
        
        # Cleanup camera
        if self.camera_system:
            self.camera_system.cleanup()
        
        # Cleanup AI inference
        if self.hailo_inference:
            self.hailo_inference.cleanup()
        
        # Send shutdown notification
        if self.discord_notifier:
            try:
                shutdown_message = "🛑 Hailo AI Detection System is shutting down"
                final_stats = {
                    "⏱️ Total Runtime": str(runtime).split('.')[0],
                    "📊 Total Frames": str(self.frame_count),
                    "🔍 Total Detections": str(self.total_detections),
                    "📊 Average FPS": f"{self.frame_count / runtime.total_seconds():.1f}"
                }
                self.discord_notifier.send_notification(shutdown_message, 0, final_stats)
            except:
                pass  # Don't fail cleanup if Discord fails
        
        # Cleanup OpenCV windows (only if not in headless mode)
        if not Config.HEADLESS_MODE:
            try:
                cv2.destroyAllWindows()
            except:
                pass  # Ignore cleanup errors in headless mode
        
        logger.info("✅ Safety monitoring system cleanup completed successfully")
        logger.info("=" * 60)
        logger.info("🛡️ Thank you for using Hailo AI Safety Monitoring System!")
        logger.info("📊 Final compliance statistics logged above")
        logger.info("=" * 60)

# ===============================
# 🚀 MAIN FUNCTION
# ===============================

def check_system_requirements():
    """Check system requirements and show warnings if needed"""
    logger.info("🔍 Checking system requirements...")
    
    warnings = []
    
    # Check HEF file
    if not Path(Config.HEF_PATH).exists():
        warnings.append(f"HEF file not found: {Config.HEF_PATH} (will use CPU fallback)")
    
    # Check available memory
    try:
        import psutil
        available_mem = psutil.virtual_memory().available // (1024**2)  # MB
        if available_mem < 1000:  # Less than 1GB
            warnings.append(f"Low memory detected: {available_mem}MB available")
    except ImportError:
        pass
    
    # Check disk space
    try:
        import shutil
        free_space = shutil.disk_usage('.').free // (1024**3)  # GB
        if free_space < 2:
            warnings.append(f"Low disk space: {free_space}GB free")
    except:
        pass
    
    if warnings:
        logger.warning("⚠️  System warnings:")
        for warning in warnings:
            logger.warning(f"   • {warning}")
    else:
        logger.info("✅ System requirements check passed")
    
    return len(warnings) == 0

def show_startup_banner():
    """Show enhanced startup banner with Wi-Fi info"""
    banner = f"""
┌{'─' * 58}┐
│{' ' * 58}│
│  🎧 HAILO AI PPE COMPLIANCE MONITOR v2.2   │
│{' ' * 58}│
│  💻 Raspberry Pi 5 + Hailo AI TOP13 + Camera   │
│  🛡️ Headphone PPE Compliance Detection         │
│  📶 5GHz Wi-Fi Support + IP Notifications      │
│{' ' * 58}│
└{'─' * 58}┘
"""
    print(banner)
    
    # Show Network Configuration
    print("📶 Network Configuration:")
    if Config.PREFER_ETHERNET:
        print("   🔗 Priority: Ethernet -> Wi-Fi -> Auto-scan")
    else:
        print("   🔗 Priority: Wi-Fi -> Auto-scan")
    print(f"   📡 Wi-Fi Target: {Config.WIFI_SSID}")
    print(f"   🌍 Country Code: {Config.WIFI_COUNTRY}")
    print(f"   ⚡ 5GHz Support: {'✅ Enabled' if Config.ENABLE_WIFI_5GHZ else '❌ Disabled'}")
    print(f"   🔄 Auto-scan: Every {Config.NETWORK_SCAN_INTERVAL} seconds")
    
    # Check current connection
    if wifi_manager.check_connection():
        connection_info = wifi_manager.get_connection_info()
        connection_type = "5GHz" if connection_info.get("is_5ghz") else "2.4GHz" if wifi_manager.current_interface == "wlan0" else "Ethernet"
        print(f"   ✅ Connected: {wifi_manager.current_ssid} ({connection_type}) via {wifi_manager.current_interface}")
        print(f"   📍 Local IP: {wifi_manager.current_ip}")
        
        # Show Tailscale status
        if Config.ENABLE_TAILSCALE:
            tailscale_info = connection_info.get("tailscale", {})
            if tailscale_info.get("running") and tailscale_info.get("ip"):
                print(f"   🌐 Tailscale: {tailscale_info['ip']} (Remote Access Ready)")
            elif tailscale_info.get("installed"):
                print(f"   🌐 Tailscale: Installed (Setup Required)")
            else:
                print(f"   🌐 Tailscale: Not Available")
    else:
        print(f"   ❌ Not Connected (will attempt auto-connection)")
    print()
    
    # Show compatibility info
    print("🔧 System Compatibility:")
    print(f"   🐍 Python: {sys.version.split()[0]}")
    print(f"   💻 Platform: {sys.platform}")
    if PICAMERA_AVAILABLE:
        print("   📷 PiCamera2: ✅ Available")
    else:
        print("   📷 PiCamera2: ❌ Not Available (will use USB/Simulation)")
    
    if HAILO_AVAILABLE:
        print("   🤖 Hailo AI: ✅ Available") 
    else:
        print("   🤖 Hailo AI: ❌ Not Available (will use CPU Fallback)")
    
    if HEADLESS_MODE:
        print("   🖥️  Display Mode: 🚫 Headless (no GUI)")
    else:
        print("   🖥️  Display Mode: ✅ GUI Enabled")
    
    print()
    
    if not PICAMERA_AVAILABLE:
        print("💡 PiCamera2 Troubleshooting:")
        print("   1. sudo apt update && sudo apt install -y python3-picamera2")
        print("   2. sudo raspi-config -> Interface Options -> Camera -> Enable")
        print("   3. Reboot: sudo reboot")
        print("   4. Check camera: libcamera-still -o test.jpg")
        print()

def main():
    """Enhanced main function with comprehensive startup flow"""
    try:
        # Show startup banner
        show_startup_banner()
        
        # Check system requirements
        requirements_ok = check_system_requirements()
        
        logger.info("🎆 System Configuration:")
        logger.info(f"   📏 Resolution: {Config.CAMERA_WIDTH}x{Config.CAMERA_HEIGHT}")
        logger.info(f"   ⚡ Confidence: {Config.CONFIDENCE_THRESHOLD:.1%}")
        logger.info(f"   🔔 Discord: {'Enabled' if Config.DISCORD_WEBHOOK else 'Disabled'}")
        logger.info(f"   💾 Model: {Config.HEF_PATH}")
        logger.info(f"   🔄 Cooldown: {Config.NOTIFICATION_COOLDOWN}s")
        
        # Initialize Network Connection (Ethernet priority -> Wi-Fi -> Monitor)
        logger.info("\n📶 Step 0: Network Connection")
        network_connected = False
        try:
            # Check current connection with priority system
            if wifi_manager.check_connection():
                interface_info = f"{wifi_manager.current_interface} ({wifi_manager.current_ssid})"
                logger.info(f"✅ Network connected via: {interface_info}")
                logger.info(f"📍 IP Address: {wifi_manager.current_ip}")
                network_connected = True
            else:
                logger.info("🔗 No network connection detected - attempting to connect...")
                
                # Try Ethernet first
                if Config.PREFER_ETHERNET and wifi_manager.check_ethernet_connection():
                    logger.info("✅ Ethernet connection established")
                    network_connected = True
                else:
                    # Try Wi-Fi connection
                    logger.info("🔗 Attempting Wi-Fi connection...")
                    network_connected = wifi_manager.connect_to_wifi()
            
            # Setup Tailscale for remote access
            if Config.ENABLE_TAILSCALE:
                logger.info("🌐 Setting up Tailscale for remote access...")
                tailscale_success = wifi_manager.setup_tailscale()
                if tailscale_success:
                    logger.info("✅ Tailscale remote access enabled")
                else:
                    logger.warning("⚠️ Tailscale setup incomplete - check logs for details")
            
            # Start network monitoring for continuous connectivity
            wifi_manager.start_network_monitoring()
            
            # Send network notification
            if network_connected:
                connection_info = wifi_manager.get_connection_info()
                # Create a temporary Discord notifier for network notification
                temp_notifier = DiscordNotifier(Config.DISCORD_WEBHOOK)
                temp_notifier.send_network_notification(connection_info)
            else:
                logger.warning("⚠️  No network connection available")
                logger.info(f"🔄 Will continue scanning every {Config.NETWORK_SCAN_INTERVAL} seconds")
                
        except Exception as e:
            logger.error(f"❌ Network setup error: {e}")
            logger.info("🔄 Continuing with network monitoring enabled")
        
        # Initialize safety monitoring system
        logger.info("\n🚀 Initializing safety monitoring system...")
        detection_system = SafetyMonitoringSystem()
        
        if detection_system.initialize():
            logger.info("⚠️ Safety monitoring system ready! Starting PPE compliance monitoring...")
            if Config.HEADLESS_MODE:
                logger.info("🛡️ Running safety monitoring - evidence images will be saved")
                logger.info("⚡ Use Ctrl+C to stop monitoring")
            else:
                logger.info("📹 Monitoring live feed - 'q' to quit, 's' for statistics")
            
            # Run the detection system
            detection_system.run()
            
        else:
            logger.error("❌ Failed to initialize detection system")
            logger.error("Please check the logs above for specific error details")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("⚡ Startup interrupted by user")
        # Clean up network monitoring
        if 'wifi_manager' in locals() and wifi_manager.monitoring_active:
            wifi_manager.stop_network_monitoring()
        return 130
    except Exception as e:
        logger.error(f"💥 Fatal error during startup: {e}")
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        return 1

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    import signal
    
    def signal_handler(sig, frame):
        if Config.HEADLESS_MODE:
            logger.info(f"\n⚡ Received signal {sig} in headless mode, initiating graceful shutdown...")
        else:
            logger.info(f"\n⚡ Received signal {sig}, initiating graceful shutdown...")
        
        # Clean up network monitoring
        try:
            if 'wifi_manager' in globals() and wifi_manager.monitoring_active:
                logger.info("🔌 Stopping network monitoring...")
                wifi_manager.stop_network_monitoring()
        except:
            pass
        
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run main function and exit with appropriate code
    exit_code = main()
    sys.exit(exit_code)

