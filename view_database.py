from kalshi_ingest import app, Market

with app.app_context():
    for m in Market.query.all():
        print(m)