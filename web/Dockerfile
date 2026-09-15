FROM node:22-alpine AS build
WORKDIR /app
COPY package.json .
RUN npm install
COPY index.html .
COPY src ./src
RUN npm run build

FROM httpd:2.4-alpine
COPY --from=build /app/dist/ /usr/local/apache2/htdocs/
COPY httpd.conf /usr/local/apache2/conf/httpd.conf
