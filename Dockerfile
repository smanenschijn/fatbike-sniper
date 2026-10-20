# Builds the Godot web export (same steps as the old GitHub Pages workflow) and serves it with nginx.
FROM ubuntu:24.04 AS build
ARG GODOT_VERSION=4.7.2

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl unzip python3 libfontconfig1 \
 && rm -rf /var/lib/apt/lists/*

# Godot + the single-threaded web template, in its own layer so Docker caches the big download.
RUN set -eux; \
    base=https://github.com/godotengine/godot/releases/download/${GODOT_VERSION}-stable; \
    mkdir -p /opt/godot /root/.local/share/godot/export_templates/${GODOT_VERSION}.stable; \
    cd /opt/godot; \
    curl -sSL -o godot.zip "$base/Godot_v${GODOT_VERSION}-stable_linux.x86_64.zip"; \
    unzip -q godot.zip && mv Godot_v${GODOT_VERSION}-stable_linux.x86_64 /usr/local/bin/godot && rm godot.zip; \
    curl -sSL -o templates.tpz "$base/Godot_v${GODOT_VERSION}-stable_export_templates.tpz"; \
    unzip -q -j templates.tpz templates/web_nothreads_release.zip templates/version.txt \
      -d /root/.local/share/godot/export_templates/${GODOT_VERSION}.stable; \
    rm templates.tpz

WORKDIR /src
COPY . .
RUN scripts/sync-godot-assets.sh \
 && godot --headless --path godot --import \
 && mkdir -p /out \
 && godot --headless --path godot --export-release "Web" /out/index.html \
 && ls -la /out

FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /out /usr/share/nginx/html
EXPOSE 80
