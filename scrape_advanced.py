import os
import datetime
from typing import Optional
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI

import google_sheets_helper

load_dotenv()


def save_scrape_content(content):
    filename = "test.txt"
    # filepath = os.path.join("data", filename)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)


def scrape_with_jina(url):
    jina_url = "https://r.jina.ai/" + url
    r = requests.get(jina_url)

    return r.text


def scrape_with_playwright(url):
    with sync_playwright() as p:
        # browser = p.chromium.launch(headless=False, slow_mo=50)
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)

        html = page.content()
        browser.close()

    return html


# Cleaning --------------------------------------------
def remove_unwanted_tags(html_content, unwanted_tags=["script", "style"]):
    soup = BeautifulSoup(html_content, "html.parser")

    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()

    return str(soup)


def extract_tags(html_content, tags: list[str]):
    """
    Input: HTML content and a list of tags
    Output: a string of the text content of those tags
    """
    soup = BeautifulSoup(html_content, "html.parser")
    text_parts = []

    for tag in tags:
        elements = soup.find_all(tag)
        for element in elements:
            text_parts.append("".join(element.find_all(string=True, recursive=False)))
            # text_parts.append(element.get_text())

    return " ".join(text_parts)


def remove_unessesary_lines(content):
    lines = content.split("\n")
    stripped_lines = [line.strip() for line in lines]
    non_empty_lines = [line for line in stripped_lines if line]

    # Remove duplicated lines (while preserving order) -- don't need this because we changed the soup find method
    # seen = set()
    # deduped_lines = [line for line in non_empty_lines if not (
    #     line in seen or seen.add(line))]

    # Join the cleaned lines
    cleaned_content = "\n".join(non_empty_lines)

    return cleaned_content


def clean_playwright_html(html, wanted_tags):
    cleaned = remove_unwanted_tags(html)
    cleaned = extract_tags(cleaned, wanted_tags)
    cleaned = remove_unessesary_lines(cleaned)

    return cleaned


# Extraction -----------------------------------------------------
class ApartmentInfo(BaseModel):
    unit_number: Optional[str] = Field(
        default=None, description="The unit number of the available unit"
    )
    price: int = Field(default=None, description="The price of the available unit")
    size: Optional[int] = Field(
        default=None, description="The size of the available unit in square feet"
    )
    floor: Optional[int] = Field(
        default=None, description="The floor of the available unit"
    )
    date_available: Optional[str] = Field(
        default=None,
        description="The date the unit is available in the format: mm/dd/yyyy",
    )
    other: Optional[str] = Field(
        default=None, description="Other information about the unit"
    )

    def to_dict(self):
        return self.dict()


class ApartmentInfoList(BaseModel):
    apartment_info: list[ApartmentInfo] = Field(
        default=None, description="A list of available apartments"
    )


class ApartmentName(BaseModel):
    name: str = Field(default=None, description="The name of the apartment complex")

    def __str__(self):
        return self.name


def extract_apartment_info(text_data):
    openai_api_key = os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    structured_llm = llm.with_structured_output(ApartmentInfoList)

    prompt = f"Extract the apartment information from the following text data containing information about available apartments. Give me the information of all available 2 bedroom apartments as a list:\n{text_data}"
    response = structured_llm.invoke(prompt)

    response_list = [item for item in response]

    json_data = response_list[0][1]
    data = []
    for unit in json_data:
        data.append(unit.to_dict())

    return data


def extract_apartment_name(text_data):
    openai_api_key = os.getenv("OPENAI_API_KEY")

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=openai_api_key)
    structured_llm = llm.with_structured_output(ApartmentName)

    prompt = (
        f"Extract the name of the apartment from the following text data:\n{text_data}"
    )
    response = structured_llm.invoke(prompt)

    return str(response)


# Driver code -----------------------------------------------------
def add_to_google_sheets(sheet, apt_list, apt_name):
    data = []
    current_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")

    for unit in apt_list:
        data.append(
            [
                current_time,
                apt_name,
                unit["unit_number"],
                unit["price"],
                unit["size"],
                unit["floor"],
                unit["date_available"],
                unit["other"],
            ]
        )

    google_sheets_helper.append_values(sheet, data)


test_url = "https://www.essexapartmenthomes.com/apartments/san-francisco/mb360/floor-plans-and-pricing"
# test_url = "https://www.udr.com/san-francisco-bay-area-apartments/san-francisco/channel-mission-bay/apartments-pricing/"

essex_apt_urls = [
    "https://www.essexapartmenthomes.com/apartments/san-francisco/bennett-lofts/floor-plans-and-pricing",
    "https://www.essexapartmenthomes.com/apartments/san-francisco/mb360/floor-plans-and-pricing"
    "https://www.essexapartmenthomes.com/apartments/san-francisco/500-folsom/floor-plans-and-pricing",
]

equity_apt_urls = [
    "https://www.equityapartments.com/san-francisco-bay/soma/soma-square-apartments",
    "https://www.equityapartments.com/san-francisco/potrero-hill/potrero-1010-apartments",
    "https://www.equityapartments.com/san-francisco-bay/mission-bay/azure-apartments",
    "https://www.equityapartments.com/san-francisco/design-district/one-henry-adams-apartments",
    "https://www.equityapartments.com/san-francisco/soma/855-brannan-apartments"
    "https://www.equityapartments.com/san-francisco/rincon-hill/340-fremont-apartments",
]

# has load more button
avalon_url = [
    "https://www.avaloncommunities.com/california/san-francisco-apartments/avalon-at-mission-bay/#community-unit-listings"
]

# has load more button
udr_apt_urls = [
    "https://www.udr.com/san-francisco-bay-area-apartments/san-francisco/edgewater/apartments-pricing/#/",
    "https://www.udr.com/san-francisco-bay-area-apartments/san-francisco/388-beale/apartments-pricing/#/",
]


def scrape_equity_apt_urls():

    for url in equity_apt_urls:
        content = scrape_with_jina(url)
        # save_scrape_content(content)

        apt_list = extract_apartment_info(content)
        apt_name = extract_apartment_name(content)

        print(f"Response for {apt_name}:\n", apt_list)


def main():
    wanted_tags = ["p", "div", "a", "span", "h1", "h2", "h3", "h4", "h5", "h6"]

    scrape_equity_apt_urls()

    # content = scrape_with_jina(test_url)
    # save_scrape_content(content)

    # html = scrape_with_playwright(test_url)
    # html = clean_playwright_html(html)
    # save_scrape_content(html)

    # with open("test.txt", "r", encoding="utf-8") as f:
    #     text_data = f.read()

    # sheet = google_sheets_helper.get_sheet()
    # apt_list = extract_apartment_info(text_data)
    # apt_name = extract_apartment_name(text_data)

    # add_to_google_sheets(sheet, apt_list, apt_name)


if __name__ == "__main__":
    main()
