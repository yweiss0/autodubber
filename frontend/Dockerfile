FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy application code
COPY . .

# Create .svelte-kit directory to avoid permission issues
RUN mkdir -p .svelte-kit

# Expose port
EXPOSE 5173

# For development, we'll use Vite's dev server with proper host configuration
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"] 