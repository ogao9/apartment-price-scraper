import os
import json
import datetime
from dotenv import load_dotenv

import requests
from bs4 import BeautifulSoup
from openai import OpenAI

import google_sheets_helper

load_dotenv()


def get_and_save_html(urls):
    for url in urls:
        r = requests.get(url, verify=False)

        filename = url.split("/")[-1] + ".html"
        filepath = os.path.join("data", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(r.text)


def extract_relevant_html(html, id):
    soup = BeautifulSoup(html, "html.parser")
    res = soup.find(id=id)

    return res


def get_relevant_data(html):
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    example_json = {
        "available units": [
            {
                "Unit number": "601",
                "price": "3000",
                "size (sqft)": "900",
                "floor": "3",
                "date available": "06/01/2024",
                "other": "This unit has a balcony",
            }
        ]
    }

    instructions = f"I am going to give you the HTML of a webpage that lists available apartments. List all available 2 bedroom apartments as well as the price, size, floor, date available, and any other relevant information in JSON format. The data schema should be like this: {json.dumps(example_json)}. Here is the HTML: {html} "

    MODEL = "gpt-4o-mini"
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": instructions},
        ],
        response_format={"type": "json_object"},
        temperature=0.5,
    )

    response_content = response.choices[0].message.content
    response_object = json.loads(response_content)

    print("------\nResponse: \n", response_object)
    return response_object


def add_to_google_sheets(sheet, json_data, apt_name):
    data = []
    current_time = datetime.datetime.now().strftime("%m/%d/%Y %H:%M:%S")

    for unit in json_data["available units"]:
        data.append(
            [
                current_time,
                apt_name,
                unit["Unit number"],
                unit["price"],
                unit["size (sqft)"],
                unit["floor"],
                unit["date available"],
                unit["other"],
            ]
        )

    google_sheets_helper.append_values(sheet, data)


"""
For equity apartments, we only care about the html in the div with id bedroom-type-2 
"""
equity_apt_urls = [
    "https://www.equityapartments.com/san-francisco-bay/soma/soma-square-apartments",
    "https://www.equityapartments.com/san-francisco/potrero-hill/potrero-1010-apartments",
    "https://www.equityapartments.com/san-francisco-bay/mission-bay/azure-apartments",
    "https://www.equityapartments.com/san-francisco/design-district/one-henry-adams-apartments",
    "https://www.equityapartments.com/san-francisco/soma/855-brannan-apartments"
    "https://www.equityapartments.com/san-francisco/rincon-hill/340-fremont-apartments"
]
relevant_id = "bedroom-type-2"

def main():
    # remove all files in the data/ directory
    old_files = os.listdir("data/")
    for file in old_files:
        os.remove(os.path.join("data", file))

    sheet = google_sheets_helper.get_sheet()
    get_and_save_html(equity_apt_urls)
    
    html_files = os.listdir("data/")
    for file in html_files:
        apt_name = os.path.splitext(file)[0]
        html = ""
        with open(os.path.join("data", file), "r", encoding="utf-8") as f:
            html = f.read()

        res = extract_relevant_html(html, relevant_id)
        json_data = get_relevant_data(res)
        add_to_google_sheets(sheet, json_data, apt_name)

    google_sheets_helper.set_date_format(sheet)


if __name__ == "__main__":
    main()
