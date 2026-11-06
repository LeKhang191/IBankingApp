# iBanking React frontend

This is a real-API React/Vite frontend; `mockApi.js` has been removed. Start it with `docker compose up -d --build` from the project root and open `http://localhost:5173`.

The frontend uses one `axiosClient.js` with the browser token and one API Gateway origin. Configure `VITE_API_URL=http://localhost:8080`. Auth uses `/api/auth/*`, tuition uses `/api/tuitions/*`, and payment uses `/api/payments/*`. Formatting helpers are in `src/utils/format.js` and do not mock data.

Environment values with prefix `VITE_` are browser-visible; never put passwords or SMTP secrets in them. Real email delivery requires the notification service and configured SMTP credentials.
