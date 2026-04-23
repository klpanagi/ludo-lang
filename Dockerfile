FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir textX==4.3.0 Jinja2==3.1.6

COPY grammar/   grammar/
COPY generator/ generator/
COPY templates/ templates/
COPY examples/  examples/
COPY ui/        ui/

RUN mkdir -p output

EXPOSE 8765

CMD ["python", "ui/server.py"]
