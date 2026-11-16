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

Set `VITE_BACKEND_URL=http://127.0.0.1:8000` for local frontend development. Production builds
use `.env.production`, currently configured for `https://dumosense-backend.onrender.com`.
The backend must allow the website's origin in `CORS_ALLOWED_ORIGINS`.
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
The registration API does not send emails itself. Production must run a separate, persistent
worker; otherwise registrations remain queued with an email status of `processing`.
Verify the sender domain with Resend. The API records registrations in Aiven and returns an email
status separately; the frontend reports email delivery as confirmed only after Resend accepts it.
Never put database credentials or the Resend API key in frontend variables.
Confirmation emails embed the DumoSense logo so it does not depend on a publicly reachable logo URL.
The sender avatar shown beside an email is controlled by the recipient's mail provider or the sender's
mailbox profile; it cannot be set by Resend's email body or API.
Publish and link the approved DumoSense Privacy Policy before enabling waitlist registration in production.

### Render backend and frontend deployment

The Django API is hosted at `https://dumosense-backend.onrender.com`; the production frontend
must use that URL as `VITE_BACKEND_URL`. The Render service must have the backend environment
variables documented in `backend/.env.example`, including the Aiven database connection,
`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS=dumosense-backend.onrender.com`, and
`CORS_ALLOWED_ORIGINS=https://dumosense.com,https://www.dumosense.com`. Keep `RESEND_API_KEY`
configured as a Render backend environment variable only.

1. **Configure the Render backend.** In the Render service's *Environment* settings, set the
   backend variables from `backend/.env.example`. In particular set
   `DJANGO_ALLOWED_HOSTS=dumosense-backend.onrender.com` and
   `CORS_ALLOWED_ORIGINS=https://dumosense.com,https://www.dumosense.com`, plus valid Aiven and
   Resend backend credentials. Trigger a deploy/restart after changing backend settings.
2. **Apply database migrations on Render.** Configure the Render service's pre-deploy command
   as `python manage.py migrate`, or run migrations in the Render shell using the service's
   Python environment. Check deployment logs for errors.
3. **Create a Render Background Worker for confirmation emails.** Use the same repository and
   backend root directory/environment as the API service. Set its build command to
   `pip install -r requirements.txt` and its start command to
   `python manage.py send_waitlist_confirmations --watch --interval 10`. Copy the backend
   environment variables to the worker, especially the Aiven database settings and
   `RESEND_API_KEY`, `WAITLIST_FROM_EMAIL`, and `WAITLIST_FROM_NAME`. Keep this as a separate,
   continuously running Background Worker; do not use a one-time deploy command for it.
   Confirm the worker is running in Render and check its logs after a test registration; the
   API initially returns `processing`, and the worker should log a successful send.
4. **Build and upload the frontend.** The production-only `.env.production` file points to
   `https://dumosense-backend.onrender.com` and leaves the local development URL in `.env`
   unchanged. Run `npm run build`:

   ```powershell
   npm run build
   ```

   Upload the contents of `dist/` to the frontend host (for cPanel static hosting, the main
   domain's `public_html`). Rebuild and re-upload `dist/` after changing frontend code or the API
   URL.
5. **Verify the deployment.** `GET https://dumosense-backend.onrender.com/api/v1/waitlist/`
   should return `405 Method Not Allowed` (the endpoint accepts POST). An OPTIONS request from
   `https://dumosense.com` should return `200` with
   `Access-Control-Allow-Origin: https://dumosense.com`. Then test a registration using an email
   address you control and have not already registered. Verify the registration is in the
   database and that the worker logs a successful send; check the inbox and spam folder.

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
