FROM oven/bun:alpine AS base
WORKDIR /app

COPY package.json bun.lock ./

FROM base AS prod
RUN bun add husky && \
  bun install --production

FROM base AS build

COPY . .

ENV LOCAL_BASE_URL=
ARG AUTH_BASE_PATH=
ENV AUTH_BASE_PATH=${AUTH_BASE_PATH}

RUN bun i && bun build:dist && \
  if [ -n "$AUTH_BASE_PATH" ] && [ "$AUTH_BASE_PATH" != "/" ]; then \
    BASE_PATH="$(echo "$AUTH_BASE_PATH" | sed 's#^/*##; s#/*$##')" && \
    mkdir -p "/app/dist/client/$BASE_PATH" && \
    cp -R /app/dist/client/dist "/app/dist/client/$BASE_PATH/dist"; \
  fi

FROM oven/bun:alpine

WORKDIR /app
ARG AUTH_BASE_PATH=
ENV AUTH_BASE_PATH=${AUTH_BASE_PATH}

COPY package.json ./
COPY --from=prod /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist

ENV HOST=0.0.0.0
EXPOSE 4321

CMD [ "bun", "serv" ]
