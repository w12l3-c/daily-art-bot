FROM python:3.12-slim-bookworm
WORKDIR /app

# Build tools + image libs for Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev \
    zlib1g-dev libjpeg-dev libpng-dev libtiff5-dev \
    libfreetype6-dev liblcms2-dev libwebp-dev \
    libharfbuzz-dev libfribidi-dev libopenjp2-7-dev \
    libimagequant-dev libxcb1-dev \
 && rm -rf /var/lib/apt/lists/*

# Use piwheels if available, but also allow fallback to PyPI
# (You can also just omit these ENV lines entirely.)
ENV PIP_EXTRA_INDEX_URL=https://pypi.org/simple
# Optional: keep piwheels first; remove if you prefer PyPI first
ENV PIP_INDEX_URL=https://www.piwheels.org/simple

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir --prefer-binary -r requirements.txt

COPY . .
RUN mkdir -p /app/badges

CMD ["python", "bot.py"]
