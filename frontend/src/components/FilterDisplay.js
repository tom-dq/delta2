import React from 'react';
import styled from 'styled-components';

const FilterContainer = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
`;

const FiltersHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
`;

const RemainingCount = styled.div`
  background: ${props => {
    if (props.count === 0) return '#dc3545';
    if (props.count === 1) return '#28a745';
    if (props.count <= 5) return '#ffc107';
    return '#17a2b8';
  }};
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
`;

const FiltersList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
`;

const FilterItem = styled.div`
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  padding: 12px 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
`;

const FilterContent = styled.div`
  flex: 1;
`;

const FilterNumber = styled.span`
  background: #007bff;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 600;
  margin-right: 10px;
`;

const FilterDescription = styled.span`
  color: #495057;
  font-weight: 500;
`;

const EmptyState = styled.div`
  text-align: center;
  color: #6c757d;
  padding: 40px 20px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 2px dashed #dee2e6;
`;

const FilterDisplay = ({ filters = [], remainingItems = 0 }) => {
  const getCountMessage = (count) => {
    if (count === 0) return 'No taxa match';
    if (count === 1) return '1 taxon remaining';
    return `${count} taxa remaining`;
  };

  const getCountIcon = (count) => {
    if (count === 0) return '❌';
    if (count === 1) return '🎯';
    if (count <= 5) return '⚠️';
    return '📊';
  };

  return (
    <FilterContainer>
      <FiltersHeader>
        <h3 style={{ margin: 0, color: '#2c3e50' }}>
          Applied Filters
        </h3>
        <RemainingCount count={remainingItems}>
          {getCountIcon(remainingItems)} {getCountMessage(remainingItems)}
        </RemainingCount>
      </FiltersHeader>

      {filters.length === 0 ? (
        <EmptyState>
          <div style={{ fontSize: '3rem', marginBottom: '15px' }}>🔍</div>
          <h4 style={{ marginBottom: '10px', color: '#495057' }}>No Filters Applied</h4>
          <p style={{ margin: 0 }}>
            Select character values above to start narrowing down taxa
          </p>
        </EmptyState>
      ) : (
        <FiltersList>
          {filters.map((filter, index) => (
            <FilterItem key={index}>
              <FilterContent>
                <FilterNumber>{index + 1}</FilterNumber>
                <FilterDescription>
                  {filter.description}
                </FilterDescription>
              </FilterContent>
            </FilterItem>
          ))}
        </FiltersList>
      )}
    </FilterContainer>
  );
};

export default FilterDisplay;