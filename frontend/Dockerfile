FROM node:20-alpine AS build
WORKDIR /app

# Build args vóór COPY zodat cache wordt gebust als env-waarden veranderen
ARG VITE_API_URL=""
ARG VITE_RHADIX_ENV=""
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_RHADIX_ENV=${VITE_RHADIX_ENV}

COPY package.json .
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
