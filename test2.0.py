from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

chrome_options = Options()
# If you don't have a display (headless server), enable headless:
# chrome_options.add_argument("--headless")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)

driver.get("https://www.google.com")
print("Title:", driver.title)

driver.quit()





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