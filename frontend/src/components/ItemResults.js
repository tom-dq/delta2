import React from 'react';
import styled from 'styled-components';

const ResultsContainer = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
`;

const ResultsHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
`;

const ItemsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
`;

const ItemCard = styled.div`
  background: ${props => {
    if (props.isTarget) return '#d4edda';
    return '#f8f9fa';
  }};
  border: 1px solid ${props => {
    if (props.isTarget) return '#c3e6cb';
    return '#dee2e6';
  }};
  border-radius: 6px;
  padding: 15px;
  transition: all 0.2s;

  &:hover {
    background: ${props => {
      if (props.isTarget) return '#c3e6cb';
      return '#e9ecef';
    }};
  }
`;

const ItemName = styled.div`
  font-weight: 600;
  color: ${props => props.isTarget ? '#155724' : '#495057'};
  margin-bottom: 5px;
  font-size: 1rem;
`;

const ItemNumber = styled.div`
  font-size: 0.8rem;
  color: #6c757d;
  font-family: monospace;
`;

const EmptyState = styled.div`
  text-align: center;
  color: #6c757d;
  padding: 40px 20px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 2px dashed #dee2e6;
`;

const SuccessState = styled.div`
  text-align: center;
  color: #155724;
  padding: 30px 20px;
  background: #d4edda;
  border-radius: 6px;
  border: 2px solid #c3e6cb;
`;

const cleanItemName = (name) => {
  if (typeof name !== 'string') return name;
  
  return name
    .replace(/\\i\{\}/g, '')  // Remove italic start
    .replace(/\\i0\{\}/g, '') // Remove italic end
    .replace(/\\b\{\}/g, '')  // Remove bold start
    .replace(/\\b0\{\}/g, '') // Remove bold end
    .trim();
};

const ItemResults = ({ items = [], totalCount = 0 }) => {
  const getHeaderIcon = () => {
    if (totalCount === 0) return '❌';
    if (totalCount === 1) return '🎯';
    if (totalCount <= 5) return '📋';
    return '📊';
  };

  const getHeaderText = () => {
    if (totalCount === 0) return 'No Results';
    if (totalCount === 1) return 'Identification Complete!';
    if (totalCount <= 5) return 'Few Results Remaining';
    return 'Current Results';
  };

  if (totalCount === 0) {
    return (
      <ResultsContainer>
        <ResultsHeader>
          <h3 style={{ margin: 0, color: '#2c3e50' }}>
            {getHeaderIcon()} {getHeaderText()}
          </h3>
        </ResultsHeader>
        
        <EmptyState>
          <div style={{ fontSize: '3rem', marginBottom: '15px' }}>🔍</div>
          <h4 style={{ marginBottom: '10px', color: '#495057' }}>No Taxa Match</h4>
          <p style={{ margin: 0 }}>
            Your current filters don't match any taxa. Try adjusting your selections.
          </p>
        </EmptyState>
      </ResultsContainer>
    );
  }

  if (totalCount === 1) {
    return (
      <ResultsContainer>
        <ResultsHeader>
          <h3 style={{ margin: 0, color: '#2c3e50' }}>
            {getHeaderIcon()} {getHeaderText()}
          </h3>
        </ResultsHeader>
        
        <SuccessState>
          <div style={{ fontSize: '4rem', marginBottom: '20px' }}>🎉</div>
          <h3 style={{ marginBottom: '15px' }}>Identification Successful!</h3>
          {items[0] && (
            <div>
              <ItemName isTarget>{cleanItemName(items[0].item_name)}</ItemName>
              <ItemNumber>Item #{items[0].item_number}</ItemNumber>
            </div>
          )}
        </SuccessState>
      </ResultsContainer>
    );
  }

  return (
    <ResultsContainer>
      <ResultsHeader>
        <h3 style={{ margin: 0, color: '#2c3e50' }}>
          {getHeaderIcon()} {getHeaderText()}
        </h3>
        <div style={{ 
          background: '#17a2b8', 
          color: 'white', 
          padding: '4px 12px', 
          borderRadius: '12px',
          fontSize: '0.9rem',
          fontWeight: '600'
        }}>
          {totalCount} taxa
        </div>
      </ResultsHeader>

      <ItemsList>
        {items.map((item, index) => (
          <ItemCard key={item.item_number || index} isTarget={totalCount === 1}>
            <ItemName isTarget={totalCount === 1}>
              {cleanItemName(item.item_name)}
            </ItemName>
            <ItemNumber>
              Item #{item.item_number}
            </ItemNumber>
          </ItemCard>
        ))}
      </ItemsList>
    </ResultsContainer>
  );
};

export default ItemResults;