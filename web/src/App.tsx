import React, { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { ThemeContextProvider } from './contexts/ThemeContext';
import SearchBar from './components/SearchBar';
import SearchResults from './components/SearchResults';
import FilterPanel from './components/FilterPanel';
import StatusBar from './components/StatusBar';
import BrandingHeader from './components/BrandingHeader';
import { SearchResult, SearchFilters } from './types';
import { searchAPI } from './services/api';
import './styles/App.css';

const queryClient = new QueryClient();

function App() {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState<SearchFilters>({
    modalities: [],
    topK: 10,
    useRerank: false,
  });
  const [darkMode, setDarkMode] = useState(false);
  const [themeConfig, setThemeConfig] = useState<any>(null);

  useEffect(() => {
    // Load theme configuration from server
    searchAPI.getConfig().then(config => {
      setThemeConfig(config);
      setDarkMode(localStorage.getItem('darkMode') === 'true');
    });
  }, []);

  const theme = React.useMemo(() => {
    const colors = darkMode && themeConfig?.darkMode?.enabled
      ? { ...themeConfig.colors, ...themeConfig.darkMode.colors }
      : themeConfig?.colors || {};

    return createTheme({
      palette: {
        mode: darkMode ? 'dark' : 'light',
        primary: {
          main: colors.primary || '#1976d2',
        },
        secondary: {
          main: colors.secondary || '#dc004e',
        },
        background: {
          default: colors.background || (darkMode ? '#121212' : '#ffffff'),
          paper: colors.surface || (darkMode ? '#1e1e1e' : '#f5f5f5'),
        },
        text: {
          primary: colors.text || (darkMode ? '#ffffff' : '#333333'),
          secondary: colors.textSecondary || (darkMode ? '#aaaaaa' : '#666666'),
        },
      },
      typography: {
        fontFamily: themeConfig?.layout?.fontFamily || "'Inter', sans-serif",
      },
      shape: {
        borderRadius: parseInt(themeConfig?.layout?.borderRadius || '8'),
      },
    });
  }, [darkMode, themeConfig]);

  const handleSearch = async (query: string) => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      const response = await searchAPI.search({
        query,
        top_k: filters.topK,
        modalities: filters.modalities,
        use_rerank: filters.useRerank,
      });
      setResults(response.results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleDarkMode = () => {
    const newMode = !darkMode;
    setDarkMode(newMode);
    localStorage.setItem('darkMode', String(newMode));
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <ThemeContextProvider value={{ themeConfig, setThemeConfig }}>
          <CssBaseline />
          <div className="app">
            <BrandingHeader
              darkMode={darkMode}
              onToggleDarkMode={toggleDarkMode}
              config={themeConfig?.branding}
            />

            <main className="main-content">
              <div className="search-section">
                <SearchBar
                  onSearch={handleSearch}
                  loading={loading}
                  placeholder="Search across all your documents..."
                />

                <FilterPanel
                  filters={filters}
                  onFiltersChange={setFilters}
                />
              </div>

              <SearchResults
                results={results}
                loading={loading}
              />
            </main>

            <StatusBar />
          </div>
        </ThemeContextProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;