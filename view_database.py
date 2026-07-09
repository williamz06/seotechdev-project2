<<<<<<< HEAD
from api.kalshi_ingest import app, Market
=======
from kalshi_ingest import app, Market, PriceHistory
>>>>>>> kalshi-api

with app.app_context():
    print("Markets in database:")
    for m in Market.query.all():
        print(m)
        
    print("Price history in database:")
    for ph in PriceHistory.query.all():
        print(ph)