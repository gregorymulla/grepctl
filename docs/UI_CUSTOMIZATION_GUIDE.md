# grepctl UI Customization Guide

This guide explains how to customize the grepctl web interface to match your company's branding and requirements.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Branding Customization](#branding-customization)
3. [Color Themes](#color-themes)
4. [Advanced Customization](#advanced-customization)
5. [Deployment Options](#deployment-options)
6. [Examples](#examples)

## Quick Start

The fastest way to customize the UI is through the theme configuration file:

```bash
# 1. Copy the default theme
cp config/ui_theme.yaml my-company-theme.yaml

# 2. Edit your theme file
nano my-company-theme.yaml

# 3. Start the server with your theme
grepctl serve --theme-config ./my-company-theme.yaml
```

## Branding Customization

### Step 1: Update Company Information

Edit your theme configuration file:

```yaml
branding:
  companyName: "Acme Corporation"
  tagline: "Enterprise Search Solutions"
  logo: "/static/acme-logo.svg"
  favicon: "/static/acme-favicon.ico"
```

### Step 2: Add Your Logo

1. Place your logo file in the `web/public/` directory:
   ```bash
   cp /path/to/your-logo.svg web/public/company-logo.svg
   ```

2. Recommended logo specifications:
   - Format: SVG (preferred) or PNG
   - Size: 40x40px to 200x40px
   - Background: Transparent

3. Update the logo path in your theme config:
   ```yaml
   branding:
     logo: "/company-logo.svg"
   ```

### Step 3: Custom Favicon

1. Generate favicon files (use a tool like https://favicon.io)
2. Place in `web/public/`
3. Update the path in config

## Color Themes

### Using Preset Themes

Choose from built-in themes by setting the preset:

```yaml
preset: "google"  # Options: default, google, github, enterprise, dark
```

### Custom Color Scheme

Define your brand colors:

```yaml
colors:
  # Brand colors
  primary: "#FF5722"      # Main brand color
  secondary: "#FFC107"    # Secondary color
  accent: "#4CAF50"       # Accent color

  # UI colors
  background: "#FFFFFF"   # Page background
  surface: "#F5F5F5"      # Card background
  text: "#212121"         # Main text
  textSecondary: "#757575" # Secondary text

  # Status colors (optional)
  error: "#F44336"
  warning: "#FF9800"
  info: "#2196F3"
  success: "#4CAF50"
```

### Dark Mode Configuration

Configure dark mode colors separately:

```yaml
darkMode:
  enabled: true  # Allow users to toggle dark mode
  colors:
    primary: "#FFB74D"
    secondary: "#FFD54F"
    background: "#121212"
    surface: "#1E1E1E"
    text: "#FFFFFF"
    textSecondary: "#B0B0B0"
```

## Advanced Customization

### Custom CSS

For deeper customization, create a custom CSS file:

1. Create `web/src/styles/custom.css`:

```css
/* Custom styles for your company */
:root {
  --company-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.branding-header {
  background: var(--company-gradient);
}

.search-bar {
  border: 2px solid var(--color-primary);
}
```

2. Import in `web/src/App.tsx`:
```typescript
import './styles/custom.css';
```

### Component Customization

Modify React components directly for structural changes:

1. **Header Layout** - `web/src/components/BrandingHeader.tsx`
2. **Search Interface** - `web/src/components/SearchBar.tsx`
3. **Results Display** - `web/src/components/SearchResults.tsx`

### Font Customization

Use custom fonts:

```yaml
layout:
  fontFamily: "'Roboto', 'Helvetica Neue', sans-serif"
```

Add font link to `web/index.html`:
```html
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
```

## Deployment Options

### Option 1: Static Build with Embedded Theme

1. Update `web/src/config/theme.config.json`
2. Build the application:
   ```bash
   cd web
   npm install
   npm run build
   ```
3. Deploy the `dist/` folder

### Option 2: Dynamic Theme Loading

1. Create theme file on server
2. Pass to grepctl:
   ```bash
   grepctl serve --theme-config /path/to/theme.yaml
   ```

### Option 3: Environment Variables

Set theme via environment:

```bash
export GREPCTL_THEME_CONFIG=/path/to/theme.yaml
grepctl serve
```

### Option 4: Docker Deployment

Create a Dockerfile with your theme:

```dockerfile
FROM python:3.11

# Copy application
COPY . /app
WORKDIR /app

# Install dependencies
RUN pip install grepctl

# Copy custom theme
COPY my-company-theme.yaml /app/theme.yaml

# Copy custom logo
COPY company-logo.svg /app/web/public/logo.svg

# Build web UI
RUN cd web && npm install && npm run build

# Start server
CMD ["grepctl", "serve", "--theme-config", "/app/theme.yaml"]
```

## Examples

### Example 1: Corporate Blue Theme

```yaml
branding:
  companyName: "TechCorp"
  tagline: "Intelligent Document Search"
  logo: "/techcorp-logo.svg"

colors:
  primary: "#003366"
  secondary: "#0066CC"
  accent: "#66B2FF"
  background: "#FFFFFF"
  surface: "#F0F4F8"
  text: "#1A1A1A"
  textSecondary: "#4A4A4A"

layout:
  borderRadius: "4px"  # More angular design
  fontFamily: "'IBM Plex Sans', sans-serif"
```

### Example 2: Modern Gradient Theme

```yaml
branding:
  companyName: "DataViz"
  tagline: "See Your Data Differently"

colors:
  primary: "#6B46C1"
  secondary: "#EC4899"
  accent: "#10B981"
  background: "#FAFAFA"
  surface: "#FFFFFF"

# Add custom CSS for gradients
customCss: |
  .search-bar {
    background: linear-gradient(135deg, #6B46C1 0%, #EC4899 100%);
    padding: 2rem;
    border-radius: 12px;
  }
```

### Example 3: Minimal Dark Theme

```yaml
branding:
  companyName: "NightSearch"
  tagline: ""  # No tagline for minimal look

colors:
  primary: "#FFFFFF"
  secondary: "#888888"
  background: "#000000"
  surface: "#111111"
  text: "#FFFFFF"
  textSecondary: "#888888"

darkMode:
  enabled: false  # Always dark

layout:
  borderRadius: "0px"  # Sharp corners
  fontFamily: "'JetBrains Mono', monospace"
```

## Testing Your Customization

1. **Local Testing**:
   ```bash
   # Start API server
   grepctl serve --theme-config ./my-theme.yaml

   # In another terminal, start web dev server
   cd web
   npm run dev
   ```

2. **Production Testing**:
   ```bash
   # Build web UI
   cd web
   npm run build

   # Start server
   grepctl serve --theme-config ./my-theme.yaml
   ```

3. **Visual Testing**:
   - Test in light and dark modes
   - Check mobile responsiveness
   - Verify logo displays correctly
   - Ensure color contrast meets accessibility standards

## Troubleshooting

### Logo Not Displaying

- Check file path is correct
- Ensure file is in `web/public/` directory
- Verify file permissions

### Colors Not Updating

- Clear browser cache
- Restart the server
- Check for CSS specificity conflicts

### Theme Not Loading

- Verify YAML syntax is correct
- Check file path in --theme-config
- Look for errors in server logs

## Best Practices

1. **Keep original files**: Don't modify default theme files directly
2. **Version control**: Track your theme files in git
3. **Test thoroughly**: Check all UI states and components
4. **Accessibility**: Ensure sufficient color contrast (WCAG AA standard)
5. **Performance**: Optimize logo and image files
6. **Documentation**: Document your customizations for team members

## Support

For help with customization:

1. Check the [web/README.md](../web/README.md) for technical details
2. Review example themes in `config/themes/`
3. Open an issue on GitHub for bugs or feature requests