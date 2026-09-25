# Cloudflare deployment

The Worker serves `frontend/dist`, routes `/api/*` to the FastAPI Container, and stores a clean SQLite database snapshot in the `marketflow-production-data` R2 bucket after API writes. The local `backend/marketing_campaigns.db` and `.env` are excluded from the container image.

Create an untracked `.env.production` file in this directory with `SECRET_KEY` and the three `MARKETFLOW_*_PASSWORD` values, then run `npm run deploy` after creating the R2 bucket. Wrangler uploads the secrets with the first deployment. The deploy script builds the frontend first. Containers require Cloudflare Workers Paid; see [Cloudflare Containers pricing](https://developers.cloudflare.com/containers/platform/pricing/).

The first container startup creates sample data using the configured passwords. Later starts restore the latest R2 snapshot before serving API traffic.
