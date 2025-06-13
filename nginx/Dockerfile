# Use the official lightweight Nginx image from Docker Hub.
FROM nginx:1.25-alpine

# Remove the default Nginx configuration file.
RUN rm /etc/nginx/conf.d/default.conf

# Copy your custom nginx.conf file into the container's configuration directory.
# When Nginx starts, it will automatically load this configuration.
COPY nginx.conf /etc/nginx/conf.d/default.conf
