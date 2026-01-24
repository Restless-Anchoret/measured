# Measured Frontend

React + TypeScript frontend for the Measured time tracking application.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Run the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Environment Variables

Create a `.env.local` file in the frontend directory for local development:

```
VITE_API_URL=http://localhost:8000/api
```

For production deployment, set `VITE_API_URL` to your backend URL (e.g., `https://measured-backend.fly.dev/api`).

## Build

To build for production:
```bash
npm run build
```

To preview the production build locally:
```bash
npm run preview
```

## Deployment to Vercel

This frontend is configured for deployment to Vercel with automatic deployments from GitHub.

### Prerequisites

1. Create a Vercel account at [vercel.com](https://vercel.com)
2. Connect your Vercel account to GitHub
3. Ensure your code is pushed to a GitHub repository

### Deployment Steps

1. **Import Project to Vercel**
   - Log in to Vercel dashboard
   - Click "Add New" → "Project"
   - Import your GitHub repository

2. **Configure Project**
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

3. **Set Environment Variables**
   - Add `VITE_API_URL` with your backend URL
   - Example: `https://measured-backend.fly.dev/api`

4. **Deploy**
   - Click "Deploy"
   - Vercel will build and deploy your application
   - You'll receive a production URL

### Automatic Deployments

Once connected:
- Pushes to `main` branch deploy to production automatically
- Pull requests get unique preview URLs
- All branches can have preview deployments

### Post-Deployment

After deployment, update the backend CORS settings to allow your Vercel domain:

1. Update `backend/app/main.py` with your Vercel URL
2. Redeploy the backend with `fly deploy`

For detailed deployment instructions, see the deployment plan documentation.

## Technologies

- React 19
- TypeScript
- Vite
- Material UI
- React Router
