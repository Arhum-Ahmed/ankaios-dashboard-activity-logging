FROM docker.io/alpine:3.18.4 AS base
RUN apk update \
    && apk add --update-cache python3 \
    && python3 -m ensurepip \
    && pip3 install --no-cache-dir protobuf Flask flask-login ankaios-sdk \
    && apk add --no-cache nodejs npm yarn \
    && npm install -g @quasar/cli \
    && rm -rf /var/cache/apk/*

FROM base AS build
COPY /workspaces/ankaios-dashboard/app /ankaios-dashboard
WORKDIR /ankaios-dashboard/client
RUN npm install \
    && quasar build

FROM docker.io/alpine:3.18.4
RUN apk add --update-cache python3 \
    && python3 -m ensurepip \
    && pip3 install --no-cache-dir Flask flask-login ankaios-sdk \
    && rm -rf /var/cache/apk/*
WORKDIR /ankaios-dashboard
COPY --from=build /ankaios-dashboard/static /ankaios-dashboard/static
COPY /workspaces/ankaios-dashboard/app/AnkCommunicationService.py /ankaios-dashboard
COPY /workspaces/ankaios-dashboard/app/DashboardAPI.py /ankaios-dashboard
COPY /workspaces/ankaios-dashboard/app/Logger.py /ankaios-dashboard
COPY /workspaces/ankaios-dashboard/app/main.py /ankaios-dashboard
ENTRYPOINT ["python3", "-u", "main.py"]
