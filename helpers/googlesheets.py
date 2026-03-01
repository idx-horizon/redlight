from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CREDS='../googlecreds.json'
SID='133lOhBaTYkus5_tQ79QDkBShbCaFYwjTuGWeXMcfxcU'
RANGE={'Ian': 'Summary!H9','Sheila': 'Summary!H10','Joint': 'Summary!H11'}

def get_metrics(spreadsheet_id, ranges, creds_path):
    """
    Fetch one or more ranges and return a dict with friendly labels.
    
    Args:
        ranges: str, list[str], or dict[label] = range
    """
    # Determine if we have labels
    if isinstance(ranges, dict):
        labels = list(ranges.keys())
        range_list = list(ranges.values())
    elif isinstance(ranges, str):
        labels = [ranges]
        range_list = [ranges]
    else:  # list of ranges
        labels = range_list = ranges

    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    service = build("sheets", "v4", credentials=creds)

    result = service.spreadsheets().values().batchGet(
        spreadsheetId=spreadsheet_id,
        ranges=range_list
    ).execute()

    value_ranges = result.get("valueRanges", [])
    output = {}
    for label, vr in zip(labels, value_ranges):
        vals = vr.get("values", [])
        # flatten single cells
        if vals and len(vals) == 1 and len(vals[0]) == 1:
            output[label] = vals[0][0]
        else:
            output[label] = vals
    return output

if __name__ == '__main__':
   cash = get_metrics(SID, RANGE, CREDS)
   print(f'Cash = {cash}')
