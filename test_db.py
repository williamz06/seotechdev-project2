from api.db import get_dashboard_predictions
print("fetchingRecords")
try: 
    data = get_dashboard_predictions()
    print(f"Worked found {len(data)} records")
    if len(data) > 0:
        print("\nsample record:")
        print(data[0])
    else: 
        print("empty data")
except Exception as e:
    print(f"Error fetching records: {e}")