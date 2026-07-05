FROM nginx:alpine

# Copy the static site (index.html + Assets videos) into nginx's web root
COPY index.html /usr/share/nginx/html/index.html
COPY Assets /usr/share/nginx/html/Assets

# Basic nginx config: correct mime types for video + gzip off for mp4 (already compressed)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8093
