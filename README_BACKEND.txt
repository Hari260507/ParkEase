# ParkEase Backend (Flask + SQLite)

## Requirements
- Python 3.10 or newer
- Internet is needed only once to install Flask.

## Run on Windows / VS Code
1. Extract this ZIP folder.
2. Open the extracted `parking slot` folder in VS Code.
3. Open Terminal > New Terminal.
4. Run:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   py -m pip install -r requirements.txt
   py app.py
   ```

5. Open **http://127.0.0.1:5000** in your browser. Do not open `index.html` directly or use Live Server; the backend must be running.
6. Keep the terminal open while using the site. Press `Ctrl+C` to stop it.

## Backend features
- Signup with hashed passwords and unique mobile numbers
- Login/logout using a server session cookie
- Profile update
- SQLite database (`parkease.db`) created automatically
- 100 slot names (A1-A100) and overlapping-time booking prevention on the server
- My bookings, cancellation, completed booking history
- Demo notification records stored in the database under SMS History

## Important
- The SMS feature is a **demo notification record**; it does not send a real SMS. Real SMS requires an SMS provider and credentials.
- This is a college project/demo setup. Before public deployment, set a strong `PARKEASE_SECRET_KEY`, use HTTPS, configure production hosting, and add appropriate security protections.
- The old localStorage-based accounts/bookings are not automatically imported. Create a new account through the backend signup page.
- The database file is created next to `app.py` the first time you start the server.


## Admin Dashboard (Step 1)
- Open http://127.0.0.1:5000/admin-login.html
- Demo username: admin
- Demo password: ParkEase@123
- Admin dashboard shows slot totals, users, bookings, and booking statuses.
- These demo credentials are for local college testing only. Before deployment, set PARKEASE_ADMIN_USERNAME and PARKEASE_ADMIN_PASSWORD environment variables to private values.


## Booking Reports (Step 3)
- In the Admin Dashboard, click “Booking CSV” to download all booking records.
- Click “Users CSV” to download registered users and booking counts.
- CSV files can be opened with Excel or Google Sheets. Export endpoints require admin login.
- Reports contain personal information (such as names, phone numbers and addresses); keep downloaded files private.
