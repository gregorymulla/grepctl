import React, { createContext, useContext } from 'react';
import { ThemeConfig } from '../types';

interface ThemeContextValue {
  themeConfig: ThemeConfig | null;
  setThemeConfig: (config: ThemeConfig) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeContextProvider: React.FC<{
  children: React.ReactNode;
  value: ThemeContextValue;
}> = ({ children, value }) => {
  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useThemeContext = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeContext must be used within ThemeContextProvider');
  }
  return context;
};