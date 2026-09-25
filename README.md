# Dumosense Frontend

This project uses Vite for local development and production builds.

## Backend

The authentication API is in `backend/`. For local development, run it from the project root:

```sh
node backend/server.js
```

The backend stores development data in `backend/data.json`. That file is ignored by git.

For cPanel hosting, follow [backend/CPANEL.md](backend/CPANEL.md). The backend folder is ready to
upload as a cPanel Node.js application with `server.js` as its startup file.

### Hosting the backend

The backend can run on Render, Railway, Fly.io, or any Node 18+ host. Set these variables in the
host's environment configuration:

```text
NODE_ENV=production
HOST=0.0.0.0
PORT=4000
FRONTEND_ORIGIN=https://dumosense.com,https://www.dumosense.com
DATA_FILE=/data/dumosense.json
COOKIE_SECURE=true
COOKIE_SAMESITE=Lax
```

Attach a persistent volume at `/data`. The current store is intended for a single backend
instance with persistent disk; use a managed database before running multiple replicas or storing
large production datasets. The included [backend/Dockerfile](backend/Dockerfile) exposes port 4000.

### Hosting the frontend

Create a production environment file before building, using the public Dumosense URL:

```text
VITE_BACKEND_URL=https://dumosense.com
```

Then build with `npm run build` and serve the generated `dist/` directory from a static host.
The local `.env` is only for development and must not be used for the hosted build.

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
