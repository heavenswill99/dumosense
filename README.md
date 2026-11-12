# Dumosense Frontend

This project uses Vite for local development and production builds.

## Backend and Waitlist

The API is the Django application in `backend/`; it uses the configured Aiven MySQL database.
The waitlist endpoint is `POST /api/v1/waitlist/`. Run `npm run dev` (or `npm start`) from this
project directory to start Django, the waitlist email worker, and Vite. Registrations are saved
before the API responds; a database-backed worker sends the confirmation email afterward. This
keeps Resend network latency out of the visitor's submit wait. To run Django separately:

```powershell
cd backend
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Set `VITE_BACKEND_URL=http://127.0.0.1:8000` for local frontend development. For deployment,
set it to the API's HTTPS origin (for example, `https://api.dumosense.com`) before building.
The production build refuses missing, HTTP, or localhost API origins. The API must allow the
frontend's origin in `CORS_ALLOWED_ORIGINS`.

### Resend confirmation email

Configure these only in the backend environment (including cPanel's Python application settings):

```text
RESEND_API_KEY=your_private_resend_api_key
WAITLIST_FROM_EMAIL=hello@your-verified-domain.com
WAITLIST_FROM_NAME=DumoSense
WAITLIST_WEBSITE_URL=https://dumosense.com
```

The public registration endpoint is rate-limited to five submissions per IP per hour by default;
set `WAITLIST_ANON_RATE` in the backend environment to adjust it if needed. Confirmation emails
are queued in the Aiven registration row and retried with a Resend idempotency key. Run
`python manage.py send_waitlist_confirmations` to process the queue once, or add `--watch
--interval 10` for a local worker.
Verify the sender domain with Resend. The API records registrations in Aiven and returns an email
status separately; the frontend reports email delivery as confirmed only after Resend accepts it.
Never put database credentials or the Resend API key in frontend variables.
Confirmation emails embed the DumoSense logo so it does not depend on a publicly reachable logo URL.
The sender avatar shown beside an email is controlled by the recipient's mail provider or the sender's
mailbox profile; it cannot be set by Resend's email body or API.
Publish and link the approved DumoSense Privacy Policy before enabling waitlist registration in production.

### Host the frontend and backend in one cPanel account

The frontend is static files; the Django API is a cPanel Python application. They can share one
cPanel account while using the main domain for the website and an API subdomain for Django.

1. **Create the API subdomain.** In cPanel, create `api.dumosense.com` and enable AutoSSL for it.
   The DNS A record must point to this cPanel account. Do not upload the Django code into the
   subdomain's public document root.
2. **Map a Python application to the API subdomain.** In *Setup Python App*, create an app with:
   - Python version: 3.11 or 3.12 (use a version offered by the host)
   - Application root: `dumosense-api` (cPanel resolves this under `/home/CPANEL_USER/`)
   - Application URL: domain `api.dumosense.com`, URI `/` (the subdomain root)
   - Application startup file: `passenger_wsgi.py`
   - Application entry point: `application`

   Save/create the app and use its **Restart** control after deployment or environment changes.
   If `https://api.dumosense.com/` shows a LiteSpeed `Index of /` page listing files such as
   `cgi-bin` or `php.ini`, the domain is still serving its document root; it is not mapped to
   this Python app. Fix the Application URL mapping before testing CORS or registration.
3. **Upload the backend into the application root.** Upload the *contents* of this project's
   `backend/` directory into `/home/CPANEL_USER/dumosense-api/`, not into a nested
   `/home/CPANEL_USER/dumosense-api/backend/` directory and not into `public_html/`. The
   application root must directly contain `manage.py`, `passenger_wsgi.py`, `requirements.txt`,
   `config/`, `accounts/`, and `waitlist/`. In cPanel Terminal, run the virtualenv activation
   command shown by *Setup Python App*, then:

   ```sh
   cd /home/CPANEL_USER/dumosense-api
   pip install -r requirements.txt
   ```

   Replace `CPANEL_USER` with the cPanel account username. Keep database credentials, CA
   certificates, and logs outside `public_html`.
4. **Add environment variables in the Python app's configuration.** Add each as a separate
   name/value entry in *Setup Python App* (do not include quotes or `export`):

   ```text
   DJANGO_SECRET_KEY=<a new long random secret>
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=api.dumosense.com
   DJANGO_SECURE_SSL_REDIRECT=False
   DB_NAME=<Aiven database name>
   DB_USER=<Aiven database user>
   DB_PASSWORD=<Aiven database password>
   DB_HOST=<Aiven host name>
   DB_PORT=3306
   CORS_ALLOWED_ORIGINS=https://dumosense.com,https://www.dumosense.com
   CSRF_TRUSTED_ORIGINS=https://dumosense.com,https://www.dumosense.com
   RESEND_API_KEY=<private Resend API key>
   WAITLIST_FROM_EMAIL=<verified sender email>
   WAITLIST_FROM_NAME=DumoSense
   WAITLIST_WEBSITE_URL=https://dumosense.com
   WAITLIST_ANON_RATE=5/hour
   ```

   If Aiven requires a CA certificate, upload it under the private application root (for example
   `certs/ca.pem`) and additionally set `DB_SSL_CA=certs/ca.pem`. Allow the cPanel server's
   outbound IP in Aiven's allowed IP addresses. Do not share or put database credentials, the
   Django secret, or the Resend key in frontend settings. Restart the Python app after saving
   these entries. The current backend also always allows the two DumoSense HTTPS origins.
5. **Run migrations and verify Django starts.** In cPanel Terminal, activate the app virtualenv
   and run:

   ```sh
   cd /home/CPANEL_USER/dumosense-api
   python manage.py check
   python manage.py migrate
   ```

   The migration adds the queue-attempt column needed by the current registration code. Restart
   the Python app. Verify that
   `https://api.dumosense.com/api/v1/waitlist/` now responds with a Django/API response (a `405`
   on a browser GET is expected; a LiteSpeed HTML `404` is not). Then verify preflight:

   ```sh
   curl -i -X OPTIONS https://api.dumosense.com/api/v1/waitlist/ \
     -H "Origin: https://dumosense.com" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: content-type"
   ```

   The response should be `200` and include
   `Access-Control-Allow-Origin: https://dumosense.com`. If it still shows a LiteSpeed 404 or
   lacks this header, the request is not reaching the configured Django app; check the app's
   domain/URI mapping and the cPanel Passenger error log.
6. **Schedule confirmation emails.** In *Cron Jobs*, add a task to run each minute (or the shortest
   supported interval), using the Python application's virtualenv interpreter:

   ```sh
   /home/CPANEL_USER/virtualenv/dumosense-api/3.11/bin/python /home/CPANEL_USER/dumosense-api/manage.py send_waitlist_confirmations --limit 25 >> /home/CPANEL_USER/logs/waitlist-mailer.log 2>&1
   ```

   Replace `CPANEL_USER` and `3.11` with the account username and Python version shown by cPanel.
   This task sends queued confirmations and retries transient failures. The visitor sees success
   as soon as the database save completes; the modal reports the email as being processed until
   Resend accepts it.
7. **Build the frontend for the API subdomain.** The production-only `.env.production` file
   points the frontend to `https://api.dumosense.com`; it does not change the local development
   URL in `.env`. Run `npm run build` from this project directory. If your API uses a different
   hostname, update `VITE_BACKEND_URL` in `.env.production` before building. In PowerShell:

   ```powershell
   npm run build
   ```

   Upload the *contents* of `dist/` to the main domain's `public_html` directory. Add SPA rewrite
   rules so routes fall back to `index.html`; existing files and assets must be served directly.
   Rebuild and re-upload `dist/` whenever frontend code or the API URL changes.
8. **Verify the deployment.** Open `https://api.dumosense.com/api/v1/waitlist/` and confirm the
   API responds, then submit one real registration and check the Aiven row, the mailer log, and
   Resend's email log. Do not use an already-registered address for the test.

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the Vite development server.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `dist` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)
