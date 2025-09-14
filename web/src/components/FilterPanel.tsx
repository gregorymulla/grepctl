import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  FormControl,
  FormLabel,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Slider,
  Switch,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { SearchFilters } from '../types';
import { searchAPI } from '../services/api';

interface FilterPanelProps {
  filters: SearchFilters;
  onFiltersChange: (filters: SearchFilters) => void;
}

const FilterPanel: React.FC<FilterPanelProps> = ({
  filters,
  onFiltersChange,
}) => {
  const [modalities, setModalities] = useState<any[]>([]);

  useEffect(() => {
    searchAPI.getModalities().then(setModalities);
  }, []);

  const handleModalityChange = (modality: string) => {
    const newModalities = filters.modalities.includes(modality)
      ? filters.modalities.filter(m => m !== modality)
      : [...filters.modalities, modality];

    onFiltersChange({
      ...filters,
      modalities: newModalities,
    });
  };

  const handleTopKChange = (event: Event, value: number | number[]) => {
    onFiltersChange({
      ...filters,
      topK: value as number,
    });
  };

  const handleRerankChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      useRerank: event.target.checked,
    });
  };

  return (
    <Paper sx={{ p: 2, mb: 3 }}>
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Search Filters</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Modality Filter */}
            <FormControl component="fieldset">
              <FormLabel component="legend">Data Types</FormLabel>
              <FormGroup row>
                {modalities.map((modality) => (
                  <FormControlLabel
                    key={modality.id}
                    control={
                      <Checkbox
                        checked={filters.modalities.includes(modality.id)}
                        onChange={() => handleModalityChange(modality.id)}
                      />
                    }
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <span>{modality.icon}</span>
                        <span>{modality.label}</span>
                      </Box>
                    }
                  />
                ))}
              </FormGroup>
            </FormControl>

            {/* Results Count */}
            <FormControl>
              <FormLabel>
                Number of Results: {filters.topK}
              </FormLabel>
              <Slider
                value={filters.topK}
                onChange={handleTopKChange}
                min={5}
                max={50}
                step={5}
                marks={[
                  { value: 5, label: '5' },
                  { value: 20, label: '20' },
                  { value: 35, label: '35' },
                  { value: 50, label: '50' },
                ]}
                valueLabelDisplay="auto"
              />
            </FormControl>

            {/* Advanced Options */}
            <FormControl>
              <FormLabel>Advanced Options</FormLabel>
              <FormGroup>
                <FormControlLabel
                  control={
                    <Switch
                      checked={filters.useRerank}
                      onChange={handleRerankChange}
                    />
                  }
                  label="Use AI Reranking (slower but more accurate)"
                />
              </FormGroup>
            </FormControl>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Paper>
  );
};

export default FilterPanel;