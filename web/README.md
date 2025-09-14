# grepctl Web UI

A customizable React-based web interface for the grepctl semantic search system.

## Features

- 🔍 Google-like search interface
- 🎨 Fully customizable theming
- 🌓 Dark mode support
- 📊 Real-time search results
- 🎯 Advanced filtering options
- 📱 Responsive design
- ⌨️ Keyboard shortcuts

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# The UI will be available at http://localhost:3000
# Make sure the grepctl API is running on port 8000
```

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Customization Guide

### 1. Basic Branding

Edit `src/config/theme.config.json` to customize your branding:

```json
{
  "branding": {
    "companyName": "Your Company",
    "logo": "/your-logo.svg",
    "tagline": "Your Tagline"
  }
}
```

### 2. Color Scheme

Modify the colors section in the config:

```json
{
  "colors": {
    "primary": "#1976d2",
    "secondary": "#dc004e",
    "background": "#ffffff",
    "text": "#333333"
  }
}
```

### 3. Using Preset Themes

The UI includes several preset themes:

- **Default**: Clean, modern blue theme
- **Google**: Google Search inspired
- **GitHub**: GitHub's color scheme
- **Enterprise**: Professional dark blue
- **Dark**: Built-in dark mode

To apply a preset, add the theme class to your configuration.

### 4. Custom Logo

1. Add your logo file to `public/` directory
2. Update the logo path in config:
```json
"logo": "/your-company-logo.svg"
```

### 5. Advanced Customization

For deeper customization, modify:

- `src/styles/variables.css` - CSS custom properties
- `src/App.tsx` - Theme configuration in Material-UI
- `src/components/BrandingHeader.tsx` - Header layout

### 6. Environment Variables

Create a `.env.local` file for environment-specific settings:

```env
VITE_API_URL=http://localhost:8000/api
VITE_COMPANY_NAME=Your Company
```

## Server-Side Theme Configuration

You can also configure themes server-side by passing a theme config file:

```bash
grepctl serve --theme-config ./my-theme.yaml
```

Example `my-theme.yaml`:

```yaml
branding:
  companyName: "Acme Corp"
  logo: "/static/acme-logo.svg"
  tagline: "Enterprise Search"

colors:
  primary: "#FF5722"
  secondary: "#FFC107"
  background: "#FFFFFF"
  text: "#212121"

features:
  darkMode: true
  exportEnabled: true
  advancedFilters: true
```

## Keyboard Shortcuts

- `/` - Focus search input
- `Enter` - Submit search
- `Escape` - Clear search
- `Ctrl/Cmd + K` - Quick search (coming soon)

## API Integration

The web UI expects the grepctl API to be running at:
- Development: `http://localhost:8000`
- Production: Same origin (proxied through the server)

## Building for Different Environments

### Custom Company Build

1. Replace logo in `public/`
2. Update `theme.config.json`
3. Build: `npm run build`
4. Deploy `dist/` folder

### Docker Deployment

```dockerfile
# Build stage
FROM node:18-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Serve with nginx
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT