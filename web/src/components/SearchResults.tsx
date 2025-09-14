import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Tooltip,
  Paper,
} from '@mui/material';
import {
  ContentCopy as CopyIcon,
  OpenInNew as OpenIcon,
  GetApp as DownloadIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { SearchResult } from '../types';
import { searchAPI } from '../services/api';

interface SearchResultsProps {
  results: SearchResult[];
  loading?: boolean;
}

const SearchResults: React.FC<SearchResultsProps> = ({ results, loading }) => {
  const handleCopyContent = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const handleOpenUri = (uri: string) => {
    window.open(uri, '_blank');
  };

  const handleExportResults = async (format: 'json' | 'csv') => {
    const blob = await searchAPI.exportResults(results, format);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `search-results-${Date.now()}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const getModalityColor = (modality: string) => {
    const colors: Record<string, any> = {
      text: 'primary',
      markdown: 'secondary',
      pdf: 'error',
      images: 'warning',
      json: 'info',
      csv: 'success',
      audio: 'primary',
      video: 'secondary',
    };
    return colors[modality] || 'default';
  };

  const truncateText = (text: string, maxLength: number = 300) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  if (loading) {
    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        <LinearProgress />
      </Box>
    );
  }

  if (results.length === 0) {
    return (
      <Paper
        sx={{
          p: 4,
          textAlign: 'center',
          color: 'text.secondary',
        }}
      >
        <Typography variant="h6">No results found</Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>
          Try adjusting your search query or filters
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 2,
        }}
      >
        <Typography variant="h6" color="text.secondary">
          {results.length} results found
        </Typography>

        <Box>
          <Tooltip title="Export as JSON">
            <IconButton onClick={() => handleExportResults('json')}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
          <Tooltip title="Export as CSV">
            <IconButton onClick={() => handleExportResults('csv')}>
              <DownloadIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {results.map((result, index) => (
          <Card
            key={result.doc_id || index}
            elevation={1}
            sx={{
              '&:hover': {
                boxShadow: 3,
              },
            }}
          >
            <CardContent>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  mb: 1,
                }}
              >
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Chip
                    label={result.modality}
                    size="small"
                    color={getModalityColor(result.modality)}
                  />
                  <Chip
                    label={result.source}
                    size="small"
                    variant="outlined"
                  />
                  <Typography variant="caption" color="text.secondary">
                    Score: {result.score.toFixed(3)}
                  </Typography>
                </Box>

                <Box>
                  <Tooltip title="Copy content">
                    <IconButton
                      size="small"
                      onClick={() => handleCopyContent(result.text_content)}
                    >
                      <CopyIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  {result.uri && (
                    <Tooltip title="Open source">
                      <IconButton
                        size="small"
                        onClick={() => handleOpenUri(result.uri)}
                      >
                        <OpenIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </Box>

              <Typography
                variant="body1"
                sx={{
                  mb: 1,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {truncateText(result.text_content)}
              </Typography>

              {result.uri && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{
                    display: 'block',
                    mt: 1,
                    fontFamily: 'monospace',
                  }}
                >
                  {result.uri}
                </Typography>
              )}

              {result.created_at && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: 'block', mt: 0.5 }}
                >
                  {format(new Date(result.created_at), 'PPp')}
                </Typography>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
};

export default SearchResults;