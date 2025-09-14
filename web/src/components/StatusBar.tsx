import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  Chip,
  CircularProgress,
} from '@mui/material';
import {
  Storage as StorageIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { searchAPI } from '../services/api';
import { SystemStatus } from '../types';

const StatusBar: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const data = await searchAPI.getStatus();
        setStatus(data);
      } catch (error) {
        console.error('Failed to fetch status:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box
        sx={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          bgcolor: 'background.paper',
          borderTop: 1,
          borderColor: 'divider',
          p: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <CircularProgress size={16} />
      </Box>
    );
  }

  if (!status) {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        bgcolor: 'background.paper',
        borderTop: 1,
        borderColor: 'divider',
        p: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        px: 3,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <Chip
          icon={status.dataset_exists ? <CheckIcon /> : <ErrorIcon />}
          label={status.dataset_exists ? 'Dataset Ready' : 'Dataset Not Found'}
          size="small"
          color={status.dataset_exists ? 'success' : 'error'}
          variant="outlined"
        />

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <StorageIcon fontSize="small" color="action" />
          <Typography variant="caption" color="text.secondary">
            {status.document_count.toLocaleString()} documents indexed
          </Typography>
        </Box>

        <Chip
          label={`${status.modalities.length} modalities`}
          size="small"
          variant="outlined"
        />
      </Box>

      {status.last_updated && (
        <Typography variant="caption" color="text.secondary">
          Last updated: {new Date(status.last_updated).toLocaleString()}
        </Typography>
      )}
    </Box>
  );
};

export default StatusBar;