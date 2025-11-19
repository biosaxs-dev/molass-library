import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Set up the Selenium WebDriver (Chrome example)
driver = webdriver.Chrome()  # Or use webdriver.Firefox() if you prefer

try:
    # 1. Go to the reviewers page
    driver.get("https://reviewers.joss.theoj.org/reviewers")
    time.sleep(2)

    # 2. Click the "Log in with GitHub" button
    # Wait for the button to be present, then click it
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[text()='Log in with GitHub']"))
    )
    login_button = driver.find_element(By.XPATH, "//button[text()='Log in with GitHub']")
    login_button.click()
    time.sleep(2)

    # 3. If not already logged in to GitHub, enter your credentials
    # (You may need to adjust these selectors if GitHub changes its login page)
    if "github.com/login" in driver.current_url:
        username = driver.find_element(By.ID, "login_field")
        password = driver.find_element(By.ID, "password")
        username.send_keys(os.environ.get("MY_GITHUB_USERNAME", ""))
        password.send_keys(os.environ.get("MY_GITHUB_PASSWORD", ""))
        password.send_keys(Keys.RETURN)
        # Wait for redirect back to JOSS (user completes 2FA manually)
        WebDriverWait(driver, 300).until(
            lambda d: "reviewers.joss.theoj.org" in d.current_url
        )

    # 4. If GitHub asks for authorization, click "Authorize"
    if "authorize" in driver.current_url:
        authorize_button = driver.find_element(By.NAME, "authorize")
        authorize_button.click()
        time.sleep(2)

    time.sleep(30)

    # 5. Now you should be on the reviewers page, logged in
    # Save the page source or parse with BeautifulSoup
    html = driver.page_source
    with open("reviewers_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved logged-in reviewers page to reviewers_page.html")

finally:
    driver.quit()