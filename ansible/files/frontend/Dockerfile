FROM nginx:alpine

# Копируем статические файлы
COPY index.html /usr/share/nginx/html/

# Копируем конфиг (если нужен кастомный)
# Важно: этот файл должен существовать при сборке!
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Открываем порт
EXPOSE 80

# Запускаем nginx
CMD ["nginx", "-g", "daemon off;"]