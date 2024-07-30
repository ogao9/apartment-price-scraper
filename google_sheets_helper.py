import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
RANGE_NAME = os.getenv("RANGE_NAME")


def get_sheet():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("sheets", "v4", credentials=creds)
    sheet = service.spreadsheets()
    return sheet


def append_values(sheet, values):
    """
    values is a list of lists, where each list represents a row of data
    Ex:
    [
        ["timestamp", "property name", "unit number", "price", "sqft", "beds", "date available", "other notes"]
        ["timestamp", "property name", "unit number", "price", "sqft", "beds", "date available", "other notes"]
    ]
    """

    result = (
        sheet.values()
        .append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body={"values": values},
            insertDataOption="INSERT_ROWS",
        )
        .execute()
    )
    print(f"{(result.get('updates').get('updatedCells'))} cells appended.")
    return result


def read_values(sheet):
    result = (
        sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    )
    values = result.get("values", [])

    if not values:
        print("No data found.")
        return

    for row in values:
        # Print columns A and E, which correspond to indices 0 and 4.
        print(f"{row[0]}, {row[4]}")

    return result


def set_date_format(sheet):
    # set format of date available column to MM/dd/yyyy
    result = sheet.batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startColumnIndex": 6,
                            "endColumnIndex": 7,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE",
                                    "pattern": "MM/dd/yyyy",
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            ]
        },
    ).execute()
    print("{0} cells updated.".format(result.get("totalUpdatedCells")))

    # set format of timestamp column to MM/dd/yyyy hh:mm:ss
    result = sheet.batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": 0,
                            "startColumnIndex": 0,
                            "endColumnIndex": 1,
                        },
                        "cell": {
                            "userEnteredFormat": {
                                "numberFormat": {
                                    "type": "DATE_TIME",
                                    "pattern": "MM/dd/yyyy hh:mm:ss",
                                }
                            }
                        },
                        "fields": "userEnteredFormat.numberFormat",
                    }
                }
            ]
        },
    ).execute()
    print("{0} cells updated.".format(result.get("totalUpdatedCells")))


def test():
    sheet = get_sheet()

    try:
        test_values = [
            [
                "timestamp1",
                "property name1",
                "unit number1",
                "price1",
                "sqft1",
                "beds1",
                "date available1",
                "other notes1",
            ],
            [
                "timestamp2",
                "property name2",
                "unit number2",
                "price2",
                "sqft2",
                "beds2",
                "date available2",
                "other notes2",
            ],
        ]

        append_values(sheet, test_values)

    except HttpError as err:
        print(err)


if __name__ == "__main__":
    test()
