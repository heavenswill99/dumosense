# cPanel Setup for Dumosense

Use this guide when the React frontend is in `public_html` and the Node backend is hosted by cPanel.
The backend startup file is `server.js`.

## Before you start

You need:

- cPanel **Application Manager** or **Setup Node.js App**
- Node.js 18 or newer
- HTTPS enabled for `dumosense.com`
- The built frontend files from `dist/`

## 1. Upload the frontend

1. Run `npm run build` on your computer.
2. Open cPanel **File Manager**.
3. Open `public_html`.
4. Remove old frontend files, especially old `build/` files.
5. Upload the contents of the local `dist/` folder directly into `public_html`.

The file must be located at:

```text
public_html/index.html
```

Do not upload the local `dist` folder itself as `public_html/dist`.

## 2. Upload the backend

Create a folder outside `public_html`, for example:

```text
/home/CPANEL_USERNAME/dumosense-backend
```

Upload these files into that folder:

```text
server.js
package.json
```

Do not put the backend inside `public_html`. Do not upload `node_modules`.

## 3. Create persistent storage

Create this folder:

```text
/home/CPANEL_USERNAME/dumosense-data
```

Make sure the Node application user can read and write to it. User accounts and sessions are stored
in this folder, so it must not be inside a temporary deployment directory.

## 4. Create the Node application

Open cPanel **Application Manager** or **Setup Node.js App**, then create an application with:

```text
Node.js version: 18 or newer
Application mode: Production
Application root: /home/CPANEL_USERNAME/dumosense-backend
Application URL: https://dumosense.com/api
Application startup file: server.js
```

If cPanel does not allow `/api` as an application URL, create an API subdomain instead:

```text
api.dumosense.com
```

In that case, use `https://api.dumosense.com` as the backend URL and rebuild the frontend with
`VITE_BACKEND_URL=https://api.dumosense.com`.

## 5. Add environment variables

In the Node application settings, add these values. Replace `CPANEL_USERNAME` with the actual cPanel
username. Use the port shown by cPanel; do not invent a port.

```text
NODE_ENV=production
HOST=0.0.0.0
PORT=<PORT_SHOWN_BY_CPANEL>
FRONTEND_ORIGIN=https://dumosense.com,https://www.dumosense.com
DATA_FILE=/home/CPANEL_USERNAME/dumosense-data/data.json
COOKIE_SECURE=true
COOKIE_SAMESITE=Lax
```

The backend has safe defaults, but setting these values explicitly avoids deployment surprises.

## 6. Install and start

In cPanel, click **Run NPM Install** if that button is available. This backend has no external
runtime dependencies, so installation should be quick.

Then click **Start App** or **Restart App**. Every time you change an environment variable, restart
the app.

## 7. Test the backend before testing signup

Open this URL in a browser:

```text
https://dumosense.com/api/health
```

It must show:

```json
{"status":"ok"}
```

If it shows `503`, signup cannot work yet. Check the cPanel application log and verify:

- Application root points to the folder containing `server.js`.
- Startup file is exactly `server.js`.
- The cPanel-assigned port is used in `PORT`.
- The data directory exists and is writable.
- The Node app has been restarted.

If it shows `404`, the `/api` route is not connected to the Node app. Fix the Application URL or use
the `api.dumosense.com` subdomain setup.

## 8. Test signup and login

Only after `/api/health` returns `{"status":"ok"}`:

1. Open `https://dumosense.com`.
2. Hard-refresh with `Ctrl+Shift+R`.
3. Create a new account.
4. Log out.
5. Log back in with the same email and password.

The frontend is already configured to call:

```text
https://dumosense.com/api
```

