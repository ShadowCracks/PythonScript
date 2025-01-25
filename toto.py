import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager

# Eventbrite event URL
EVENT_URL = "https://www.eventbrite.ca/e/tropic-like-its-hot-tickets-1203615098159?aff=ebdssbehomepeforyou"

def setup_driver():
    """
    Sets up and returns a Chrome WebDriver instance using webdriver_manager.
    """
    service = Service(ChromeDriverManager().install())
    chrome_options = Options()
    # Uncomment or add options if you need headless mode or other configs:
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def open_eventbrite_page(driver, url):
    """
    Opens the specified Eventbrite page and prints a status message.
    """
    print(f"Opening Eventbrite page: {url}")
    driver.get(url)
    print("Page opened successfully.")

def press_select_tickets(driver):
    """
    Attempts to find and click the 'Select Tickets' button by data-testid.
    Returns True if clicked, False otherwise.
    """
    try:
        select_tickets_button = driver.find_element(
            By.XPATH,
            '//button[@data-testid="scroll-to-date-button"]'
        )
        select_tickets_button.click()
        print("Pressed 'Select Tickets' button (data-testid).")
        return True
    except NoSuchElementException:
        print('No "Select Tickets" button found by data-testid.')
    except Exception as e:
        print(f"Error pressing 'Select Tickets' button by data-testid: {e}")
    return False

def press_get_tickets(driver):
    """
    Attempts to find and click the 'Get Tickets' button.
    Returns True if clicked, False otherwise.
    """
    try:
        get_tickets_button = driver.find_elements(
            By.XPATH,
            '//button[contains(translate(text(),'
            ' "ABCDEFGHIJKLMNOPQRSTUVWXYZ",'
            ' "abcdefghijklmnopqrstuvwxyz"),'
            ' "get tickets")]'
        )
        if get_tickets_button:
            get_tickets_button[0].click()
            print("Pressed 'Get Tickets' button.")
            return True
    except Exception as e:
        print(f"Error pressing 'Get Tickets': {e}")
    return False

def select_tier_quantity(driver, quantity=1):
    """
    Selects the ticket quantity for Tier 2
    """
    try:
        time.sleep(1)
        dropdown = driver.find_element(
            By.CSS_SELECTOR,
            'select[data-automation="quantity-selector-tier-2"]'
        )
        select_obj = Select(dropdown)
        select_obj.select_by_value(str(quantity))  # Convert quantity to string when selecting
        print(f"Set Tier 2 ticket quantity to {quantity}")
        return True
    except Exception as e:
        print(f"Error selecting tier quantity: {e}")
        return False

def press_checkout(driver):
    """
    Attempts to find and click the 'Checkout' button.
    Returns True if the checkout button was found and clicked, False otherwise.
    """
    try:
        checkout_button = driver.find_elements(
            By.XPATH,
            '//button[contains(text(), "Checkout")]'
        )
        if checkout_button:
            checkout_button[0].click()
            print("Proceeded to checkout. Stopping script.")
            return True
    except Exception as e:
        print(f"Error pressing 'Checkout': {e}")
    return False

def press_buttons_continuously():
    """
    The main logic that continuously checks for and clicks the desired buttons
    until checkout is reached or user interrupts with Ctrl+C.
    """
    driver = setup_driver()

    try:
        open_eventbrite_page(driver, EVENT_URL)
        print("Monitoring and constantly clicking relevant buttons...")

        quantity_selected = False

        while True:
            try:
                # Step 1: Press "Select Tickets"
                press_select_tickets(driver)

                # Step 2: Press "Get Tickets"
                press_get_tickets(driver)

                # Step 3: Directly set the <select> quantity to 1 (if not done yet)
                if not quantity_selected:
                    quantity_selected = select_tier_quantity(driver, quantity=1)

                # Step 4: Press "Checkout"
                if press_checkout(driver):
                    break

                # Repeat every 0.01 seconds
                time.sleep(0.01)

            except KeyboardInterrupt:
                print("\nScript stopped by user (KeyboardInterrupt). Exiting gracefully...")
                break

    finally:
        print("Closing browser...")
        driver.quit()

if __name__ == "__main__":
    press_buttons_continuously()
