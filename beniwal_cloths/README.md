
Beniwal Cloths - BENIWAL'CLOTHS APP (Simple Flask shop)
-------------------------------
How to run:
1. Create a Python 3 virtualenv.
2. pip install -r requirements.txt
3. python app.py
4. Open http://127.0.0.1:5000

Features implemented:
- Seller upload page at /seller/upload (corner upload)
- Products listing with seller name and rating
- Buyer must enter phone and allow geolocation (browser prompt)
- Buy flow returns seller phone; buyer must call seller externally.
  After the call, click "I completed call" and choose Yes/No to confirm purchase.
- Delivery charge fixed at Rs 10.
- Simple SQLite DB stored as beniwal.db
