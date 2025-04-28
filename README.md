# ExplainerChonk: Enhancing Comprehension of Research Texts through Human-AI Collaboration

## How-To: Running as "Production" like app with docker

## Initial requirements

You need docker/docker compose installed on your hosting machine.

### Steps

1. Copy `.env.prod.example` to `.env.prod`.
2. Adjust the variable values in `.env.prod` (e.g., AWS keys, OpenAI keys, etc.)
3. copy `frontend/env.devopment` to `frontend/env.production`. Adjust environment variables accordingly.
4. Run: `docker compose -f docker-compose.yaml --env-file .env.prod up -d`

### SSL

Setting up SSL with Let's Encrypt and cerbot is a chicken and egg problem. Nginx will fail if the the specificed certs don't exist. If the Nginx doesn't run, then you won't be able to generate the certs with Let's Encrypt. To remedy this, you just need to selectively comment out the 443/SSL parts of nginx to run certbot (you shoul have docker compose running). E.g., `docker compose exec certbot certbot certonly --webroot -w /var/www/certbot -d app.explainerchonk.com` . After generating the certs, re-enable/uncomment the SSL blocks in nginx/conf.d/app.conf

## How-To: Running in development

1. (from root) `cp .env.development.example .env`; Adjust anything as appropriate in `.env`
2. `cp backend/.env.example backend/.env`; Adjust anything as appropriate in `.env`
3. `cp frontend/.env.example frontend/.env`; Adjust anything as appropriate in `.env`
4. From the root of the app (directory above `/backend` and `/frontend`), run:
   `docker compose -f compose-local.yaml up --build --env-file .env.development`
5. (from another terminal) `cd backend && uvicorn main:app --reload`
6. (from another terminal) `cd frontend && npm run dev`
7. (from another terminal) `cd backend && huey_consumer.py main.huey`
