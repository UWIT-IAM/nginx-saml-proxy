FROM nginx as certbuilder

RUN apt-get update && apt-get install -y ssl-cert && apt-get clean
RUN mkdir /ssl && \
    cp -p /etc/ssl/private/ssl-cert-snakeoil.key /ssl/key.pem && \
    cp -p /etc/ssl/certs/ssl-cert-snakeoil.pem /ssl/cert.pem

FROM nginx

EXPOSE 80
EXPOSE 443

RUN rm /etc/nginx/conf.d/* && mkdir /static
COPY server.conf /etc/nginx/conf.d/server.conf
COPY --from=certbuilder /ssl /etc/nginx/ssl

CMD ["nginx", "-g", "daemon off;"]