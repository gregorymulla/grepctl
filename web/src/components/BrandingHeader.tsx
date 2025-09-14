import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Box,
  Avatar,
} from '@mui/material';
import {
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';

interface BrandingHeaderProps {
  darkMode: boolean;
  onToggleDarkMode: () => void;
  config?: {
    companyName: string;
    logo: string;
    tagline: string;
  };
}

const BrandingHeader: React.FC<BrandingHeaderProps> = ({
  darkMode,
  onToggleDarkMode,
  config,
}) => {
  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: 'background.paper' }}>
      <Toolbar>
        <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
          {config?.logo && (
            <Avatar
              src={config.logo}
              sx={{ width: 40, height: 40, mr: 2 }}
              variant="square"
            />
          )}
          <Box>
            <Typography
              variant="h6"
              component="h1"
              sx={{
                fontWeight: 600,
                color: 'text.primary',
              }}
            >
              {config?.companyName || 'grepctl'}
            </Typography>
            {config?.tagline && (
              <Typography
                variant="caption"
                sx={{
                  color: 'text.secondary',
                  display: 'block',
                  mt: -0.5,
                }}
              >
                {config.tagline}
              </Typography>
            )}
          </Box>
        </Box>

        <IconButton
          onClick={onToggleDarkMode}
          color="inherit"
          sx={{ ml: 1 }}
        >
          {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
        </IconButton>

        <IconButton
          color="inherit"
          sx={{ ml: 1 }}
        >
          <SettingsIcon />
        </IconButton>
      </Toolbar>
    </AppBar>
  );
};

export default BrandingHeader;