import requests
from bs4 import BeautifulSoup

url = "https://reviewers.joss.theoj.org/reviewers"
response = requests.get(url)
soup = BeautifulSoup(response.text, "html.parser")

print(response.url)
print(response.status_code)
print(response.text[:1000])  # Print the first 1000 characters

# Example: Extract reviewer names (adjust selector as needed)
reviewers = []
for reviewer in soup.select(".reviewer-name"):  # Update selector based on actual HTML
    reviewers.append(reviewer.get_text(strip=True))

print(f"Found {len(reviewers)} reviewers.")
for name in reviewers:
    print(name)

# Save the page content to a file
with open("page.html", "w", encoding="utf-8") as f:
    f.write(response.text)