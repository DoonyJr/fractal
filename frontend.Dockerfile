FROM nginx:alpine

ENV BACKEND_URL=http://backend:5000

RUN rm -rf /usr/share/nginx/html/*

COPY frontend-dist/ /usr/share/nginx/html/

RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    gzip on;\n\
    gzip_min_length 1k;\n\
    gzip_comp_level 6;\n\
    gzip_types text/plain text/css text/javascript application/json application/javascript application/x-javascript application/xml;\n\
    gzip_vary on;\n\
\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    location /api {\n\
        proxy_pass ${BACKEND_URL};\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n\
        proxy_set_header X-Forwarded-Proto $scheme;\n\
        proxy_read_timeout 300s;\n\
        proxy_connect_timeout 10s;\n\
    }\n\
\n\
    location /socket.io {\n\
        proxy_pass ${BACKEND_URL};\n\
        proxy_http_version 1.1;\n\
        proxy_set_header Upgrade $http_upgrade;\n\
        proxy_set_header Connection "upgrade";\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
        proxy_read_timeout 86400s;\n\
    }\n\
\n\
    location /health {\n\
        access_log off;\n\
        return 200 "ok";\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf.template

COPY <<'EOF' /docker-entrypoint.d/90-envsubst-backend.sh
#!/bin/sh
envsubst '${BACKEND_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
EOF
RUN chmod +x /docker-entrypoint.d/90-envsubst-backend.sh

EXPOSE 80
