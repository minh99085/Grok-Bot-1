FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY grok_bot grok_bot/
COPY loop loop/
COPY skills skills/
RUN pip install --no-cache-dir -e .
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "grok_bot.main", "--daemon"]