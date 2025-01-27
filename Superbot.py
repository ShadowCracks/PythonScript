import os
import uuid
import time
import hashlib
import requests
import shutil
import random
import uiautomator2 as u2
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, Dict, Any
from xml.etree import ElementTree
from typing import Union, List
from PIL import Image
import io

class SwipeHandler:
    def __init__(self, device: u2.Device):
        self.device = device

    def perform_swipe(self, direction: str):
        """Perform a single swipe in the specified direction"""
        screen_size = self.device.window_size()
        center_x = screen_size[0] // 2
        center_y = screen_size[1] // 2

        swipe_coordinates = {
            'left': {
                'start_x': center_x,
                'start_y': center_y,
                'end_x': center_x - (screen_size[0] * 0.8),
                'end_y': center_y
            },
            'right': {
                'start_x': center_x,
                'start_y': center_y,
                'end_x': center_x + (screen_size[0] * 0.8),
                'end_y': center_y
            }
        }

        # Add randomness to coordinates and duration
        start_x = swipe_coordinates[direction]['start_x'] + random.uniform(-50, 50)
        start_y = swipe_coordinates[direction]['start_y'] + random.uniform(-50, 50)
        end_x = swipe_coordinates[direction]['end_x'] + random.uniform(-50, 50)
        end_y = swipe_coordinates[direction]['end_y'] + random.uniform(-50, 50)
        duration = random.uniform(0.2, 0.4)

        self.device.swipe(
            fx=start_x,
            fy=start_y,
            tx=end_x,
            ty=end_y,
            duration=duration
        )

        # Random delay between swipes
        time.sleep(random.uniform(1, 3))


class DynamicBumbleFlow:
    def find_text_in_xml(self, root, text_substring: Union[str, List[str]]) -> bool:
        """Find text in XML hierarchy"""
        if isinstance(text_substring, list):
            return any(self.find_text_in_xml(root, single_text) for single_text in text_substring)

        # Convert the search string to lowercase for case-insensitive comparison
        text_substring = text_substring.lower()

        for node in root.iter():
            node_text = (node.attrib.get('text') or "").lower()
            content_desc = (node.attrib.get('content-desc') or "").lower()
            if text_substring in node_text or text_substring in content_desc:
                return True
        return False

    def find_resource_id_in_xml(self, root, resource_id: str) -> bool:
        """Find resource ID in XML hierarchy"""
        for node in root.iter():
            node_res_id = node.attrib.get('resource-id', "")
            if resource_id in node_res_id:
                return True
        return False

    def __init__(self, device: u2.Device, bumble_registration: "BumbleRegistration"):
        self.device = device
        self.bumble = bumble_registration  # This is our BumbleRegistration instance
        self.finished = False

        # Add swipe configuration
        self.swipe_config = {
            'total_swipes': 10,
            'right_swipe_percentage': 30,
            'swipes_completed': 0
        }

        # This maps screens to BumbleRegistration methods
        self.screen_actions = {
            "phone_entry": {
                "identifiers": {"text": "Use cell phone number"},
                "action": self.bumble.click_use_cell_phone_button
            },
            "phone_number_input": {
                "identifiers": {
                    "text": "Can we get your number, please?"
                },
                "action": lambda: self.bumble.enter_phone_number(self.bumble.request_phone_number())
            },
            "call_me": {
                "identifiers": {"resource_id": "com.bumble.app:id/button_call_me"},
                "action": self.bumble.handle_call_me_screen
            },
            "okbutton": {
                "identifiers": {"text": "We need to verify your number"},
                "action": self.bumble.click_ok_button
            },
            "sms_code": {
                "identifiers": {
                    "text": ["Verify your number", "Enter code", "Verification code", "Enter the code"]
                },
                "action": lambda: self.bumble.enter_sms_code_and_continue(
                    self.bumble.check_sms_code()) if self.bumble.check_sms_code() else None
            },
            "get_code": {
                "identifiers": {"text": "Get a code instead"},
                "action": self.bumble.click_get_code_instead
            },
            "retry_call": {
                "identifiers": {"text": "Didn't get a code?"},
                "action": self.bumble.retry_with_new_number
            },
            "name_entry": {
                "identifiers": {
                    "text": "Your first name"
                },
                "action": self.bumble.enter_personal_info
            },
            "location_services": {
                "identifiers": {
                    "resource_id": "com.bumble.app:id/enableLocation",
                    "text": "Set location services"
                },
                "action": self.bumble.enable_location_and_notifications
            },
            "gender_selection": {
                "identifiers": {
                    "text": "Which gender best describes you?"
                },
                "action": self.bumble.select_gender
            },
            "dating_preference": {
                "identifiers": {
                    "text": ["I'm open to dating everyone", "Who would you like to meet?"]
                },
                "action": self.bumble.select_dating_preference
            },
            "relationship_goal": {
                "identifiers": {
                    "text": ["A long-term relationship", "Fun, casual dates", "Intimacy, without commitment"]
                },
                "action": self.bumble.select_relationship_goal
            },
            "five_things": {
                "identifiers": {
                    "text": ["Choose 5 things you're really into", "Choose 5 things"]
                },
                "action": self.bumble.select_five_things
            },
            "Value": {
                "identifiers": {
                    "text": "Ambition"
                },
                "action": self.bumble.select_values
            },
            "relationship_goals": {
                "identifiers": {
                    "text": "It's your dating journey,"
                },
                "action": self.bumble.select_relationship_goal
            },
           "opening_moves": {
                "identifiers": {
                    "text": "Write your own Opening Move"
                },
                "action": self.bumble.select_opening_move
            }, 
            
            "next_button": {
                "identifiers": {
                    "text": ["Shown as:", "What brings you to Bumble"]
                },
                "action": self.bumble.handle_next_buttons
            },
            "skip": {
                "identifiers": {
                    "text": [ "Religion", "Can we get your email?", "ethnicity?",
                             "important in your life", "height", "like to date you",
                             "How about causes and communities"]
                },
                "action": self.bumble.Skip
            },
            "drinking_habits": {
                "identifiers": {
                    "text": "Yes, I drink"
                },
                "action": self.bumble.select_habits
            },
            "kids_questions": {
                "identifiers": {
                    "text": "Have kids"
                },
                "action": self.bumble.handle_kids_questions
            },
            "swipe_screen": {
                "identifiers": {
                    "text": ["Keep on swiping", "we're learning what you like", "learning what you like", "Chats" ]
                },
                "action": self.handle_swiping
            },
            "photo_upload": {
                "identifiers": {
                    "text": "Add at least 4"
                },
                "action": self.bumble.setup_photos
            },
            "finish": {
                "identifiers": {
                    "text": "I accept",
                    "resource_id": "com.bumble.app:id/pledge_cta"
                },
                "action": self.bumble.finish_registration
            },
            # Add new swiping screen detection

        }
    def scroll_profile(self):
        """
        Scroll down on the current profile, wait a bit, then scroll back up.
        """
        screen_size = self.device.window_size()
        width = screen_size[0]
        height = screen_size[1]

        center_x = width // 2
        # Start near the center, but a bit lower for a "scroll up" gesture
        start_y = int(height * 0.7)
        end_y = int(height * 0.3)

        # Scroll down (finger moves from lower to upper = upward gesture)
        print("Scrolling down within the profile...")
        self.device.swipe(center_x, start_y, center_x, end_y, duration=0.4)
        time.sleep(random.uniform(1.5, 3))  # Wait while user reads more details

        # Scroll back up (finger moves from upper to lower = downward gesture)
        print("Scrolling back up...")
        self.device.swipe(center_x, end_y, center_x, start_y, duration=0.4)
        time.sleep(random.uniform(1.5, 3))  # Pause briefly again


    def handle_swiping(self):
        """Handle the swiping screen with configured ratios"""
        print("Handling swipe screen...")

        if self.swipe_config['swipes_completed'] >= self.swipe_config['total_swipes']:
            print("All swipes completed")
            self.finished = True
            return

        # Optional: add a random chance to scroll the profile
        # For example, 30% chance to scroll the current profile up/down:
        if random.random() < 0.7:
            self.scroll_profile()

        # The rest of your existing code for left/right swipe follows
        screen_size = self.device.window_size()
        center_x = screen_size[0] // 2
        center_y = screen_size[1] // 2

        # Determine swipe direction based on configured ratio
        should_swipe_right = random.random() < (self.swipe_config['right_swipe_percentage'] / 100)

        try:
            swipe_distance = int(screen_size[0] * 0.7)
            swipe_y_variation = int(screen_size[1] * 0.1)

            if should_swipe_right:
                start_x = center_x - int(screen_size[0] * 0.3)
                end_x   = center_x + int(screen_size[0] * 0.4)
                print("Swiping right...")
            else:
                start_x = center_x + int(screen_size[0] * 0.3)
                end_x   = center_x - int(screen_size[0] * 0.4)
                print("Swiping left...")

            start_y = center_y + random.randint(-swipe_y_variation, swipe_y_variation)
            end_y   = start_y + random.randint(-20, 20)

            duration = random.uniform(0.3, 0.5)

            self.device.swipe(
                fx=start_x,
                fy=start_y,
                tx=end_x,
                ty=end_y,
                duration=duration
            )

            self.swipe_config['swipes_completed'] += 1
            print(f"Completed {self.swipe_config['swipes_completed']}/{self.swipe_config['total_swipes']} swipes")

            # Slightly longer delay between swipes
            time.sleep(random.uniform(1.5, 3.5))

        except Exception as e:
            print(f"Error during swipe: {str(e)}")


    def set_swipe_config(self, total_swipes: int = 10, right_swipe_percentage: int = 30):
        """Update swipe configuration"""
        self.swipe_config.update({
            'total_swipes': total_swipes,
            'right_swipe_percentage': right_swipe_percentage,
            'swipes_completed': 0
        })

    def run_flow(self):
        """Run the dynamic flow"""
        while not self.finished:
            screen_name = self.identify_current_screen()
            print(f"Current screen: {screen_name}")

            if screen_name in self.screen_actions:
                # Regular screen handling
                action = self.screen_actions[screen_name]["action"]
                try:
                    action()
                    time.sleep(2)
                except Exception as e:
                    print(f"Error executing action: {e}")
                    self.try_fallback_buttons()
            else:
                self.try_fallback_buttons()

    def identify_current_screen(self) -> str:
        """Identify the current screen based on XML hierarchy"""
        xml = self.device.dump_hierarchy()
        root = ElementTree.fromstring(xml)

        for screen_name, screen_info in self.screen_actions.items():
            identifiers = screen_info["identifiers"]
            if all(self.check_identifier(root, key, value)
                   for key, value in identifiers.items()):
                return screen_name

        return "unknown"

    def check_identifier(self, root, key, value):
        """Check if identifier exists in XML hierarchy"""
        if key == "text":
            return self.find_text_in_xml(root, value)
        elif key == "resource_id":
            return self.find_resource_id_in_xml(root, value)
        return False

    def try_fallback_buttons(self):
        """Try common buttons when screen isn't recognized"""
        common_buttons = ["Maybe later", "YES", "NOT INTERESTED", "Continue", "Confirm", "OK", "Allow", "I accept",
                          "Got it", "Change number", "Start connecting"]
        for button_text in common_buttons:
            if self.device(text=button_text).exists:
                self.device(text=button_text).click()
                time.sleep(2)
                return True
        return False

    def run_flow(self):
        while not self.finished:
            screen_name = self.identify_current_screen()
            print(f"Current screen: {screen_name}")

            if screen_name in self.screen_actions:
                # Regular screen handling
                action = self.screen_actions[screen_name]["action"]
                try:
                    action()
                    time.sleep(2)
                except Exception as e:
                    print(f"Error executing action: {e}")
                    self.try_fallback_buttons()
            else:
                self.try_fallback_buttons()

    def identify_current_screen(self) -> str:
        xml = self.device.dump_hierarchy()
        root = ElementTree.fromstring(xml)

        for screen_name, screen_info in self.screen_actions.items():
            identifiers = screen_info["identifiers"]
            if all(self.check_identifier(root, key, value)
                   for key, value in identifiers.items()):
                return screen_name

        return "unknown"

    def check_identifier(self, root, key, value):
        if key == "text":
            return self.find_text_in_xml(root, value)
        elif key == "resource_id":
            return self.find_resource_id_in_xml(root, value)
        # Add other identifier types as needed
        return False

    def try_fallback_buttons(self):
        """Try common buttons when screen isn't recognized"""
        common_buttons = [
            "YES",  # For right swipe confirmation
            "NOT INTERESTED",  # For left swipe confirmation
            "CANCEL",  # For both dialogs
            "Maybe later",
            "Continue",
            "Confirm",
            "OK",
            "Allow",
            "I accept",
            "Got it",
            "Change number",
            "Start connecting"
        ]
        for button_text in common_buttons:
            if self.device(text=button_text).exists:
                print(f"Clicking fallback button: {button_text}")
                self.device(text=button_text).click()
                time.sleep(2)
                return True
        return False


def wait_for_element(device, class_name=None, resource_id=None, text=None, description=None, timeout=80,
                     poll_interval=0.5):
    """
    Wait for an element to appear within the given timeout.
    """
    end_time = time.time() + timeout
    while time.time() < end_time:
        element = device(**{k: v for k, v in {
            "className": class_name,
            "resourceId": resource_id,
            "text": text,
            "description": description
        }.items() if v})
        if element.exists:
            return element
        time.sleep(poll_interval)
    raise Exception(
        f"Element not found within {timeout} seconds: class_name={class_name}, resource_id={resource_id}, text={text}, description={description}")


# Cloud Phone API Constants
APP_ID = "ME7YWKTAFWBJEUX4AZQCKIGN"
API_KEY = "B5OH6I6R7BI1024DULUA02VUZLP7QF"
CREATE_PROFILE_URL = "https://openapi.geelark.com/open/v1/phone/add"
START_PROFILE_URL = "https://openapi.geelark.com/open/v1/phone/start"
GPS_INFO_URL = "https://openapi.geelark.com/open/v1/phone/gps/get"
GET_UPLOAD_URL = "https://openapi.geelark.com/open/v1/upload/getUrl"
UPLOAD_TO_PHONE_URL = "https://openapi.geelark.com/open/v1/phone/uploadFile"
UPLOAD_STATUS_URL = "https://openapi.geelark.com/open/v1/phone/uploadFile/result"
ADB_SET_STATUS_URL = "https://openapi.geelark.com/open/v1/adb/setStatus"
GET_INSTALLED_APPS_URL = "https://openapi.geelark.com/open/v1/app/list"
START_APP_URL = "https://openapi.geelark.com/open/v1/app/start"
GET_ADB_INFO_URL = "https://openapi.geelark.com/open/v1/adb/getData"

# DAISYSMS API Constants
DAISYSMS_API_KEY = "Y7x49dtcq1RTLO2PRxH3zNk0TZPlVJ"
DAISYSMS_BASE_URL = "https://daisysms.com/stubs/handler_api.php"

# File and folder settings
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROXY_FILE = os.path.join(SCRIPT_DIR, "proxies.txt")
IMAGES_FOLDER = os.path.join(SCRIPT_DIR, "images")
NAMES_FILE = os.path.join(SCRIPT_DIR, "names.txt")

# Cloud Phone settings
PROFILE_SETTINGS = {
    "amount": 1,
    "androidVersion": 4,  # Android 13
    "groupName": "API",
    "tagsName": ["API - 1"],
    "region": None,  # Auto-match
    "remark": "",
}


class CloudPhoneManager:
    def __init__(self):
        self.profile_id = None
        self.adb_info = None

    def generate_headers(self) -> Dict[str, str]:
        """Generate headers required for the API request."""
        trace_id = str(uuid.uuid4())
        ts = str(int(time.time() * 1000))
        nonce = trace_id[:6]
        to_sign = APP_ID + trace_id + ts + nonce + API_KEY
        sign = hashlib.sha256(to_sign.encode()).hexdigest().upper()

        return {
            "Content-Type": "application/json",
            "appId": APP_ID,
            "traceId": trace_id,
            "ts": ts,
            "nonce": nonce,
            "sign": sign
        }

    def get_random_proxy(self) -> str:
        """Select a random proxy from proxies.txt and remove it."""
        try:
            with open(PROXY_FILE, "r") as f:
                proxies = f.readlines()

            if not proxies:
                raise ValueError("Proxy file is empty. Please add proxies to the file.")

            selected_proxy = random.choice(proxies).strip()
            updated_proxies = [proxy for proxy in proxies if proxy.strip() != selected_proxy]

            with open(PROXY_FILE, "w") as f:
                f.writelines(updated_proxies)

            return selected_proxy
        except FileNotFoundError:
            raise FileNotFoundError(f"Proxy file '{PROXY_FILE}' not found.")

    def parse_proxy(self, proxy: str) -> Dict[str, Any]:
        parts = proxy.split(":")
        if len(parts) < 4:
            raise ValueError(f"Invalid proxy format: {proxy}")

        return {
            "typeId": 1,  # SOCKS5 proxy
            "server": parts[0],
            "port": int(parts[1]),
            "username": parts[2],
            "password": ":".join(parts[3:])  # Handles any extra parts in the password
        }

    def create_profile(self) -> Dict[str, Any]:
        """Create a cloud phone profile."""
        proxy = self.get_random_proxy()
        proxy_config = self.parse_proxy(proxy)
        PROFILE_SETTINGS["proxyConfig"] = proxy_config

        headers = self.generate_headers()
        response = requests.post(CREATE_PROFILE_URL, headers=headers, json=PROFILE_SETTINGS)

        # Print the full response for debugging
        print("DEBUG create_profile response:", response.json())

        creation_response = response.json()

        profile_data = creation_response.get("data", {}).get("details", [{}])[0]
        self.profile_id = profile_data.get("id")

        if self.profile_id:
            return creation_response
        else:
            print("Failed to create profile. Response:", creation_response)
            return creation_response

    def start_profile(self) -> str:
        """Start the cloud phone profile."""
        headers = self.generate_headers()
        payload = {"ids": [self.profile_id]}
        response = requests.post(START_PROFILE_URL, headers=headers, json=payload)
        response_data = response.json()
        print("DEBUG start_profile response_data =", response_data)

        if response_data.get("code") == 0:
            success_details = response_data["data"]["successDetails"][0]
            return success_details["url"]
        else:
            raise Exception(f"Failed to start profile: {response_data.get('msg')}")

    def enable_adb(self):
        """Enable ADB for the cloud phone."""
        try:
            headers = self.generate_headers()
            payload = {
                "ids": [self.profile_id],
                "open": True
            }
            response = requests.post(ADB_SET_STATUS_URL, headers=headers, json=payload)
            response_data = response.json()

            if response_data.get("code") == 0:
                print("ADB enabled successfully. Waiting for initialization...")
                time.sleep(10)  # Increased wait time to 10 seconds
            else:
                raise Exception(f"Failed to enable ADB: {response_data.get('msg')}")

        except Exception as e:
            print(f"Error enabling ADB: {str(e)}")
            raise

    def get_adb_info(self) -> Dict[str, Any]:
        """Retrieve ADB connection information."""
        try:
            # Add retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    headers = self.generate_headers()
                    payload = {"ids": [self.profile_id]}
                    response = requests.post(GET_ADB_INFO_URL, headers=headers, json=payload)
                    response_data = response.json()

                    if response_data.get("code") == 0:
                        adb_info = response_data["data"]["items"][0]
                        if adb_info["code"] == 0:
                            self.adb_info = {
                                "ip": adb_info["ip"],
                                "port": adb_info["port"],
                                "password": adb_info["pwd"]
                            }
                            print(f"Successfully got ADB info: {self.adb_info}")
                            return self.adb_info
                        else:
                            print(f"ADB info retrieval failed with code: {adb_info['code']}")
                    else:
                        print(f"Failed to get ADB info: {response_data.get('msg')}")

                    if attempt < max_retries - 1:
                        print(f"Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(5)
                except Exception as e:
                    if attempt < max_retries - 1:
                        print(f"Error: {str(e)}. Retrying in 5 seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(5)
                    else:
                        raise

            raise Exception("Failed to retrieve ADB information after multiple attempts")
        except Exception as e:
            print(f"Error getting ADB info: {str(e)}")
            raise

    def process_subfolder(self):
        """Process all files in a subfolder and upload them concurrently."""
        subfolders = [f for f in os.listdir(IMAGES_FOLDER) if os.path.isdir(os.path.join(IMAGES_FOLDER, f))]
        if not subfolders:
            print("No subfolders found in the images directory.")
            return

        subfolder_name = random.choice(subfolders)
        subfolder_path = os.path.join(IMAGES_FOLDER, subfolder_name)
        print(f"Processing folder: {subfolder_name}")

        try:
            with ThreadPoolExecutor() as executor:
                file_paths = [os.path.join(subfolder_path, file_name)
                              for file_name in os.listdir(subfolder_path)
                              if os.path.isfile(os.path.join(subfolder_path, file_name))]
                futures = [executor.submit(self.upload_file, file_path) for file_path in file_paths]

                for future in futures:
                    future.result()

            shutil.rmtree(subfolder_path)
            print(f"Folder {subfolder_name} processed and deleted.")
        except Exception as e:
            print(f"Error processing folder {subfolder_name}: {e}")

    def upload_file(self, file_path: str):
        """Handle the full upload process for a single file."""
        file_extension = file_path.split(".")[-1]
        upload_url, resource_url = self.get_signed_upload_url(file_extension)
        self.upload_file_to_signed_url(file_path, upload_url)
        task_id = self.associate_file_with_cloud_phone(resource_url)

        while True:
            status = self.query_upload_status(task_id)
            if status == 2:  # Upload successful
                print(f"File {file_path} uploaded and associated successfully!")
                break
            elif status == 3:  # Upload failed
                raise Exception(f"Upload failed for file {file_path}")
            else:
                print(f"Uploading {file_path}... Status: {status}")
                time.sleep(2)

    def get_signed_upload_url(self, file_type: str) -> tuple:
        """Retrieve a signed upload URL."""
        headers = self.generate_headers()
        payload = {"fileType": file_type}
        response = requests.post(GET_UPLOAD_URL, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("code") == 0:
            return response_data["data"]["uploadUrl"], response_data["data"]["resourceUrl"]
        raise Exception(f"Failed to get upload URL: {response_data.get('msg')}")

    def upload_file_to_signed_url(self, file_path: str, upload_url: str):
        """Upload a file to the signed URL."""
        with open(file_path, "rb") as file:
            response = requests.put(upload_url, data=file)
            if response.status_code != 200:
                raise Exception(f"Failed to upload file: {response.status_code}")

    def associate_file_with_cloud_phone(self, resource_url: str) -> str:
        """Associate the uploaded file with the cloud phone."""
        headers = self.generate_headers()
        payload = {"id": self.profile_id, "fileUrl": resource_url}
        response = requests.post(UPLOAD_TO_PHONE_URL, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("code") == 0:
            return response_data["data"]["taskId"]
        raise Exception(f"Failed to associate file with phone: {response_data.get('msg')}")

    def query_upload_status(self, task_id: str) -> int:
        """Query the upload status of a file."""
        headers = self.generate_headers()
        payload = {"taskId": task_id}
        response = requests.post(UPLOAD_STATUS_URL, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("code") == 0:
            return response_data["data"]["status"]
        raise Exception(f"Failed to query upload status: {response_data.get('msg')}")

    def get_installed_apps(self) -> list:
        """Retrieve the list of installed apps."""
        headers = self.generate_headers()
        payload = {
            "envId": self.profile_id,
            "page": 1,
            "pageSize": 100
        }
        response = requests.post(GET_INSTALLED_APPS_URL, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("code") == 0:
            return response_data["data"]["items"]
        else:
            raise Exception(f"Failed to get installed apps: {response_data.get('msg')}")

    def start_bumble(self):
        """Start the Bumble app if installed."""
        installed_apps = self.get_installed_apps()
        for app in installed_apps:
            if app.get("appName") == "Bumble":
                app_version_id = app.get("appVersionId")
                headers = self.generate_headers()
                payload = {
                    "envId": self.profile_id,
                    "appVersionId": app_version_id
                }
                response = requests.post(START_APP_URL, headers=headers, json=payload)
                response_data = response.json()
                if response_data.get("code") == 0:
                    print(f"Bumble app started successfully.")
                    time.sleep(4)  # Wait for app to fully start
                else:
                    raise Exception(f"Failed to start Bumble app: {response_data.get('msg')}")
                return
        print("Bumble app is not installed on this device.")


class BumbleRegistration:
    def __init__(self, adb_address: str, password: str):
        print(f"Attempting to connect to device at {adb_address}")
        max_retries = 3
        retry_delay = 5

        # Only disconnect this specific device
        os.system(f"adb disconnect {adb_address}")
        time.sleep(2)

        for attempt in range(max_retries):
            try:
                print(f"Connection attempt {attempt + 1}/{max_retries}")
                
                # Connect to specific device
                os.system(f"adb connect {adb_address}")
                time.sleep(2)
                
                # Always use -s flag to specify the device
                os.system(f'adb -s {adb_address} shell "glogin {password}"')
                time.sleep(2)
                
                # Initialize uiautomator2 with the specific device
                self.device = u2.connect(adb_address)
                
                # Test connection
                self.device.info
                print("Successfully connected to device")
                self.current_order_id = None
                
                # Initialize dynamic_flow after successful connection
                self.dynamic_flow = DynamicBumbleFlow(self.device, self)
                break
                
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {str(e)}")
                # Disconnect only this specific device before retrying
                os.system(f"adb disconnect {adb_address}")
                time.sleep(2)
                
                if attempt < max_retries - 1:
                    print(f"Waiting {retry_delay} seconds before retrying...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Failed to connect to device after {max_retries} attempts")
                
    def delay(self, seconds: float = 2.5):
        """Add a delay between actions."""
        time.sleep(seconds)

    

    def request_phone_number(self) -> Optional[str]:
        """Request a phone number from DaisySMS."""
        params = {
            "api_key": DAISYSMS_API_KEY,
            "action": "getNumber",
            "service": "mo",
            "max_price": "5.5"  # You can adjust this
        }

        print("Requesting a phone number from DaisySMS...")
        response = requests.get(DAISYSMS_BASE_URL, params=params)
        print(f"DaisySMS response: {response.text}")

        if response.status_code == 200:
            # Response format should be: ACCESS_NUMBER:ID:PHONE_NUMBER
            response_parts = response.text.split(':')
            if len(response_parts) == 3 and response_parts[0] == "ACCESS_NUMBER":
                self.current_order_id = response_parts[1]
                phone_number = response_parts[2]
                print(f"Received phone number: {phone_number}")
                return phone_number
            else:
                print(f"Unexpected response format: {response.text}")
        return None

    def check_sms_code(self) -> Optional[str]:
        """Check for SMS code from DaisySMS."""
        start_time = time.time()
        while time.time() - start_time < 30:  # Check for up to 30 seconds
            params = {
                "api_key": DAISYSMS_API_KEY,
                "action": "getStatus",
                "id": self.current_order_id
            }

            response = requests.get(DAISYSMS_BASE_URL, params=params)
            print(f"Checking SMS status: {response.text}")

            if response.ok:
                response_parts = response.text.split(':')
                if len(response_parts) == 2 and response_parts[0] == "STATUS_OK":
                    code = response_parts[1]
                    print(f"SMS code received: {code}")
                    return code

            time.sleep(2)  # Short delay between checks

        # After 30 seconds with no code
        print("No code received after 30 seconds of checking, clicking 'didn't get a code?' button...")
        try:
            self.device(text="didn't get a code?").click()
        except:
            try:
                self.device(textContains="get a code").click()
            except:
                print("Could not find 'didn't get a code?' button")

        return None

        # UI Interaction Methods

    def click_use_cell_phone_button(self):
        """Click 'Use cell phone number' button using text-based detection."""
        print("Looking for the 'Use cell phone number' button...")

        try:
            # Use text-based detection to find the button
            element = wait_for_element(self.device, text="Use cell phone number")
            element.click()
            self.delay()
            print("Successfully clicked 'Use cell phone number' button.")
        except Exception as e:
            print(f"Error clicking 'Use cell phone number' button: {str(e)}")
            raise


    def enter_phone_number(self, phone_number: str):
        phone_input_field = self.device(resourceId="com.bumble.app:id/phone_edit_text")
        
        if phone_input_field.exists:
            bounds = phone_input_field.info['bounds']
            # Get screenshot as bytes and convert to PIL Image
            screenshot = Image.open(io.BytesIO(self.device.screenshot(format='raw')))
            # Crop to input field bounds
            cropped = screenshot.crop((bounds['left'], bounds['top'], 
                                    bounds['right'], bounds['bottom']))
            # Use device OCR on cropped image
            has_number = len([c for c in self.device.ocr(cropped) if c.isdigit()]) > 0
            
            if has_number:
                print("Phone field has number. Skipping entry.")
            else:
                print("Phone field empty. Entering number...")
                for digit in str(phone_number):
                    self.device.shell(f"input text {digit}")
                    time.sleep(0.1)
                self.delay()
        else:
            # Fallback typing
            for digit in str(phone_number):
                self.device.shell(f"input text {digit}")
                time.sleep(0.1)
            self.delay()

        self.device(resourceId="com.bumble.app:id/reg_footer_button").click()
        self.delay()


    def click_ok_button(self):
        """Click OK button."""
        print("Clicking 'OK' button...")
        self.device(resourceId="android:id/button1", text="OK").click()
        self.delay()

    def handle_call_me_screen(self):
        """Handle 'Call me' screen."""
        print("Checking for 'Call me' button...")
        if self.device(resourceId="com.bumble.app:id/button_call_me").exists:
            self.device(resourceId="com.bumble.app:id/button_call_me").click()
            self.delay()

            print("Clicking 'Didn't get a call?'...")
            self.device(resourceId="com.bumble.app:id/reg_footer_label").click()
            self.delay()
            print("Clicking 'Get a code instead'...")
            self.device(className="android.widget.Button", description="Get a code instead").click()
            self.delay()
            self.click_ok_button()

    def click_get_code_instead(self):
        """Click 'Get a code instead' button."""
        print("Clicking 'Get a code instead'...")
        self.device(className="android.widget.Button", description="Get a code instead").click()
        self.delay()
        self.click_ok_button()

    def retry_with_new_number(self):
        """Retry with a new phone number."""
        print("Retrying with a new number...")
        print("Clicking 'Didn't get a code?'...")
        self.device(resourceId="com.bumble.app:id/reg_footer_label").click()
        self.delay()
        print("Clicking 'Change number'...")
        self.device(className="android.widget.TextView", text="Change number").click()
        self.delay()

    def enter_sms_code_and_continue(self, sms_code: str):
        """Enter SMS code and continue."""
        print("Entering the SMS code...")
        for digit in sms_code:
            self.device.shell(f"input text {digit}")
            time.sleep(0.1)
        print("Clicking 'Next' button...")
        self.device(resourceId="com.bumble.app:id/reg_footer_button").click()
        self.delay(5)

    def enable_location_and_notifications(self):
        """Enable location and notifications."""

        # Step 1: Wait for and click "Set location services"
        print("Setting up location services...")
        wait_for_element(self.device, resource_id="com.bumble.app:id/enableLocation", text="Set location services")
        self.device(resourceId="com.bumble.app:id/enableLocation", text="Set location services").click()
        self.delay()

        # Step 2: Wait for and click "WHILE USING THE APP"
        print("Allowing location while using app...")
        wait_for_element(self.device,
                         resource_id="com.android.permissioncontroller:id/permission_allow_foreground_only_button",
                         text="WHILE USING THE APP")
        self.device(resourceId="com.android.permissioncontroller:id/permission_allow_foreground_only_button",
                    text="WHILE USING THE APP").click()
        self.delay()

        # Step 3: Wait for and click "Allow notifications"
        print("Enabling notifications...")
        wait_for_element(self.device, class_name="android.widget.TextView", text="Allow notifications")
        self.device(className="android.widget.TextView", text="Allow notifications").click()
        self.delay()

        # Step 4: Wait for and click "ALLOW" button
        wait_for_element(self.device, resource_id="com.android.permissioncontroller:id/permission_allow_button",
                         text="ALLOW")
        self.device(resourceId="com.android.permissioncontroller:id/permission_allow_button", text="ALLOW").click()
        self.delay()

    def enter_personal_info(self):
        """Enter random name and date of birth."""
        # Enter name
        print("Waiting for name input field to load...")
        wait_for_element(self.device, class_name="android.widget.EditText")

        with open("names.txt", "r") as file:
            names = file.readlines()
            name = random.choice(names).strip()

        print(f"Entering name: {name}")
        for char in name:
            self.device.shell(f"input text {char}")
            time.sleep(0.05)  # Reduced from 0.1

        # Enter DOB
        year = random.choice(["2000", "2001", "2002"])
        month = f"{random.randint(1, 12):02}"
        day = f"{random.randint(1, 28):02}"

        print(f"Entering DOB: {month}/{day}/{year}")

        wait_for_element(self.device, class_name="android.widget.EditText", description="Enter month")
        self.device(className="android.widget.EditText", description="Enter month").click()

        # Enter all parts with less delay
        for part in [month, day, year]:
            for digit in part:
                self.device.shell(f"input text {digit}")
                time.sleep(0.05)  # Reduced from 0.1
            time.sleep(0.5)  # Reduced from 1

        print("Clicking Continue after entering info...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def click_continue_buttons(self):
        """Click various continue buttons."""

        print("Clicking 'Continue' button...")

        # Wait for the "Continue" button to appear and click it
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

        print("Clicking 'Confirm' button...")

        # Wait for the "Confirm" button to appear and click it
        if wait_for_element(self.device, class_name="android.widget.TextView", text="Confirm"):
            self.device(className="android.widget.TextView", text="Confirm").click()
            self.delay()

    def click_next_button(self):
        """Click the next/continue button."""
        print("Clicking next button...")
        try:
            # Try to find the arrow button by its class
            self.device(className="android.widget.ImageButton").click()
        except:
            try:
                # Try by description
                self.device(description="Continue").click()
            except:
                # Last resort - try clicking where the arrow appears
                # You might need to adjust these coordinates based on your screen
                self.device.click(900, 1800)
        self.delay()

    def select_gender(self):
        """Select gender preference."""
        print("Selecting gender...")
        if wait_for_element(self.device, class_name="android.widget.TextView", text="Woman"):
            self.device(className="android.widget.TextView", text="Woman").click()
            self.delay()

        # Try multiple methods to click the continue button
        print("Clicking Continue after selecting gender...")
        try:
            # Try to find the arrow button by its class and index (bottom right corner)
            if self.device(className="android.widget.ImageButton").exists:
                self.device(className="android.widget.ImageButton").click()
            elif self.device(className="android.widget.Button", description="Continue").exists:
                self.device(className="android.widget.Button", description="Continue").click()
            elif self.device(className="android.view.View", description="Continue").exists:
                self.device(className="android.view.View", description="Continue").click()
            else:
                # If no button is found, try clicking the bottom right corner
                screen_size = self.device.window_size()
                x = screen_size[0] - 50  # 50 pixels from the right
                y = screen_size[1] - 50  # 50 pixels from the bottom
                self.device.click(x, y)
            print("Continue button clicked successfully")
        except Exception as e:
            print(f"Error clicking continue button: {str(e)}")
        self.delay()

    def handle_next_buttons(self):
        """Handle clicking next buttons for additional screens."""
        # Try multiple methods to click the continue button
        print("Clicking Continue after selecting gender...")
        try:
            # Try to find the arrow button by its class and index (bottom right corner)
            if self.device(className="android.widget.ImageButton").exists:
                self.device(className="android.widget.ImageButton").click()
            elif self.device(className="android.widget.Button", description="Continue").exists:
                self.device(className="android.widget.Button", description="Continue").click()
            elif self.device(className="android.view.View", description="Continue").exists:
                self.device(className="android.view.View", description="Continue").click()
            else:
                # If no button is found, try clicking the bottom right corner
                screen_size = self.device.window_size()
                x = screen_size[0] - 50  # 50 pixels from the right
                y = screen_size[1] - 50  # 50 pixels from the bottom
                self.device.click(x, y)
            print("Continue button clicked successfully")
        except Exception as e:
            print(f"Error clicking continue button: {str(e)}")
        self.delay()

    def skip_optional_sections(self):
        """Skip optional sections."""
        print("Skipping optional sections...")
        if wait_for_element(self.device, resource_id="com.bumble.app:id/reg_footer_label", text="Skip"):
            self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").click()
            self.delay()

    def select_five_things(self):
        """Dynamically select between 3 and 5 checkboxes."""
        print("Selecting interests from what's actually on the screen...")

        xml_content = self.device.dump_hierarchy()
        root = ElementTree.fromstring(xml_content)

        checkboxes_found = []
        for node in root.iter():
            if node.attrib.get("class") == "android.widget.CheckBox":
                label_text = node.attrib.get("content-desc") or node.attrib.get("text")
                if label_text:
                    checkboxes_found.append(label_text.strip())

        print(f"Found {len(checkboxes_found)} checkboxes: {checkboxes_found}")

        if not checkboxes_found:
            print("No checkboxes found. Attempting to click Skip...")
            try:
                skip_button = self.device(className="android.widget.TextView", text="Skip")
                if skip_button.exists:
                    skip_button.click()
                    self.delay()
                else:
                    print("Skip button not found")
            except Exception as e:
                print(f"Error clicking Skip: {e}")
            return

        num_to_select = random.randint(3, 5)
        selected_labels = random.sample(checkboxes_found, num_to_select)
        print(f"Selecting these {num_to_select} items: {selected_labels}")

        for label in selected_labels:
            try:
                check_box = self.device(
                    className="android.widget.CheckBox",
                    description=label
                )

                if not check_box.exists:
                    check_box = self.device(
                        className="android.widget.CheckBox",
                        text=label
                    )

                if check_box.exists:
                    print(f"Clicking checkbox: {label}")
                    check_box.click()
                    time.sleep(0.5)
                else:
                    print(f"Checkbox '{label}' not found on screen. Skipping.")
            except Exception as e:
                print(f"Error clicking checkbox '{label}': {e}")

        print("Clicking 'Continue' after selecting values...")
        continue_btn = self.device(className="android.view.View", description="Continue")
        if continue_btn.exists:
            continue_btn.click()
            self.delay()
        else:
            print("No 'Continue' button found.")


    def select_dating_preference(self):
        """Select dating preference."""
        print("Setting dating preferences...")
        if wait_for_element(self.device, class_name="android.widget.TextView", text="Men"):
            self.device(className="android.widget.TextView", text="Men").click()
            self.delay()

            # Try multiple methods to click the continue button
        print("Clicking Continue after selecting gender...")
        try:
            # Try to find the arrow button by its class and index (bottom right corner)
            if self.device(className="android.widget.ImageButton").exists:
                self.device(className="android.widget.ImageButton").click()
            elif self.device(className="android.widget.Button", description="Continue").exists:
                self.device(className="android.widget.Button", description="Continue").click()
            elif self.device(className="android.view.View", description="Continue").exists:
                self.device(className="android.view.View", description="Continue").click()
            else:
                # If no button is found, try clicking the bottom right corner
                screen_size = self.device.window_size()
                x = screen_size[0] - 50  # 50 pixels from the right
                y = screen_size[1] - 50  # 50 pixels from the bottom
                self.device.click(x, y)
            print("Continue button clicked successfully")
        except Exception as e:
            print(f"Error clicking continue button: {str(e)}")
        self.delay()

    def select_relationship_goal(self):
        """Select relationship goal."""
        print("Selecting relationship goal...")
        options = [
            "A long-term relationship",
            "Fun, casual dates",
            "Intimacy, without commitment"
        ]
        choice = random.choice(options)
        if wait_for_element(self.device, class_name="android.widget.TextView", text=choice):
            self.device(className="android.widget.TextView", text=choice).click()
            self.delay()

        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def setup_profile_preferences(self):
        """Set up profile preferences."""

        # Gender selection
        print("Selecting gender...")
        if wait_for_element(self.device, class_name="android.widget.TextView", text="Woman"):
            self.device(className="android.widget.TextView", text="Woman").click()
            self.delay()

        # Click next buttons
        print("Clicking 'Next' button...")
        self.click_next_button()
        self.click_next_button()

        # Skip certain sections
        print("Skipping optional sections...")
        if wait_for_element(self.device, resource_id="com.bumble.app:id/reg_footer_label", text="Skip"):
            self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").click()
            self.delay()

        # Click next button after skipping
        self.click_next_button()

        # Select dating preference
        print("Setting dating preferences...")
        if wait_for_element(self.device, class_name="android.widget.TextView", text="Men"):
            self.device(className="android.widget.TextView", text="Men").click()
            self.delay()

        if wait_for_element(self.device, resource_id="com.bumble.app:id/reg_footer_button",
                            class_name="android.widget.Button"):
            self.device(resourceId="com.bumble.app:id/reg_footer_button", className="android.widget.Button").click()
            self.delay()

        # Select relationship goal
        print("Selecting relationship goal...")
        options = [
            "A long-term relationship",
            "Fun, casual dates",
            "Intimacy, without commitment"
        ]
        choice = random.choice(options)
        if wait_for_element(self.device, class_name="android.widget.TextView", text=choice):
            self.device(className="android.widget.TextView", text=choice).click()
            self.delay()

        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def fill_profile_details(self):
        """Fill in profile details."""
        # Skip height selection
        if wait_for_element(self.device, resource_id="com.bumble.app:id/reg_footer_label", text="Skip"):
            self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").click()
            self.delay()

        # Scroll and select interests
        self.device(scrollable=True).scroll.toEnd()
        self.delay()

        # Select random interests
        interests = [
            "Cats", "Dogs", "Wine", "Horror", "Baking",
            "Coffee", "Dancing", "Exploring new cities"
        ]
        selected_interests = random.sample(interests, random.randint(3, 5))
        for interest in selected_interests:
            if self.device(className="android.widget.CheckBox", description=interest).exists:
                self.device(className="android.widget.CheckBox", description=interest).click()
                self.delay(0.5)

        # Continue after interests
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

        # Select values
        values = [
            "Ambition", "Confidence", "Empathy", "Generosity",
            "Humor", "Kindness", "Leadership", "Loyalty"
        ]
        selected_values = random.sample(values, random.randint(2, 3))
        for value in selected_values:
            if self.device(className="android.widget.CheckBox", description=value).exists:
                self.device(className="android.widget.CheckBox", description=value).click()
                self.delay(0.5)

        self.device(className="android.view.View", description="Continue").click()
        self.delay()

    def select_interests(self):
        """Select random interests from the list."""
        print("Selecting interests...")

        # Scroll to see all options
        self.device(scrollable=True).scroll.toEnd()
        self.delay()

        # List of possible interests
        interests = [
            "Cats", "Dogs", "Wine", "Horror", "Baking",
            "Coffee", "Dancing", "Exploring new cities",
        ]

        # Select 3-5 random interests
        selected_interests = random.sample(interests, random.randint(3, 5))
        for interest in selected_interests:
            if self.device(className="android.widget.CheckBox", description=interest).exists:
                self.device(className="android.widget.CheckBox", description=interest).click()
                self.delay(0.5)

        # Click Continue after selecting interests
        print("Clicking Continue after selecting interests...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def select_values(self):
        """Select random values from the list."""
        print("Selecting values...")

        # List of possible values
        values = [
            "Ambition", "Confidence", "Empathy", "Generosity",
            "Humor", "Kindness", "Leadership", "Loyalty"
        ]

        # Select 2-3 random values
        selected_values = random.sample(values, random.randint(2, 3))
        for value in selected_values:
            if self.device(className="android.widget.CheckBox", description=value).exists:
                self.device(className="android.widget.CheckBox", description=value).click()
                self.delay(0.5)

        # Click Continue after selecting values
        print("Clicking Continue after selecting values...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def Skip(self):
        """Skip the current screen."""
        print("Attempting to skip screen...")

        # Try multiple skip button variations
        try:
            # Try the footer skip button
            if self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").exists:
                self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").click()
                print("Clicked footer skip button")
            # Try just text "Skip"
            elif self.device(text="Skip").exists:
                self.device(text="Skip").click()
                print("Clicked text skip button")
            # Try skip by class and text
            elif self.device(className="android.widget.TextView", text="Skip").exists:
                self.device(className="android.widget.TextView", text="Skip").click()
                print("Clicked TextView skip button")
            else:
                print("No skip button found")
        except Exception as e:
            print(f"Error during skip: {e}")

        self.delay()

    def select_habits(self):
        """Select drinking and smoking habits."""
        # Drinking habits selection
        print("Starting drinking habits selection...")
        habits = ["I drink sometimes", "I rarely drink", "No, I don't drink"]
        selected_habit = random.choice(habits)
        print(f"Attempting to select habit: {selected_habit}")
        partial_map = {
            "I drink sometimes": "sometimes",
            "I rarely drink": "rarely",
            "No, I don't drink": "don"
        }

        self.device(
            className="android.widget.RadioButton",
            descriptionContains=partial_map[selected_habit]
        ).click()
        self.delay()

        # Continue after smoking selection
        print("Clicking 'Continue' after smoking selection...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def handle_kids_questions(self):
        """Handle kids questions."""
        print("Starting kids questions...")

        # First question about having kids (only select "Don't have kids")
        print("Selecting 'Don't have kids'")
        self.device(
            className="android.widget.RadioButton",
            descriptionContains="Don"
        ).click()
        self.delay()

        # Second question about future kids (only "Open to kids" and "Want kids")
        future_choices = ["Open to kids", "Want kids"]
        selected_choice = random.choice(future_choices)
        print(f"Selecting future kids preference: {selected_choice}")
        future_map = {
            "Open to kids": "Open",
            "Want kids": "Want"
        }

        self.device(
            className="android.widget.RadioButton",
            descriptionContains=future_map[selected_choice]
        ).click()
        self.delay()

        # Continue after selections
        print("Clicking 'Continue' after kids questions...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

    def complete_profile_setup(self):
        """Complete the profile setup process."""
        print("Starting profile setup process...")

        # Skip race selection
        print("Attempting to skip race selection...")
        if wait_for_element(self.device, resource_id="com.bumble.app:id/reg_footer_label", text="Skip"):
            self.device(resourceId="com.bumble.app:id/reg_footer_label", text="Skip").click()
            self.delay()

        # Drinking habits selection
        print("Starting drinking habits selection...")
        habits = ["Yes, I drink", "I drink sometimes", "I rarely drink", "No, I don't drink"]
        selected_habit = random.choice(habits)
        print(f"Attempting to select habit: {selected_habit}")
        partial_map = {
            "Yes, I drink": "Yes, I",
            "I drink sometimes": "sometimes",
            "I rarely drink": "rarely",
            "No, I don't drink": "don"
        }

        self.device(
            className="android.widget.RadioButton",
            descriptionContains=partial_map[selected_habit]
        ).click()
        self.delay()

        # Dump current UI elements
        print("Dumping current UI elements before smoking selection...")
        os.system('adb shell uiautomator dump /sdcard/window_dump.xml')
        os.system('adb pull /sdcard/window_dump.xml')
        print("UI dump completed")

        # Smoking preference selection
        print("Attempting to select smoking preference...")
        if wait_for_element(self.device, class_name="android.widget.RadioButton", description="No, I don’t smoke"):
            self.device(className="android.widget.RadioButton", description="No, I don’t smoke").click()
            self.delay()

        # Continue after smoking selection
        print("Clicking 'Continue' after smoking selection...")
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

        # Kids questions
        print("Handling kids questions...")
        if wait_for_element(self.device, class_name="android.widget.RadioButton", description="Don’t have kids"):
            self.device(className="android.widget.RadioButton", description="Don’t have kids").click()
            self.delay()

        choices = ["Open to kids", "Want kids"]
        selected_choice = random.choice(choices)
        print(f"Selecting kids preference: {selected_choice}")
        self.device(className="android.widget.RadioButton", description=selected_choice).click()
        self.delay()
        self.device(className="android.view.View", description="Continue").click()
        self.delay()

        # Continue after kids questions
        if wait_for_element(self.device, class_name="android.view.View", description="Continue"):
            self.device(className="android.view.View", description="Continue").click()
            self.delay()

        # What's important in your life?
        if self.device(textContains="important in your life").exists:
            print("Skipping 'What’s important in your life?' screen...")
            self.device(text="Skip").click()
            self.delay()

        # How about causes and communities?
        print("Skipping 'How about causes and communities?' screen...")
        if wait_for_element(self.device, text="How about causes and communities?"):
            self.device(text="Skip").click()
            self.delay()

        # What's it like to date you?
        if self.device(textContains="like to date you").exists:
            print("Skipping 'What’s it like to date you?' screen...")
            self.device(text="Skip").click()
            self.delay()

        # Move on to photo upload
        print("Now moving on to photo upload...")
        self.setup_photos()

    def setup_photos(self):
        """Set up profile photos with retry logic."""
        max_retries = 3
        retry_delay = 2

        # Add photos button
        for attempt in range(max_retries):
            try:
                if self.device(className="android.widget.Button", description="Add photo 1").exists:
                    self.device(className="android.widget.Button", description="Add photo 1").click()
                    self.delay()
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"Add photo button not found, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
            except Exception as e:
                print(f"Error clicking add photo button: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        # Upload photos button
        for attempt in range(max_retries):
            try:
                if self.device(className="android.widget.TextView", text="Upload photos").exists:
                    self.device(className="android.widget.TextView", text="Upload photos").click()
                    self.delay()
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"Upload photos button not found, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
            except Exception as e:
                print(f"Error clicking upload photos button: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        # Allow photo access
        for attempt in range(max_retries):
            try:
                if self.device(className="android.widget.Button",
                               resourceId="com.android.permissioncontroller:id/permission_allow_button",
                               text="ALLOW").exists:
                    self.device(className="android.widget.Button",
                                resourceId="com.android.permissioncontroller:id/permission_allow_button",
                                text="ALLOW").click()
                    self.delay()
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"Allow button not found, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
            except Exception as e:
                print(f"Error clicking allow button: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        # Select pictures
        for index in range(1, 7):  # Try to select up to 6 photos
            for attempt in range(max_retries):
                try:
                    picture_node = self.device(className="android.widget.FrameLayout",
                                               resourceId="com.bumble.app:id/media_view",
                                               index=index)
                    if picture_node.exists:
                        picture_node.click()
                        self.delay()
                        break
                    else:
                        if attempt < max_retries - 1:
                            print(f"Picture {index} not found, retrying... ({attempt + 1}/{max_retries})")
                            time.sleep(retry_delay)
                except Exception as e:
                    print(f"Error selecting picture {index}: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)

        # Save button
        for attempt in range(max_retries):
            try:
                if self.device(className="android.widget.Button",
                               resourceId="com.bumble.app:id/navbar_right_content_text",
                               text="Save").exists:
                    self.device(className="android.widget.Button",
                                resourceId="com.bumble.app:id/navbar_right_content_text",
                                text="Save").click()
                    self.delay(15)  # Longer delay for photo upload
                    break
                else:
                    if attempt < max_retries - 1:
                        print(f"Save button not found, retrying... ({attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
            except Exception as e:
                print(f"Error clicking save button: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)

        # Continue after photos
        print("Clicking 'Continue' after photos...")
        if wait_for_element(self.device, class_name="android.widget.Button",
                            resource_id="com.bumble.app:id/reg_footer_button", description="Continue"):
            self.device(className="android.widget.Button", resourceId="com.bumble.app:id/reg_footer_button",
                        description="Continue").click()
            self.delay()
    
    def select_opening_move(self):
        """Selects introvert/extrovert option or hits Skip if not found"""
        try:
            introvert_extrovert = self.device(text="Are you more of an introvert or an extrovert?")
            if introvert_extrovert.exists:
                print("Selecting introvert/extrovert opening move...")
                introvert_extrovert.click()
                self.delay()
            else:
                print("Introvert option not found, clicking Skip...")
                skip_button = self.device(text="Skip")
                if skip_button.exists:
                    skip_button.click()
                    self.delay()
                    return
                
            print("Clicking Continue using multiple methods...")
            try:
                if self.device(className="android.widget.ImageButton").exists:
                    self.device(className="android.widget.ImageButton").click()
                elif self.device(className="android.widget.Button", description="Continue").exists:
                    self.device(className="android.widget.Button", description="Continue").click()
                elif self.device(className="android.view.View", description="Continue").exists:
                    self.device(className="android.view.View", description="Continue").click()
                else:
                    screen_size = self.device.window_size()
                    x = screen_size[0] - 50  
                    y = screen_size[1] - 50  
                    self.device.click(x, y)
                print("Continue button clicked successfully")
            except Exception as e:
                print(f"Error clicking continue button: {str(e)}")
            self.delay()
        except Exception as e:
            print(f"Error in opening move selection: {e}")




    def finish_registration(self):
        """Complete the final registration steps."""

        # Accept terms
        print("Clicking 'I accept' to accept terms...")
        if wait_for_element(self.device, class_name="android.widget.Button", text="I accept",
                            resource_id="com.bumble.app:id/pledge_cta"):
            self.device(className="android.widget.Button", text="I accept",
                        resourceId="com.bumble.app:id/pledge_cta").click()
            self.delay()

    def run_registration_flow(self):
        """Execute the complete registration flow."""
        self.click_use_cell_phone_button()

        while True:
            phone_number = self.request_phone_number()
            if not phone_number:
                return False

            self.enter_phone_number(phone_number)
            self.click_next_button()
            self.click_ok_button()
            self.handle_call_me_screen()

            # Wait for SMS code
            start_time = time.time()
            sms_code = None
            while time.time() - start_time < 35:
                sms_code = self.check_sms_code()
                if sms_code:
                    break
                time.sleep(5)

            if sms_code:
                self.enter_sms_code_and_continue(sms_code)
                self.enable_location_and_notifications()
                self.enter_name()
                self.enter_date_of_birth()
                self.click_continue_buttons()
                self.setup_profile_preferences()
                self.fill_profile_details()
                # Only call complete_profile_setup without setup_photos
                self.complete_profile_setup()
                self.finish_registration()
                return True
            else:
                self.retry_with_new_number()

    def run_screen_loop(self):
        """Entry point for screen-driven registration"""
        print("Starting screen-driven registration flow...")
        self.dynamic_flow.run_flow()
        return self.dynamic_flow.finished


def main():
    """Main function to execute the entire workflow."""
    try:
        # Add small random delay to prevent simultaneous connections
        time.sleep(random.uniform(1, 5))

        # Initialize and setup cloud phone
        cloud_phone = CloudPhoneManager()
        creation_response = cloud_phone.create_profile()

        if not cloud_phone.profile_id:
            print("Failed to create profile.")
            return

        # Start the profile
        profile_url = cloud_phone.start_profile()
        print(f"Profile started successfully. URL: {profile_url}")

        # Wait for initialization
        print("Waiting for cloud phone to initialize...")
        time.sleep(80)

        # Process and upload images
        cloud_phone.process_subfolder()

        # Enable ADB and get connection info
        print("Enabling ADB...")
        cloud_phone.enable_adb()

        print("Getting ADB info...")
        adb_info = cloud_phone.get_adb_info()

        if not adb_info:
            raise Exception("Failed to get ADB info")

        print("ADB info retrieved successfully")

        # Create ADB address for connection
        adb_address = f"{adb_info['ip']}:{adb_info['port']}"
        print(f"Connecting to device at: {adb_address}")

        # Initialize ADB connection and glogin WITHOUT killing the server
        print("Initializing device connection...")
        os.system(f"adb connect {adb_address}")
        time.sleep(2)
        os.system(f'adb shell "glogin {adb_info["password"]}"')
        time.sleep(2)

        try:
            bumble = BumbleRegistration(adb_address, adb_info['password'])
        except Exception as e:
            print(f"Error initializing BumbleRegistration: {str(e)}")
            raise

        # Only start Bumble after all connections are established
        print("Starting Bumble app...")
        cloud_phone.start_bumble()
        print("Waiting for Bumble to initialize...")
        time.sleep(5)

        # Run the registration process
        success = bumble.run_screen_loop()

        if success:
            print("Bumble registration completed successfully!")
        else:
            print("Bumble registration failed.")

    except Exception as e:
        print(f"Error during automation process: {str(e)}")
        import traceback
        print("Full error details:")
        print(traceback.format_exc())


if __name__ == "__main__":
    main()