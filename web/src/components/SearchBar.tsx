import React, { useState, useCallback, useEffect } from 'react';
import {
  Paper,
  InputBase,
  IconButton,
  Box,
  CircularProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import debounce from 'lodash.debounce';

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  realtimeSearch?: boolean;
}

const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  loading = false,
  placeholder = 'Search...',
  autoFocus = true,
  realtimeSearch = true,
}) => {
  const [query, setQuery] = useState('');

  // Debounced search for real-time searching
  const debouncedSearch = useCallback(
    debounce((searchQuery: string) => {
      if (searchQuery.trim()) {
        onSearch(searchQuery);
      }
    }, 500),
    [onSearch]
  );

  useEffect(() => {
    // Keyboard shortcut: / to focus search
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        const searchInput = document.getElementById('search-input');
        if (searchInput && document.activeElement !== searchInput) {
          e.preventDefault();
          searchInput.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value;
    setQuery(newQuery);

    if (realtimeSearch) {
      debouncedSearch(newQuery);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  const handleClear = () => {
    setQuery('');
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
      (searchInput as HTMLInputElement).focus();
    }
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        width: '100%',
        maxWidth: 800,
        mx: 'auto',
        my: 4,
      }}
    >
      <Paper
        elevation={1}
        sx={{
          p: '2px 4px',
          display: 'flex',
          alignItems: 'center',
          borderRadius: 3,
          '&:hover': {
            boxShadow: 3,
          },
          '&:focus-within': {
            boxShadow: 4,
          },
        }}
      >
        <IconButton sx={{ p: '10px' }} aria-label="search">
          <SearchIcon />
        </IconButton>

        <InputBase
          id="search-input"
          sx={{ ml: 1, flex: 1 }}
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          autoFocus={autoFocus}
          inputProps={{
            'aria-label': 'search',
          }}
        />

        {query && (
          <IconButton
            sx={{ p: '10px' }}
            aria-label="clear"
            onClick={handleClear}
          >
            <ClearIcon />
          </IconButton>
        )}

        {loading && (
          <CircularProgress
            size={20}
            sx={{ mr: 1 }}
          />
        )}
      </Paper>

      <Box
        sx={{
          textAlign: 'center',
          mt: 1,
          fontSize: '0.875rem',
          color: 'text.secondary',
        }}
      >
        Press <kbd>/</kbd> to focus search
      </Box>
    </Box>
  );
};

export default SearchBar;