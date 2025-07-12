FROM python:3.13.0-alpine3.20
COPY --from=ghcr.io/astral-sh/uv:0.5.29 /uv /uvx /bin/

COPY ./src /databass
COPY ./pyproject.toml /databass/pyproject.toml
COPY ./uv.lock /databass/uv.lock
WORKDIR /databass

RUN \
  apk add --no-cache postgresql-libs && \
  apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev && \
  uv sync --frozen && \
  uv add gunicorn && \
  apk add --no-cache nodejs npm && \
  apk --purge del .build-deps && \
  npm install -g less && \
  ln -s /usr/local/bin/lessc /usr/bin/lessc

EXPOSE 8080
ENV FLASK_APP=databass:create_app
ENV FLASK_ENV=development
ENV VERSION=0.6

CMD ["uv", "run", "gunicorn", "--bind", "0.0.0.0:8080", "databass:create_app()"]
